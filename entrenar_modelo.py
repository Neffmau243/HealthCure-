"""
ARCHIVO 01 de 09 | Empezamos aquí: cómo aprende el modelo.
Muestra main(), siguiendo los comentarios E1 a E6.
Después abre: app/schemas/evaluacion.py (archivo 02).

Aquí se enseña al modelo usando ejemplos que ya tienen una respuesta conocida.

El archivo de datos contiene respuestas de una encuesta y señala si la persona
declaró antecedentes de enfermedad coronaria o infarto. Elegimos nueve datos,
comparamos Random Forest con XGBoost y guardamos el modelo que resulte elegido.

Para ejecutarlo desde la carpeta del proyecto:
python entrenar_modelo.py ruta/al/archivo.csv

Esto se hace aparte, antes de evaluar pacientes. Ejecutarlo reemplaza el modelo
y su ficha en app/resources. Después hay que reiniciar el servidor para usarlos.

La edad del archivo ya está representada por grupos del 1 al 13. Aquí se deja
así; preprocessor.py convierte los años del paciente a esos mismos grupos.
El modelo aprende sobre antecedentes declarados, no sobre cuándo ocurrirá un infarto.
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


# Estos son los nombres originales de la tabla y los nombres que usa la aplicación.
# El orden debe coincidir con FEATURE_COLUMNS en app/ml/preprocessor.py.
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


# Aquí se guardarán el modelo entrenado y su ficha.
OUTPUT_PATH = "app/resources/modelo_cardiaco.joblib"
METADATA_PATH = "app/resources/modelo_cardiaco_metadata.json"


MODEL_VERSION = "2.0.0"
# La semilla permite repetir la misma separación y búsqueda con los mismos datos.
RANDOM_STATE = 42
TEST_SIZE = 0.20
# Probamos alternando tres partes de los datos de entrenamiento.
CV_FOLDS = 3
# Se probarán ocho configuraciones de cada método.
SEARCH_ITER = 8
SEARCH_SCORING = {"roc_auc": "roc_auc", "pr_auc": "average_precision"}


# Límites para mostrar bajo, moderado y alto. Se guardan en la ficha.
# No son límites aprendidos durante fit ni prueban un nivel de urgencia.
CLASSIFICATION_THRESHOLDS = {"bajo_max": 0.30, "moderado_max": 0.60}


def cargar_dataset(csv_path: str) -> tuple[pd.DataFrame, pd.Series, dict]:
    """
    Lee la tabla de ejemplos y comprueba que tenga las columnas necesarias.
    Devuelve X (los nueve datos para calcular), y (la respuesta conocida de cada
    ejemplo) e info (cantidad de registros y de respuestas positivas).
    """
    print(f"[TRAIN] Leyendo dataset: {csv_path}")
    df = pd.read_csv(csv_path)

    faltantes = [c for c in COLUMNAS if c not in df.columns]
    if faltantes:
        print(f"[ERROR] El CSV no tiene las columnas: {faltantes}")
        print("Asegurate de descargar 'heart_disease_health_indicators_BRFSS2015.csv'")
        sys.exit(1)

    # Elegimos las columnas necesarias y las renombramos, conservando su orden.
    df_ml = df[list(COLUMNAS.keys())].rename(columns=COLUMNAS)

    # Cualquier valor mayor que cero pasa a 1; los demás pasan a 0.
    # Se pierde la diferencia entre las categorías originales. Si cambiamos la
    # tabla de origen, hay que revisar qué significa cada código antes de agruparlo.
    df_ml["diabetes"] = (df_ml["diabetes"] > 0).astype(int)

    # X contiene los datos para calcular; y contiene la respuesta que debe aprender.
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


def _espacios_busqueda(scale_pos_weight: float) -> dict:
    """
    Prepara los dos métodos y las configuraciones que vamos a probar.
    Por ejemplo, cuántos árboles usar y qué tan profundos pueden ser.

    Hay menos ejemplos con antecedente que sin él. Por eso damos más peso a los
    primeros durante el aprendizaje. Esto también cambia la escala del puntaje:
    no basta para interpretarlo como un porcentaje real de enfermedad.
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
    Prueba distintas configuraciones de Random Forest y XGBoost.
    Divide los datos de entrenamiento en tres partes: aprende con unas y comprueba
    con otra, alternándolas. Eso es la validación cruzada.
    Para cada método devuelve la configuración que obtuvo el mejor ROC AUC.
    """
    # Alternamos tres partes para aprender y comprobar. Conservamos una proporción
    # parecida de ejemplos con y sin antecedente en cada parte.
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    resultados = []

    for nombre, (estimador, espacio) in _espacios_busqueda(scale_pos_weight).items():
        print(f"[TRAIN] Buscando hiperparámetros de {nombre} "
              f"({SEARCH_ITER} candidatos x {CV_FOLDS} folds)...")
        # Probamos varias configuraciones. Aquí no se entrena automáticamente un
        # ganador final: main() lo hará después con la configuración elegida.
        search = RandomizedSearchCV(
            estimador, espacio,
            n_iter=SEARCH_ITER, scoring=SEARCH_SCORING, refit=False,
            cv=cv, random_state=RANDOM_STATE, n_jobs=-1,
        )
        search.fit(X_train, y_train)
        res = search.cv_results_

        # Elegimos por ROC AUC: mide qué tan bien se ordenan los dos grupos.
        # También guardamos average precision, llamada pr_auc en este código.
        # ROC AUC no es un porcentaje de aciertos.
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


def optimizar_umbral(y_true, proba) -> tuple[float, float]:
    """
    Busca qué límite da el mejor F1 al separar los puntajes en dos grupos.
    F1 combina cuántos positivos detectamos y cuántos de los señalados lo son.

    main() busca ese límite con los mismos datos donde después lo evalúa. Eso puede
    dar una impresión demasiado favorable: falta elegirlo con datos separados.
    Este límite no es el que usa la aplicación para sus tres colores.
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
    """
    Compara lo que devuelve el modelo con las respuestas que ya conocemos.
    El límite recibido decide desde qué puntaje marcamos un ejemplo como positivo.
    Devuelve las medidas de aciertos, errores y capacidad de separar los grupos.
    """
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
    Cuenta cuántos ejemplos quedan en bajo, moderado y alto.
    Sirve para ver si los resultados se concentran en algún nivel o si otro queda
    vacío. Tener casos en los tres niveles no demuestra que sean útiles en clínica.
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
    """
    Convierte los números de numpy a tipos que el archivo JSON puede guardar.
    También revisa los valores dentro de listas y diccionarios.
    """
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


def main(csv_path: str):

    # EXPO-ML E1 | Leemos los ejemplos con los que el modelo va a aprender.
    # X son las nueve entradas; y indica si se declaró el antecedente cardiovascular.
    # Este script se ejecuta aparte, no cuando registramos o evaluamos a un paciente.
    X, y, info = cargar_dataset(csv_path)

    # EXPO-ML E2 | Usamos 80% para aprender y reservamos 20% para probar.
    # stratify mantiene una proporción parecida de respuestas positivas en ambos.
    # random_state permite repetir la misma separación.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    print(f"[TRAIN] Train: {len(X_train)} | Test: {len(X_test)}")

    # Contamos ejemplos sin y con antecedente. Hay menos positivos, por eso
    # calculamos cuánto peso extra darles al entrenar XGBoost.
    neg, pos = int((y_train == 0).sum()), int((y_train == 1).sum())
    scale_pos_weight = round(neg / pos, 2)

    # EXPO-ML E3 | Comparamos Random Forest y XGBoost usando solo el grupo de
    # entrenamiento. Nos quedamos con el de mejor ROC AUC en esas pruebas.
    resultados = buscar_hiperparametros(X_train, y_train, scale_pos_weight)
    mejor = max(resultados, key=lambda r: r["cv_roc_auc"])
    print(f"[TRAIN] MEJOR FAMILIA: {mejor['familia']} "
          f"(CV ROC AUC={mejor['cv_roc_auc']})")

    # EXPO-ML E4 | Preparamos al ganador con la configuración elegida.
    # fit es la orden para aprender: aquí usa todo el grupo de entrenamiento.
    # Los ejemplos reservados para probar no entran en este aprendizaje.
    estimador_ganador = _espacios_busqueda(scale_pos_weight)[mejor["familia"]][0]
    model = estimador_ganador.set_params(**mejor["parametros"])
    model.fit(X_train, y_train)

    # EXPO-ML E5 | Pedimos resultados para los ejemplos reservados y buscamos
    # un límite que dé el mejor F1 para separar en dos respuestas.
    # Pendiente: ese límite se elige y se mide con los mismos datos de prueba,
    # lo que puede hacerlo parecer mejor de lo que es. Hay que usar datos separados.
    # La aplicación usa 0.30/0.60 para sus colores, no este límite de F1.
    proba_test = model.predict_proba(X_test)[:, 1]
    umbral_optimo, f1_optimo = optimizar_umbral(y_test, proba_test)
    print(f"[TRAIN] Umbral óptimo para F1: {umbral_optimo:.4f} (F1={f1_optimo:.4f})")

    # Contamos cuántos resultados quedan en cada nivel. Esto describe el reparto;
    # que haya casos en los tres niveles no demuestra que sean válidos en clínica.
    distribucion = distribucion_triaje(proba_test, CLASSIFICATION_THRESHOLDS)
    print(f"[TRAIN] Distribución de triaje en test (bandas 0.30/0.60): {distribucion}")
    if distribucion["alto"]["n"] == 0 or distribucion["moderado"]["n"] == 0:
        print("[WARN] Alguna banda del triaje quedó vacía: revisar ponderación/umbrales.")

    # Medimos con el límite fijo 0.50 y con el límite que acabamos de elegir.
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

    # EXPO-ML E6 | Guardamos lo que aprendió el modelo y luego escribimos su ficha.
    # Después la aplicación podrá abrirlo y calcular sin volver a entrenar.
    # El recorrido del paciente empieza en EXPO-ML 01; el modelo se carga en el 08.
    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, OUTPUT_PATH)
    print(f"[TRAIN] Modelo guardado en {OUTPUT_PATH}")

    # La ficha guarda versión, origen de los ejemplos, configuración y resultados.
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
