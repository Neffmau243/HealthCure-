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
from app.ml.metadata import get_model_version, get_classification_thresholds
from app.schemas.evaluacion import PredictionResult, ClasificacionEnum
from app.exceptions.ml_exceptions import PredictionError


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
    # Ruta de exposición: load_model (08) -> preprocess (09) -> inferencia (10).
    # El entrenamiento se explica aparte en entrenar_modelo.py, EXPO-ML E1 a E6.
    try:
        model = load_model()
    except Exception as e:
        raise PredictionError(f"No se pudo cargar el modelo: {e}")

    # 2. Preprocesar y predecir
    try:
        # 2a. Limpiar y ordenar los datos
        df = preprocess(data)
        # df es un DataFrame de pandas con las columnas en orden correcto

        # EXPO-ML 10 | Aquí se ejecuta el ML: los árboles calculan el puntaje.
        # predict_proba devuelve dos valores por fila; [0][1] toma la clase 1.
        # Esa clase corresponde al antecedente cardiovascular declarado del dataset.
        # Con el modelo actual ponderado, el valor se interpreta como índice;
        # no como porcentaje clínico calibrado ni predicción de un infarto futuro.
        probabilidad = float(model.predict_proba(df)[0][1])

        # 2c. Convertir probabilidad a nivel de riesgo
        clasificacion = _classify(probabilidad)
    except Exception as e:
        raise PredictionError(f"Error en la predicción: {e}")

    return PredictionResult(
        probabilidad=round(probabilidad, 6),  # 6 decimales
        clasificacion=clasificacion,
        # Versión leída de la ficha técnica (app/ml/metadata.py);
        # NO hardcodeada → reentrenar actualiza la versión sin tocar código.
        modelo_version=get_model_version(),
    )


# EXPO-ML 11 | Convertir el puntaje binario en tres bandas del producto.
# Se leen los cortes de metadata.py: actualmente 0.30 y 0.60.
# Ejemplo: 0.513150 -> moderado. El umbral F1=0.7026 no se usa en este paso.
# Los colores no son tres clases aprendidas por XGBoost ni urgencias validadas.
# Sigue create_to_model -> generar_triaje_clinico, EXPO-ML 12.
def _classify(probabilidad: float) -> ClasificacionEnum:
    """
    Convierte una probabilidad (0.0-1.0) en un nivel de riesgo legible.

    Los umbrales NO están hardcodeados: se leen de la ficha técnica del
    modelo (app/ml/metadata.py), con fallback a los valores del MVP:
      - < 0.30 (30%)        → bajo riesgo
      - 0.30 - 0.60 (30-60%) → riesgo moderado
      - >= 0.60 (60%)       → alto riesgo

    Esto mantiene coherentes el entrenamiento (que guarda los umbrales en
    la metadata) y la inferencia (que los aplica). Si no hay ficha técnica,
    se comporta igual que antes (0.30 / 0.60).
    """
    umbrales = get_classification_thresholds()
    if probabilidad < umbrales["bajo_max"]:
        return ClasificacionEnum.bajo
    elif probabilidad < umbrales["moderado_max"]:
        return ClasificacionEnum.moderado
    else:
        return ClasificacionEnum.alto
