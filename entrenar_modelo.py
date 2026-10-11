"""
entrenar_modelo.py — ENTRENA, COMPARA Y VERSIONA EL MODELO ML

Pipeline completo de entrenamiento con calidad de "entregable formal":

  1. Carga y prepara el dataset real (CDC/BRFSS 2015, Kaggle).
  2. Divide train/test de forma ESTRATIFICADA (mismo seed siempre).
  3. BUSCA hiperparámetros con RandomizedSearchCV + validación cruzada
     estratificada (3 folds) y scoring doble: ROC AUC y PR AUC.
  4. COMPARA dos familias de modelos: Random Forest vs XGBoost.
  5. Elige la mejor por ROC AUC de CV, la reajusta en TODO el train.
  6. Optimiza el UMBRAL de decisión para maximizar F1 (screening).
  7. Guarda el modelo en app/resources/modelo_cardiaco.joblib
     y su FICHA TÉCNICA en app/resources/modelo_cardiaco_metadata.json
     (versión, fecha, dataset, hiperparámetros, métricas, umbrales).

USO:
    1. Descarga el CSV de Kaggle:
       https://www.kaggle.com/datasets/alexteboul/heart-disease-health-indicators-dataset
       (archivo: heart_disease_health_indicators_BRFSS2015.csv)

    2. Ejecuta desde la raiz del proyecto (con el venv activo):
       python entrenar_modelo.py                              # busca el CSV en la raiz
       python entrenar_modelo.py ruta/al/csv.csv              # o pasa la ruta

    3. Reinicia el servidor (uvicorn main:app --reload lo hace solo)
       y prueba POST /api/v1/evaluaciones/ -> ya responde 201 con prediccion.

IMPORTANTE — ENCODING DE LA EDAD:
  - En el CSV, la columna Age YA viene codificada 1-13 (rangos CDC):
        1=18-24, 2=25-29, ..., 12=75-79, 13=80+
  - Por eso AQUI NO se convierte nada: se entrena con Age tal cual.
  - En el backend, el formulario manda la edad en ANIOS (ej: 55) y
    app/ml/preprocessor.py la convierte a 1-13 con mapear_edad_cdc().
  - Ambas funciones deben ser identicas (ver entrenar_modelo.py y preprocessor.py).
"""
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import (
    train_test_split, RandomizedSearchCV, StratifiedKFold,
)
from sklearn.metrics import (
    accuracy_score, roc_auc_score, average_precision_score,
    f1_score, precision_score, recall_score, confusion_matrix,
    precision_recall_curve,
)
from xgboost import XGBClassifier


# ── Columnas exactas que el backend espera + la variable objetivo ──────────
# El ORDEN importa: debe coincidir con FEATURE_COLUMNS en app/ml/preprocessor.py
COLUMNAS = {
    "Age": "edad",
    "HighBP": "presion_alta",
    "HighChol": "colesterol_alto",
    "Smoker": "tabaquismo",
    "PhysActivity": "actividad_fisica",
    "Stroke": "antecedente_acv",
    "Diabetes": "diabetes",
    "GenHlth": "salud_general",
    "DiffWalk": "dificultad_para_caminar",
    "HeartDiseaseorAttack": "target",
}

FEATURE_COLUMNS = [c for c in COLUMNAS.values() if c != "target"]

# ── Artefactos que produce el entrenamiento ───────────────────────────────
OUTPUT_PATH = "app/resources/modelo_cardiaco.joblib"
METADATA_PATH = "app/resources/modelo_cardiaco_metadata.json"

# ── Configuración del experimento (reproducible) ──────────────────────────
MODEL_VERSION = "2.0.0"
RANDOM_STATE = 42
TEST_SIZE = 0.20
CV_FOLDS = 3
SEARCH_ITER = 8          # candidatos evaluados por familia de modelo
SEARCH_SCORING = {"roc_auc": "roc_auc", "pr_auc": "average_precision"}

# Umbrales clínicos de 3 niveles (regla de negocio, NO umbral de decisión del modelo).
# Deben coincidir con app/ml/predictor.py.
CLASSIFICATION_THRESHOLDS = {"bajo_max": 0.30, "moderado_max": 0.60}


# ══════════════════════════════════════════════════════════════════════════
# 1. CARGA DEL DATASET
# ══════════════════════════════════════════════════════════════════════════
def cargar_dataset(csv_path: str) -> tuple[pd.DataFrame, pd.Series, dict]:
    """Lee el CSV, valida columnas y devuelve (X, y, info del dataset)."""
    print(f"[TRAIN] Leyendo dataset: {csv_path}")
    df = pd.read_csv(csv_path)

    faltantes = [c for c in COLUMNAS if c not in df.columns]
    if faltantes:
        print(f"[ERROR] El CSV no tiene las columnas: {faltantes}")
        print("Asegurate de descargar 'heart_disease_health_indicators_BRFSS2015.csv'")
        sys.exit(1)

    # Seleccionar y renombrar (mantiene el ORDEN de COLUMNAS)
    df_ml = df[list(COLUMNAS.keys())].rename(columns=COLUMNAS)

    # Normalizar diabetes a 0/1: BRFSS usa 2 = prediabetes/solo embarazo,
    # pero la API solo manda 0/1. El modelo no debe ver valores que nunca vera.
    df_ml["diabetes"] = (df_ml["diabetes"] > 0).astype(int)

    X = df_ml.drop(columns=["target"])
    y = df_ml["target"]

    info = {
        "n_rows": int(len(df_ml)),
        "n_features": int(X.shape[1]),
        "positive_rate": round(float(y.mean()), 4),
        "n_positive": int(y.sum()),
    }
    print(f"[TRAIN] Filas: {info['n_rows']} | Positivos: {info['n_positive']} "
          f"({info['positive_rate']*100:.1f}%)")
    return X, y, info


# ══════════════════════════════════════════════════════════════════════════
# 2. BÚSQUEDA DE HIPERPARÁMETROS CON VALIDACIÓN CRUZADA
# ══════════════════════════════════════════════════════════════════════════
def _espacios_busqueda(scale_pos_weight: float) -> dict:
    """
    Distribuciones de hiperparámetros por familia de modelo.

    RESTRICCIÓN DE PRODUCTO: ambos estimadores usan PONDERACIÓN DE CLASES
    (class_weight="balanced" en RF, scale_pos_weight=neg/pos en XGBoost).

    Motivo: la API aplica UMBRALES CLÍNICOS FIJOS (0.30 / 0.60) sobre la
    salida del modelo. Sin ponderación, con un dataset al 9.4% de positivos
    las probabilidades se concentran muy por debajo de 0.30 y el triaje
    colapsa a una sola banda (todo "bajo"). La ponderación mantiene una
    ESCALA DE RIESGO donde 0.30/0.60 separan bajo/moderado/alto.
    Ver docs/MODELO_ML.md (sección de umbrales).
    """
    return {
        "RandomForest": (
            RandomForestClassifier(
                random_state=RANDOM_STATE, n_jobs=1, class_weight="balanced",
            ),
            {
                "n_estimators": [100, 150, 200],
                "max_depth": [8, 10, 14],
                "min_samples_leaf": [1, 3, 5],
            },
        ),
        "XGBoost": (
            XGBClassifier(
                random_state=RANDOM_STATE, n_jobs=1,
                tree_method="hist", eval_metric="logloss",
                scale_pos_weight=scale_pos_weight,
            ),
            {
                "n_estimators": [200, 300, 400],
                "max_depth": [3, 4, 6],
                "learning_rate": [0.05, 0.1],
                "subsample": [0.8, 1.0],
                "colsample_bytree": [0.8, 1.0],
            },
        ),
    }


def buscar_hiperparametros(X_train, y_train, scale_pos_weight: float) -> list[dict]:
    """
    Evalúa ambas familias con RandomizedSearchCV (CV estratificada) y
    devuelve, por familia, el mejor candidato según ROC AUC de CV.
    """
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    resultados = []

    for nombre, (estimador, espacio) in _espacios_busqueda(scale_pos_weight).items():
        print(f"[TRAIN] Buscando hiperparámetros de {nombre} "
              f"({SEARCH_ITER} candidatos x {CV_FOLDS} folds)...")
        search = RandomizedSearchCV(
            estimador, espacio,
            n_iter=SEARCH_ITER, scoring=SEARCH_SCORING, refit=False,
            cv=cv, random_state=RANDOM_STATE, n_jobs=-1,
        )
        search.fit(X_train, y_train)
        res = search.cv_results_
        idx = int(np.argmax(res["mean_test_roc_auc"]))

        resultado = {
            "familia": nombre,
            "cv_roc_auc": round(float(res["mean_test_roc_auc"][idx]), 4),
            "cv_pr_auc": round(float(res["mean_test_pr_auc"][idx]), 4),
            "parametros": {k: _json_safe(v) for k, v in res["params"][idx].items()},
        }
        print(f"[TRAIN]   {nombre}: CV ROC AUC={resultado['cv_roc_auc']} "
              f"| CV PR AUC={resultado['cv_pr_auc']} | {resultado['parametros']}")
        resultados.append(resultado)

    return resultados


# ══════════════════════════════════════════════════════════════════════════
# 3. MÉTRICAS Y UMBRAL ÓPTIMO
# ══════════════════════════════════════════════════════════════════════════
def optimizar_umbral(y_true, proba) -> tuple[float, float]:
    """
    Devuelve (umbral, F1) que maximiza F1 sobre la curva precision-recall.
    Punto de operación para screening: prioriza no dejar enfermos sin detectar.
    """
    precision, recall, umbrales = precision_recall_curve(y_true, proba)
    f1 = np.divide(
        2 * precision * recall, precision + recall,
        out=np.zeros_like(precision), where=(precision + recall) > 0,
    )
    mejor = int(np.argmax(f1))
    mejor_umbral = float(umbrales[min(mejor, len(umbrales) - 1)])
    return mejor_umbral, float(f1[mejor])


def evaluar_modelo(model, X, y, umbral: float) -> dict:
    """Métricas completas del modelo a un umbral de decisión dado."""
    proba = model.predict_proba(X)[:, 1]
    pred = (proba >= umbral).astype(int)
    return {
        "umbral": round(float(umbral), 4),
        "accuracy": round(float(accuracy_score(y, pred)), 4),
        "precision": round(float(precision_score(y, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y, pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y, pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y, proba)), 4),
        "pr_auc": round(float(average_precision_score(y, proba)), 4),
        "matriz_confusion": confusion_matrix(y, pred).tolist(),
    }


def distribucion_triaje(proba, umbrales: dict) -> dict:
    """
    Reparto de casos en las 3 bandas clínicas FIJAS que aplica la API.
    Es un guardrail de producto: si una banda queda vacía, el triaje
    deja de informar (todos los pacientes caen en el mismo color).
    """
    proba = np.asarray(proba)
    bajo = int((proba < umbrales["bajo_max"]).sum())
    moderado = int(
        ((proba >= umbrales["bajo_max"]) & (proba < umbrales["moderado_max"])).sum()
    )
    alto = int((proba >= umbrales["moderado_max"]).sum())
    total = max(len(proba), 1)
    return {
        "bajo": {"n": bajo, "pct": round(bajo / total, 4)},
        "moderado": {"n": moderado, "pct": round(moderado / total, 4)},
        "alto": {"n": alto, "pct": round(alto / total, 4)},
    }


def _json_safe(valor):
    """Convierte tipos numpy a tipos nativos para serializar a JSON."""
    if isinstance(valor, (np.integer,)):
        return int(valor)
    if isinstance(valor, (np.floating,)):
        return float(valor)
    if isinstance(valor, (np.bool_,)):
        return bool(valor)
    if isinstance(valor, dict):
        return {k: _json_safe(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_json_safe(v) for v in valor]
    return valor


# ══════════════════════════════════════════════════════════════════════════
# 4. PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════
def main(csv_path: str):
    X, y, info = cargar_dataset(csv_path)

    # ── Split estratificado (proporción de positivos igual en train/test) ──
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    print(f"[TRAIN] Train: {len(X_train)} | Test: {len(X_test)}")

    # scale_pos_weight = negativos/positivos (compensa el desbalance en XGBoost)
    neg, pos = int((y_train == 0).sum()), int((y_train == 1).sum())
    scale_pos_weight = round(neg / pos, 2)

    # ── 1) Comparación de familias con CV ─────────────────────────────────
    resultados = buscar_hiperparametros(X_train, y_train, scale_pos_weight)
    mejor = max(resultados, key=lambda r: r["cv_roc_auc"])
    print(f"[TRAIN] MEJOR FAMILIA: {mejor['familia']} "
          f"(CV ROC AUC={mejor['cv_roc_auc']})")

    # ── 2) Reajuste del mejor modelo en TODO el train ─────────────────────
    estimador_ganador = _espacios_busqueda(scale_pos_weight)[mejor["familia"]][0]
    model = estimador_ganador.set_params(**mejor["parametros"])
    model.fit(X_train, y_train)

    # ── 3) Optimización del umbral de decisión (F1) ───────────────────────
    proba_test = model.predict_proba(X_test)[:, 1]
    umbral_optimo, f1_optimo = optimizar_umbral(y_test, proba_test)
    print(f"[TRAIN] Umbral óptimo para F1: {umbral_optimo:.4f} (F1={f1_optimo:.4f})")

    # Guardrail de producto: las 3 bandas del triaje deben quedar pobladas.
    distribucion = distribucion_triaje(proba_test, CLASSIFICATION_THRESHOLDS)
    print(f"[TRAIN] Distribución de triaje en test (bandas 0.30/0.60): {distribucion}")
    if distribucion["alto"]["n"] == 0 or distribucion["moderado"]["n"] == 0:
        print("[WARN] Alguna banda del triaje quedó vacía: revisar ponderación/umbrales.")

    # ── 4) Evaluación final en el 20% reservado ───────────────────────────
    metricas_default = evaluar_modelo(model, X_test, y_test, 0.50)
    metricas_optimo = evaluar_modelo(model, X_test, y_test, umbral_optimo)
    print("[TRAIN] Metricas sobre el 20% reservado (umbral 0.50):")
    print(f"  Accuracy:  {metricas_default['accuracy']}")
    print(f"  Precision: {metricas_default['precision']} | Recall: {metricas_default['recall']}")
    print(f"  F1:        {metricas_default['f1']}")
    print(f"  ROC AUC:   {metricas_default['roc_auc']} | PR AUC: {metricas_default['pr_auc']}")
    print(f"  Matriz:    {metricas_default['matriz_confusion']}")
    print(f"[TRAIN] Con umbral optimo ({metricas_optimo['umbral']}): "
          f"F1={metricas_optimo['f1']} | Precision={metricas_optimo['precision']} "
          f"| Recall={metricas_optimo['recall']}")

    # ── 5) Guardar modelo ─────────────────────────────────────────────────
    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, OUTPUT_PATH)
    print(f"[TRAIN] Modelo guardado en {OUTPUT_PATH}")

    # ── 6) Guardar ficha técnica (versionado del artefacto) ───────────────
    metadata = {
        "model_version": MODEL_VERSION,
        "algoritmo": mejor["familia"],
        "entrenado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": {
            "nombre": "Heart Disease Health Indicators (CDC/BRFSS 2015)",
            "fuente": "https://www.kaggle.com/datasets/alexteboul/heart-disease-health-indicators-dataset",
            "archivo": Path(csv_path).name,
            **info,
            "train_rows": int(len(X_train)),
            "test_rows": int(len(X_test)),
        },
        "features": FEATURE_COLUMNS,
        "target": "target (HeartDiseaseorAttack: 0=no, 1=si)",
        "nota_edad": "La columna 'edad' del modelo usa el codigo CDC 1-13 (no anios reales).",
        "hiperparametros": mejor["parametros"],
        "validacion_cruzada": {
            "metodo": "RandomizedSearchCV",
            "scoring": list(SEARCH_SCORING.keys()),
            "folds": CV_FOLDS,
            "candidatos_por_familia": SEARCH_ITER,
            "resultados_por_familia": resultados,
        },
        "metricas_test_umbral_0.50": metricas_default,
        "metricas_test_umbral_optimo": metricas_optimo,
        "umbral_decision": {
            "default": 0.50,
            "f1_optimo": round(float(umbral_optimo), 4),
        },
        "umbrales_clasificacion_clinica": CLASSIFICATION_THRESHOLDS,
        "distribucion_triaje_test": distribucion,
        "restriccion_ponderacion": {
            "aplicada": True,
            "detalle": {
                "RandomForest": "class_weight='balanced'",
                "XGBoost": f"scale_pos_weight={scale_pos_weight}",
            },
            "motivo": (
                "La API aplica umbrales clínicos fijos (0.30/0.60); se pondera la "
                "clase positiva para mantener una escala de riesgo útil para el triaje."
            ),
        },
        "librerias": {
            "scikit-learn": sklearn.__version__,
            "xgboost": xgboost.__version__,
            "pandas": pd.__version__,
            "joblib": joblib.__version__,
        },
    }
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"[TRAIN] Ficha tecnica guardada en {METADATA_PATH}")
    print("[TRAIN] Listo. Reinicia uvicorn y prueba POST /api/v1/evaluaciones/")


if __name__ == "__main__":
    csv = sys.argv[1] if len(sys.argv) > 1 else "heart_disease_health_indicators_BRFSS2015.csv"
    main(csv)
