"""
ARCHIVO 07 de 09 | AQUÍ SE CALCULA EL PUNTAJE DE RIESGO Y SE ELIGE EL NIVEL
Vienes de: app/ml/preprocessor.py (archivo 06).
Muestra predict_proba dentro de predict y luego la función _classify.
Después abre: app/ml/metadata.py (archivo 08), para ver de dónde salen
la versión del modelo y los límites que acabamos de usar.

¿QUÉ HACE ESTE ARCHIVO?
========================
Es el "cerebro" de la predicción. Recibe las 9 respuestas del paciente,
se las pasa al modelo de ML (XGBoost), y obtiene un puntaje de riesgo.
Luego clasifica ese puntaje en bajo/moderado/alto y devuelve el resultado.

Este archivo NO guarda en MySQL (eso lo hace evaluacion_service.py).
Este archivo NO muestra en la pantalla (eso lo hace el frontend).
Solo calcula y devuelve el resultado.

FLUJO:
  1. Cargar el modelo entrenado (.joblib)
  2. Preparar los datos del paciente (preprocess)
  3. Calcular el puntaje con predict_proba
  4. Clasificar: bajo / moderado / alto
  5. Devolver el resultado con la versión del modelo

NOTA IMPORTANTE:
  El campo "probabilidad" NO es un porcentaje clínico comprobado.
  Es un puntaje interno del modelo (índice 0-1) que sirve para triaje.
"""
from typing import Dict
from app.ml.model_loader import load_model
from app.ml.preprocessor import preprocess
from app.ml.metadata import get_model_version, get_classification_thresholds
from app.schemas.evaluacion import PredictionResult, ClasificacionEnum
from app.exceptions.ml_exceptions import PredictionError


def predict(data: Dict) -> PredictionResult:
    """
    FUNCIÓN PRINCIPAL: recibe las 9 respuestas del paciente y devuelve
    el puntaje de riesgo, la clasificación y la versión del modelo.

    Parámetro:
        data: diccionario con las 9 respuestas del paciente
              Ej: {"edad": 55, "presion_alta": 1, "colesterol_alto": 0, ...}

    Retorna:
        PredictionResult con:
        - probabilidad: número entre 0 y 1 (ej: 0.787930)
        - clasificacion: "bajo", "moderado" o "alto"
        - modelo_version: "2.0.0"

    Si algo falla, lanza PredictionError con un mensaje descriptivo.
    """

    # ================================================================
    # PASO 1: Cargar el modelo de ML ya entrenado
    # ================================================================
    # load_model() abre el archivo modelo_cardiaco.joblib la primera vez
    # y lo deja en memoria. Las siguientes veces lo reutiliza sin abrir.
    # Si el archivo no existe o está corrupto, lanza error.
    try:
        model = load_model()
    except Exception as e:
        raise PredictionError(f"No se pudo cargar el modelo: {e}")

    # ================================================================
    # PASO 2: Preparar los datos del paciente
    # ================================================================
    # preprocess() convierte las respuestas del paciente en un DataFrame
    # con el formato exacto que el modelo espera (9 columnas en orden).
    # Por ejemplo: convierte la edad en años al grupo CDC (1-13).
    try:
        df = preprocess(data)

        # ============================================================
        # PASO 3: Calcular el puntaje de riesgo (EL PORCENTAJE)
        # ============================================================
        # predict_proba devuelve las probabilidades de cada clase:
        #   [0] → probabilidad de NO tener enfermedad (clase 0)
        #   [1] → probabilidad de SÍ tener enfermedad (clase 1)
        #
        # Nos interesa la clase [1] → el riesgo cardíaco.
        #
        # Ejemplo: si devuelve [[0.21, 0.79]], el puntaje es 0.79
        # Eso significa que el modelo le asigna 79% de riesgo a este paciente.
        #
        # NOTA: Es un índice del modelo, NO una probabilidad clínica real
        # de que el paciente vaya a tener un infarto en el futuro.
        probabilidad = float(model.predict_proba(df)[0][1])

        # ============================================================
        # PASO 4: Clasificar el puntaje en un nivel
        # ============================================================
        # _classify toma el número (ej: 0.79) y decide si es:
        #   - "bajo"     → si es menor a 0.30
        #   - "moderado" → si está entre 0.30 y 0.60
        #   - "alto"     → si es mayor o igual a 0.60
        clasificacion = _classify(probabilidad)

    except Exception as e:
        raise PredictionError(f"Error en la predicción: {e}")

    # ================================================================
    # PASO 5: Devolver el resultado completo
    # ================================================================
    # Redondeamos a 6 decimales para guardar en MySQL (DECIMAL(7,6)).
    # La clasificación ya se calculó con el número completo (sin redondear).
    # La versión del modelo viene del archivo metadata.json.
    return PredictionResult(
        probabilidad=round(probabilidad, 6),
        clasificacion=clasificacion,
        modelo_version=get_model_version(),
    )


# ====================================================================
# FUNCIÓN AUXILIAR: clasifica el puntaje en bajo / moderado / alto
# ====================================================================
# Los límites 0.30 y 0.60 vienen del archivo metadata.json.
# Son umbrales clínicos fijos definidos por el equipo médico.
#
# IMPORTANTE:
#   - El umbral F1 óptimo (0.7026) del entrenamiento NO se usa aquí.
#   - Estos niveles son para triaje, no prueban urgencia clínica por sí solos.
#   - Después se añaden textos y colores en generar_triaje_clinico (EXPO-ML 12).
def _classify(probabilidad: float) -> ClasificacionEnum:
    """
    Clasifica el puntaje de riesgo en uno de tres niveles.

    Parámetro:
        probabilidad: número entre 0 y 1 (ej: 0.513150)

    Retorna:
        ClasificacionEnum.bajo     → si probabilidad < 0.30
        ClasificacionEnum.moderado → si 0.30 <= probabilidad < 0.60
        ClasificacionEnum.alto    → si probabilidad >= 0.60

    Si faltan los umbrales en el metadata, usa 0.30 y 0.60 por defecto.
    """
    # Obtener los umbrales desde el archivo metadata.json
    umbrales = get_classification_thresholds()

    # Comparar el puntaje contra los límites
    if probabilidad < umbrales["bajo_max"]:
        # Menos de 0.30 → riesgo bajo (verde)
        return ClasificacionEnum.bajo
    elif probabilidad < umbrales["moderado_max"]:
        # Entre 0.30 y 0.60 → riesgo moderado (amarillo)
        return ClasificacionEnum.moderado
    else:
        # 0.60 o más → riesgo alto (rojo)
        return ClasificacionEnum.alto
