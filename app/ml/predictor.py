"""
predictor.py — EJECUTA EL MODELO ML Y RETORNA LA PREDICCIÓN

Este módulo es el "cerebro" del sistema de predicción.
Su única responsabilidad es:
  1. Recibir datos crudos
  2. Preprocesarlos
  3. Pasarlos al modelo
  4. Retornar probabilidad + clasificación

NO toca la base de datos.
NO conoce request/response schemas.
NO conoce FastAPI.
Solo recibe datos → devuelve predicción.
"""
from typing import Dict
from app.ml.model_loader import load_model
from app.ml.preprocessor import preprocess
from app.schemas.evaluacion import PredictionResult, ClasificacionEnum
from app.exceptions.ml_exceptions import PredictionError


# Versión del modelo (se actualiza cuando se reentrena)
MODEL_VERSION = "1.0.0"


def predict(data: Dict) -> PredictionResult:
    """
    Flujo completo de predicción:

    1. load_model() → obtiene el modelo de la caché (singleton)
    2. preprocess(data) → limpia y ordena los datos
    3. model.predict_proba(df) → calcula la probabilidad
    4. _classify(probabilidad) → convierte a nivel de riesgo

    Parámetros:
      data: dict con las variables predictoras
            Ej: {"edad": 55, "presion_alta": 1, "colesterol_alto": 1, ...}

    Retorna:
      PredictionResult(probabilidad=0.73, clasificacion="alto", ...)

    Excepciones:
      PredictionError si algo falla (modelo no encontrado, datos inválidos, etc.)
    """
    # 1. Cargar el modelo (de la caché o del disco)
    try:
        model = load_model()
    except Exception as e:
        raise PredictionError(f"No se pudo cargar el modelo: {e}")

    # 2. Preprocesar y predecir
    try:
        # 2a. Limpiar y ordenar los datos
        df = preprocess(data)
        # df es un DataFrame de pandas con las columnas en orden correcto

        # 2b. Ejecutar la predicción
        probabilidad = float(model.predict_proba(df)[0][1])
        # predict_proba retorna [[prob_no_enfermo, prob_enfermo]]
        # [0][1] = tomamos la probabilidad de ENFERMEDAD (clase 1)

        # 2c. Convertir probabilidad a nivel de riesgo
        clasificacion = _classify(probabilidad)
    except Exception as e:
        raise PredictionError(f"Error en la predicción: {e}")

    return PredictionResult(
        probabilidad=round(probabilidad, 6),  # 6 decimales
        clasificacion=clasificacion,
        modelo_version=MODEL_VERSION,
    )


def _classify(probabilidad: float) -> ClasificacionEnum:
    """
    Convierte una probabilidad (0.0-1.0) en un nivel de riesgo legible.

    Umbrales (ajustables según el modelo entrenado):
      - < 0.30 (30%)  → bajo riesgo
      - 0.30-0.60 (30-60%) → riesgo moderado
      - > 0.60 (60%)  → alto riesgo

    NOTA: Estos umbrales son ARBITRARIOS para el MVP.
    En producción se deberían ajustar con análisis de ROC curve,
    Youden's J statistic, o criterio clínico del equipo médico.
    """
    if probabilidad < 0.30:
        return ClasificacionEnum.bajo
    elif probabilidad < 0.60:
        return ClasificacionEnum.moderado
    else:
        return ClasificacionEnum.alto
