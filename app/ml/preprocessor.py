"""
preprocessor.py — LIMPIEZA Y VALIDACIÓN DE INPUTS PARA EL MODELO

Este módulo transforma datos crudos del formulario en un DataFrame
de pandas listo para que el modelo ML lo procese.

RESPONSABILIDADES:
  - Validar que no falten variables predictoras
  - Validar rangos (edad 1-120, salud_general 1-5)
  - Ordenar las columnas en el orden exacto que espera el modelo
  - Convertir booleans a números (el modelo espera ints, no bools)

NO conoce el modelo, NO toca la BD, NO conoce FastAPI.
Solo limpia y ordena datos → retorna DataFrame.
"""
import pandas as pd
from typing import Dict


# Orden EXACTO de columnas que el modelo fue entrenado a esperar.
# Si este orden cambia, las predicciones serán incorrectas.
# Este orden se documenta y se prueba en tests unitarios.
FEATURE_COLUMNS = [
    "edad",
    "presion_alta",
    "colesterol_alto",
    "tabaquismo",
    "actividad_fisica",
    "antecedente_acv",
    "diabetes",
    "salud_general",
    "dificultad_para_caminar",
]


def preprocess(data: Dict) -> pd.DataFrame:
    """
    Convierte un diccionario de datos crudos en un DataFrame
    listo para el modelo.

    Parámetros:
      data: dict con las variables predictoras
            Ej: {"edad": 55, "presion_alta": 1, ...}

    Retorna:
      pd.DataFrame con una fila y las columnas en orden correcto

    Excepciones:
      ValueError si faltan columnas o los rangos son inválidos
    """
    # --- PASO 1: Validar que no falten columnas ---
    missing = [col for col in FEATURE_COLUMNS if col not in data]
    if missing:
        raise ValueError(f"Faltan variables predictoras: {missing}")
    # Ejemplo de error: "Faltan variables predictoras: ['edad', 'diabetes']"

    # --- PASO 2: Validar rangos de valores ---
    if not (1 <= data["edad"] <= 120):
        raise ValueError("Edad fuera de rango válido (1-120)")
    if not (1 <= data["salud_general"] <= 5):
        raise ValueError("Salud general fuera de rango (1-5)")

    # --- PASO 3: Extraer y ordenar las columnas ---
    row = {col: data[col] for col in FEATURE_COLUMNS}
    # Crea un dict nuevo SOLO con las columnas del modelo,
    # en el orden EXACTO que el modelo espera.
    # Esto descarta automáticamente paciente_id y otros campos extra.

    # --- PASO 4: Convertir a DataFrame ---
    return pd.DataFrame([row], columns=FEATURE_COLUMNS)
    # pd.DataFrame con UNA fila (una evaluación) y N columnas
    # Este es el formato que espera model.predict_proba()
