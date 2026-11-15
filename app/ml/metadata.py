"""
ARCHIVO 08 de 09 | Leemos la ficha del modelo y sus límites.
Vienes de: app/ml/predictor.py (archivo 07).
Muestra get_model_version y get_classification_thresholds.
Después abre: app/services/evaluacion_triaje_service.py (archivo 09).

Aquí se lee la ficha que acompaña al modelo entrenado.

El archivo .joblib guarda el modelo. El archivo _metadata.json guarda su
versión, cómo se entrenó, sus resultados y los límites para bajo/moderado/alto.
La ficha se conserva en memoria para no abrirla en cada evaluación.

Si falta o no se puede leer, se usan valores de respaldo. El contenido no
se revisa por completo: una ficha con campos mal escritos aún puede dar errores.
"""
import json
from pathlib import Path
from typing import Any, Dict

from app.core.config import get_settings


# Valores de respaldo cuando la ficha no proporciona esta información.
DEFAULT_MODEL_VERSION = "1.0.0"
DEFAULT_THRESHOLDS = {"bajo_max": 0.30, "moderado_max": 0.60}

# Aquí conservamos la ficha ya leída. None significa que aún no se intentó leer.
_metadata_cache: Dict[str, Any] | None = None


def _metadata_path() -> Path:
    """
    Busca la ficha junto al modelo, usando su mismo nombre.
    Por ejemplo, modelo_cardiaco.joblib -> modelo_cardiaco_metadata.json.
    """
    model_path = Path(get_settings().MODEL_PATH)
    return model_path.with_name(f"{model_path.stem}_metadata.json")


def load_metadata() -> Dict[str, Any]:
    """
    Devuelve la ficha que ya está en memoria o la lee si aún no se cargó.
    Si el archivo falta o falla su lectura, devuelve un diccionario vacío: {}.
    """
    global _metadata_cache

    # Reutilizamos lo leído. Esto es independiente del modelo en memoria.
    # Incluso si guardamos {} por un error, hay que recargar para intentar leer de nuevo.
    if _metadata_cache is not None:
        return _metadata_cache

    path = _metadata_path()
    # Si falta la ficha, devolvemos {} para que se usen los valores de respaldo.
    if not path.exists():
        _metadata_cache = {}
        return _metadata_cache

    try:
        with open(path, encoding="utf-8") as f:
            _metadata_cache = json.load(f)
    except Exception:
        _metadata_cache = {}
    return _metadata_cache


def get_model_version() -> str:
    """
    Lee qué versión dice la ficha. Si no aparece, devuelve 1.0.0.
    """
    return str(load_metadata().get("model_version", DEFAULT_MODEL_VERSION))


def get_classification_thresholds() -> Dict[str, float]:
    """
    Lee los dos límites que separan bajo, moderado y alto.
    Si faltan, usa 0.30 y 0.60. Estos límites se aplican después del cálculo;
    no son algo que el modelo aprenda ni el límite elegido por F1.
    """
    # Buscamos los límites en la ficha; si no están como diccionario, usamos el respaldo.
    valores = load_metadata().get("umbrales_clasificacion_clinica")
    if not isinstance(valores, dict):
        return dict(DEFAULT_THRESHOLDS)
    return {
        "bajo_max": float(valores.get("bajo_max", DEFAULT_THRESHOLDS["bajo_max"])),
        "moderado_max": float(valores.get("moderado_max", DEFAULT_THRESHOLDS["moderado_max"])),
    }


def reload_metadata() -> Dict[str, Any]:
    """
    Olvida la ficha en memoria y la vuelve a leer desde el archivo.
    No vuelve a cargar el modelo .joblib; eso se hace con reload_model().
    """

    global _metadata_cache
    _metadata_cache = None
    return load_metadata()
