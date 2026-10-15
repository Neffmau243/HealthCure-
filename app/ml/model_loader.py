"""
model_loader.py — CARGADOR DE MODELO ML (SINGLETON)

Patrón Singleton: carga el archivo .joblib UNA sola vez en memoria
y lo reutiliza en cada predicción. Si no hiciera esto, tendríamos
que leer el archivo de disco en CADA request → terribly lento.

.modeljoblib es el modelo entrenado de Random Forest/XGBoost
que se guardó con joblib.dump() después del entrenamiento.

Flujo:
  1. Primera llamada → lee el archivo de disco, lo cachea en RAM
  2. Segunda llamada → retorna directamente el objeto en memoria
  3. Si el archivo no existe → lanza ModelNotFoundError
  4. Si hay error al cargar → lanza ModelLoadError
"""
import joblib
import hashlib
from pathlib import Path
from app.core.config import get_settings
from app.exceptions.ml_exceptions import ModelNotFoundError, ModelLoadError

_model_instance = None  # Variable global que cachea el modelo (singleton)


def load_model():
    """
    Retorna el modelo ML cargado. Lo cachea en memoria para no
    releer el archivo en cada request.

    Uso típico:
        model = load_model()  # Primera vez: lee disco. Después: retorna cache.
        prediction = model.predict_proba(data)
    """
    global _model_instance  # Accede a la variable global

    # Si ya está en memoria, retornarlo directamente (sin leer disco)
    if _model_instance is not None:
        return _model_instance

    settings = get_settings()
    model_path = Path(settings.MODEL_PATH)

    # Verificar que el archivo .joblib existe
    if not model_path.exists():
        raise ModelNotFoundError(
            f"Modelo no encontrado en: {model_path}. "
            "Restaura el artefacto versionado de la aplicación. "
            "entrenar_modelo.py genera candidatos offline y no los activa automáticamente."
        )

    # Cargar el modelo desde disco (primera y única vez)
    try:
        from app.ml.metadata import load_metadata
        meta = load_metadata()
        actual_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
        if meta.get("artifact_sha256") and meta["artifact_sha256"] != actual_hash:
            raise ValueError("El hash del modelo no corresponde a su metadata")
        model = joblib.load(model_path)
        from sklearn.calibration import CalibratedClassifierCV
        calibrated = isinstance(model, CalibratedClassifierCV)
        if calibrated != meta["model_version"].startswith("3."):
            raise ValueError("La calibración del artefacto no corresponde a su versión")
        model._healthcure_artifact_sha256 = actual_hash
        _model_instance = model
        # joblib.load() deserializa el objeto Python guardado con dump()
        # Retorna un estimador de scikit-learn/XGBoost
    except Exception as e:
        raise ModelLoadError(f"Error al cargar el modelo: {e}")

    return _model_instance


def reload_model():
    """
    Fuerza la recarga del modelo desde disco.
    Útil después de reentrenar el modelo con datos nuevos.

    Ejemplo:
        reload_model()  # Borra el cache y vuelve a leer el archivo
    """
    global _model_instance
    _model_instance = None  # Borra el cache
    from app.ml.metadata import reload_metadata
    reload_metadata()
    return load_model()     # Vuelve a cargar desde disco
