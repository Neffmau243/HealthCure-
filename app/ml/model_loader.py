"""
ARCHIVO 05 de 09 | Abrimos el modelo que ya aprendió.
Vienes de: app/mappers/evaluacion_mapper.py (archivo 04).
Muestra load_model(): abre el archivo o reutiliza el modelo ya cargado.
Después abre: app/ml/preprocessor.py (archivo 06).

Aquí recuperamos el modelo que ya fue entrenado.

La primera vez se abre el archivo .joblib y se deja el modelo en memoria.
Después se reutiliza para evitar abrir el archivo en cada evaluación.
Cada proceso del servidor conserva su propia copia. Si dos llamadas llegan
al mismo tiempo al principio, no hay un bloqueo que coordine esa primera carga.

Este archivo carga lo aprendido; no enseña de nuevo al modelo.
"""
import joblib
from pathlib import Path
from app.core.config import get_settings
from app.exceptions.ml_exceptions import ModelNotFoundError, ModelLoadError

# Aquí conservamos el modelo una vez abierto; None significa que aún no se cargó.
_model_instance = None


# EXPO-ML 08 | Recuperamos el modelo que ya aprendió fuera de la consulta.
# Después volvemos a predictor.py para preparar las respuestas: EXPO-ML 09.
def load_model():
    """
    Devuelve el modelo listo para usar.
    Si ya está cargado, lo reutiliza. Si todavía no, busca la ruta indicada en
    MODEL_PATH y abre el archivo. Si falta o no se puede leer, informa el error.
    """
    global _model_instance

    # Si ya lo tenemos listo, lo devolvemos sin volver a abrir el archivo.
    if _model_instance is not None:
        return _model_instance

    # Buscamos la ruta del modelo en la configuración de la aplicación.
    settings = get_settings()
    model_path = Path(settings.MODEL_PATH)

    # Si el archivo no existe, avisamos en lugar de inventar un resultado.
    if not model_path.exists():
        raise ModelNotFoundError(
            f"Modelo no encontrado en: {model_path}. "
            f"Entrena el modelo primero con train.py"
        )

    # joblib.load recupera lo aprendido desde el archivo. No vuelve a entrenar.
    # Debe ser un archivo de confianza, porque joblib puede cargar código Python.
    try:
        _model_instance = joblib.load(model_path)

    except Exception as e:
        raise ModelLoadError(f"Error al cargar el modelo: {e}")

    return _model_instance


def reload_model():
    """
    Olvida el modelo que estaba en memoria y vuelve a abrir su archivo.
    Sirve después de reemplazar el modelo entrenado. Su ficha se recarga aparte
    con reload_metadata(); reiniciar los procesos del servidor renueva ambos.
    """

    global _model_instance
    _model_instance = None
    return load_model()
