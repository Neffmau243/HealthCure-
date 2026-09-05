"""
preprocessor.py — LIMPIEZA Y VALIDACIÓN DE INPUTS PARA EL MODELO

Este módulo transforma datos crudos del formulario en un DataFrame
de pandas listo para que el modelo ML lo procese.

RESPONSABILIDADES:
  - Validar que no falten variables predictoras
  - Validar rangos (edad 1-120, salud_general 1-5)
  - Convertir la EDAD de años reales (55) al rango CDC 1-13 que usa
    el dataset BRFSS de entrenamiento (ver mapear_edad_cdc)
  - Ordenar las columnas en el orden exacto que espera el modelo
  - Convertir booleans a números (el modelo espera ints, no bools)

NO conoce el modelo, NO toca la BD, NO conoce FastAPI.
Solo limpia y ordena datos → retorna DataFrame.

IMPORTANTE: entrenar_modelo.py (raiz del proyecto) entrena con la columna
Age del CSV que YA viene codificada 1-13. Por eso la conversión de años →
1-13 vive AQUI (lado inferencia) y NO en el entrenamiento.
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


def mapear_edad_cdc(edad_anios: int) -> int:
    """
    Convierte la edad en AÑOS (ej: 55) al codigo 1-13 del CDC/BRFSS.

    El dataset de entrenamiento codifica la edad en 13 rangos:
        1=18-24, 2=25-29, 3=30-34, 4=35-39, 5=40-44, 6=45-49,
        7=50-54, 8=55-59, 9=60-64, 10=65-69, 11=70-74, 12=75-79, 13=80+

    Ejemplo: mapear_edad_cdc(55) -> 8

    DEBE ser identica a la logica con la que se entreno el modelo
    (el CSV ya viene codificado 1-13; el formulario manda años reales).
    """
    if edad_anios < 25:
        return 1
    elif edad_anios <= 29:
        return 2
    elif edad_anios <= 34:
        return 3
    elif edad_anios <= 39:
        return 4
    elif edad_anios <= 44:
        return 5
    elif edad_anios <= 49:
        return 6
    elif edad_anios <= 54:
        return 7
    elif edad_anios <= 59:
        return 8
    elif edad_anios <= 64:
        return 9
    elif edad_anios <= 69:
        return 10
    elif edad_anios <= 74:
        return 11
    elif edad_anios <= 79:
        return 12
    else:
        return 13


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

    # --- PASO 3: Convertir la edad de AÑOS al codigo CDC 1-13 ---
    # El modelo se entreno con Age del BRFSS (ya codificada 1-13).
    # El formulario manda la edad real (55) -> aqui se convierte a 8.
    edad_cdc = mapear_edad_cdc(data["edad"])

    # --- PASO 4: Extraer y ordenar las columnas ---
    row = {
        col: (edad_cdc if col == "edad" else data[col])
        for col in FEATURE_COLUMNS
    }
    # Crea un dict nuevo SOLO con las columnas del modelo,
    # en el orden EXACTO que el modelo espera.
    # Esto descarta automáticamente paciente_id y otros campos extra.

    # --- PASO 5: Convertir a DataFrame ---
    return pd.DataFrame([row], columns=FEATURE_COLUMNS)
    # pd.DataFrame con UNA fila (una evaluación) y N columnas
    # Este es el formato que espera model.predict_proba()
