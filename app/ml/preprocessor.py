"""
ARCHIVO 06 de 09 | Acomodamos las respuestas antes de calcular.
Vienes de: app/ml/model_loader.py (archivo 05).
Muestra mapear_edad_cdc y preprocess: 55 años pasan a grupo 8.
Después abre: app/ml/predictor.py (archivo 07).

Aquí acomodamos las nueve respuestas antes de entregarlas al modelo.

Comprobamos que estén presentes, revisamos edad y salud general, convertimos
la edad a su grupo y armamos una tabla de una fila con el orden correcto.
Los sí/no ya vienen como 1/0 desde evaluacion_mapper.py.

El modelo aprendió con grupos de edad. Por eso 55 años se convierten en el
grupo 8 (55 a 59 años), en lugar de enviar el número 55 directamente.
"""
import pandas as pd
from typing import Dict


# Estas son las nueve respuestas y el orden que el modelo espera recibir.
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
    Busca a qué grupo pertenece la edad, siguiendo los grupos de la encuesta.

    1=18-24, 2=25-29, 3=30-34, 4=35-39, 5=40-44, 6=45-49,
    7=50-54, 8=55-59, 9=60-64, 10=65-69, 11=70-74, 12=75-79, 13=80+.

    Ejemplo: 55 años devuelve 8. La tabla usada para entrenar ya trae esos grupos.
    Esta función también mete a menores de 18 en el grupo 1; no los rechaza.
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


# EXPO-ML 09 | Preparamos las respuestas: 55 años pasan a grupo 8.
# Después el modelo calcula el puntaje en predictor.py, EXPO-ML 10.
def preprocess(data: Dict) -> pd.DataFrame:
    """
    Recibe las nueve respuestas y devuelve una tabla lista para calcular.
    Por ejemplo, edad=55 pasa a edad=8 y los demás datos conservan su valor.
    La tabla tiene una fila por evaluación y las columnas de FEATURE_COLUMNS.
    Si falta un dato o falla uno de los rangos revisados, avisa con ValueError.
    """

    # Primero comprobamos que estén las nueve respuestas. Si Pydantic ya rellenó
    # un dato omitido con False o 3, aquí no podemos distinguirlo de una respuesta real.
    missing = [col for col in FEATURE_COLUMNS if col not in data]
    if missing:
        raise ValueError(f"Faltan variables predictoras: {missing}")

    # Revisamos estos dos rangos. Los tipos y los sí/no se comprueban antes en
    # EvaluacionCreate; aquí no se rellenan datos vacíos ni se revisan todos los tipos.
    if not (1 <= data["edad"] <= 120):
        raise ValueError("Edad fuera de rango válido (1-120)")
    if not (1 <= data["salud_general"] <= 5):
        raise ValueError("Salud general fuera de rango (1-5)")

    # La tabla de entrenamiento ya tenía grupos de edad; convertimos los años
    # del paciente a esos mismos grupos. Por ejemplo: 55 -> 8.
    edad_cdc = mapear_edad_cdc(data["edad"])

    # Nos quedamos con las nueve entradas en orden. Para edad usamos el grupo;
    # para las otras ocho conservamos la respuesta recibida.
    row = {
        col: (edad_cdc if col == "edad" else data[col])
        for col in FEATURE_COLUMNS
    }

    # Armamos una tabla de una fila: representa esta evaluación del paciente.
    return pd.DataFrame([row], columns=FEATURE_COLUMNS)
