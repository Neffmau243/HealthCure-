"""Contrato del CSV transformado de Kaggle; Age ya contiene códigos CDC."""
import numpy as np
import pandas as pd

from app.ml.preprocessor import FEATURE_COLUMNS

COLUMNAS = {
    "Age": "edad", "HighBP": "presion_alta", "HighChol": "colesterol_alto",
    "Smoker": "tabaquismo", "PhysActivity": "actividad_fisica",
    "Stroke": "antecedente_acv", "Diabetes": "diabetes",
    "GenHlth": "salud_general", "DiffWalk": "dificultad_para_caminar",
    "HeartDiseaseorAttack": "target",
}


def preparar_dataframe(df):
    requeridas = [*COLUMNAS, "Sex"]
    faltantes = set(requeridas) - set(df.columns)
    if faltantes:
        raise ValueError(f"Columnas faltantes: {sorted(faltantes)}")
    valores = df[requeridas].to_numpy(dtype=float)
    if not np.isfinite(valores).all():
        raise ValueError("El CSV contiene valores ausentes o no finitos")
    rangos = {col: {0, 1} for col in requeridas}
    rangos.update(Age=set(range(1, 14)), GenHlth=set(range(1, 6)), Diabetes={0, 1, 2})
    for col, permitidos in rangos.items():
        if not df[col].isin(permitidos).all():
            raise ValueError(f"Codificación inválida en {col}")
    datos = df[list(COLUMNAS)].rename(columns=COLUMNAS).astype(int)
    # Kaggle: 0=ninguna, 1=prediabetes, 2=diabetes; la API agrupa >0.
    datos["diabetes"] = (datos["diabetes"] > 0).astype(int)
    return datos[FEATURE_COLUMNS], datos["target"], df["Sex"].astype(int)


def cargar_dataset(csv_path):
    df = pd.read_csv(csv_path)
    X, y, _ = preparar_dataframe(df)
    return X, y, {
        "n_rows": len(y), "n_features": len(FEATURE_COLUMNS),
        "positive_rate": round(float(y.mean()), 4), "n_positive": int(y.sum()),
    }
