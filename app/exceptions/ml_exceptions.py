"""
ml_exceptions.py — EXCEPCIONES ESPECÍFICAS DEL MÓDULO ML

Jerarquía de excepciones:
  MLException (base)
    ├── ModelNotFoundError  → El archivo .joblib no existe
    ├── ModelLoadError      → Error al cargar el modelo
    ├── PredictionError     → Error durante la predicción
    └── PreprocessingError  → Error al limpiar los datos

¿Por qué excepciones personalizadas?
Porque cuando algo falla en el pipeline de ML, necesitamos saber
EXACTAMENTE qué falló para diagnosticar rápido:
  - ¿No se encontró el modelo? → Verificar la ruta en .env
  - ¿Error al cargar? → El archivo está corrupto o corrupto
  - ¿Error al predecir? → Los datos de entrada son incorrectos
  - ¿Error de predicción? → El modelo falló internamente

Estas excepciones se capturan en los endpoints y se convierten
en errores HTTP claros para el frontend.
"""


class MLException(Exception):
    """
    Excepción BASE para todos los errores de ML.
    Permite capturar cualquier error de ML con un solo except.
    """
    pass


class ModelNotFoundError(MLException):
    """
    El archivo .joblib del modelo no existe en la ruta configurada.
    Causa común: no se ha entrenado el modelo, o la ruta en .env es incorrecta.
    """
    pass


class ModelLoadError(MLException):
    """
    Error al cargar el modelo desde disco.
    Causa común: el archivo .joblib está corrupto o incompleto.
    """
    pass


class PredictionError(MLException):
    """
    Error durante la ejecución de la predicción.
    Causa común: los datos de entrada no coinciden con las features del modelo.
    """
    pass


class PreprocessingError(MLException):
    """
    Error al preprocesar los datos de entrada.
    Causa común: faltan variables predictoras o los rangos son inválidos.
    """
    pass
