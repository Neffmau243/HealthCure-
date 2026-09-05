"""
entrenar_modelo.py — ENTRENA EL MODELO ML Y LO GUARDA COMO .joblib

Entrena un RandomForest con el dataset "Heart Disease Health Indicators"
(CDC/BRFSS 2015, descargado de Kaggle) y guarda el modelo en la ruta que
el backend espera: app/resources/modelo_cardiaco.joblib

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
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, roc_auc_score, f1_score, confusion_matrix,
)

# Columnas exactas que el backend espera + la variable objetivo.
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

OUTPUT_PATH = "app/resources/modelo_cardiaco.joblib"


def main(csv_path: str):
    print(f"[TRAIN] Leyendo dataset: {csv_path}")

    # --- Cargar CSV ---
    df = pd.read_csv(csv_path)

    # --- Verificar que tenga las columnas esperadas ---
    faltantes = [c for c in COLUMNAS if c not in df.columns]
    if faltantes:
        print(f"[ERROR] El CSV no tiene las columnas: {faltantes}")
        print("Asegurate de descargar 'heart_disease_health_indicators_BRFSS2015.csv'")
        sys.exit(1)

    # --- Seleccionar y renombrar (mantiene el ORDEN de COLUMNAS) ---
    df_ml = df[list(COLUMNAS.keys())].rename(columns=COLUMNAS)

    # --- Normalizar diabetes a 0/1 ---
    # BRFSS usa 2 = prediabetes/solo embarazo. La API solo manda 0/1,
    # asi que el modelo debe aprender con 0/1 para no ver valores que nunca vera.
    df_ml["diabetes"] = (df_ml["diabetes"] > 0).astype(int)

    # GenHlth (1-5: 1=excelente ... 5=mala) ya viene como el backend lo envia.
    # HighBP/HighChol/Smoker/... ya son 0/1 como los envia el backend.

    X = df_ml.drop(columns=["target"])
    y = df_ml["target"]

    print(f"[TRAIN] Filas: {len(df_ml)} | Positivos: {y.sum()} ({y.mean()*100:.1f}%)")

    # --- Dividir (estratificado por clase, el dataset esta desbalanceado) ---
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # --- Entrenar Random Forest ---
    # class_weight="balanced": compensa que solo ~9% tiene enfermedad cardiaca
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    # --- Evaluar ---
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    print("[TRAIN] Metricas sobre el 20% reservado:")
    print(f"  Accuracy:      {accuracy_score(y_test, y_pred):.4f}")
    print(f"  F1:            {f1_score(y_test, y_pred):.4f}")
    print(f"  ROC AUC:       {roc_auc_score(y_test, y_proba):.4f}")
    print(f"  Matriz conf.:  {confusion_matrix(y_test, y_pred).tolist()}")

    # --- Guardar donde el backend lo busca ---
    joblib.dump(model, OUTPUT_PATH)
    print(f"[TRAIN] Modelo guardado en {OUTPUT_PATH}")
    print("[TRAIN] Listo. Reinicia uvicorn y prueba POST /api/v1/evaluaciones/")


if __name__ == "__main__":
    # Argumento opcional: ruta del CSV
    csv = sys.argv[1] if len(sys.argv) > 1 else "heart_disease_health_indicators_BRFSS2015.csv"
    main(csv)
