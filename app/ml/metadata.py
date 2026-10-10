"""
metadata.py — LEE LA FICHA TÉCNICA DEL MODELO (VERSIONADO DEL ARTEFACTO)

El entrenamiento (`entrenar_modelo.py`) guarda DOS archivos juntos:

  app/resources/modelo_cardiaco.joblib            → el modelo serializado
  app/resources/modelo_cardiaco_metadata.json     → su ficha técnica

La ficha técnica permite que la API conozca, sin hardcodear nada:
  - la VERSIÓN real del modelo (no un string escrito a mano en el código),
  - los UMBRALES de clasificación clínica con los que fue entrenado,
  - el algoritmo, hiperparámetros, dataset y métricas.

Patrón Singleton igual que `model_loader`: el JSON se lee UNA vez y se
cachea en memoria (es un archivo pequeño y no cambia en caliente).

DISEÑO DEFENSIVO: si la ficha no existe o está corrupta, se devuelven
valores por defecto y la API sigue funcionando (nunca rompe una predicción
por falta de metadata).
"""
import json
from pathlib import Path
from typing import Any, Dict

from app.core.config import get_settings

# Valores por defecto = comportamiento histórico (versión 1.x del modelo).
DEFAULT_MODEL_VERSION = "1.0.0"
DEFAULT_THRESHOLDS = {"bajo_max": 0.30, "moderado_max": 0.60}

_metadata_cache: Dict[str, Any] | None = None


def _metadata_path() -> Path:
    """
    Ruta del JSON derivada de MODEL_PATH:
      app/resources/modelo_cardiaco.joblib
        → app/resources/modelo_cardiaco_metadata.json
    """
    model_path = Path(get_settings().MODEL_PATH)
    return model_path.with_name(f"{model_path.stem}_metadata.json")


def load_metadata() -> Dict[str, Any]:
    """
    Retorna la ficha técnica del modelo (cacheada). Si no existe o está
    corrupta, retorna un dict vacío (y la API usa los valores por defecto).
    """
    global _metadata_cache
    if _metadata_cache is not None:
        return _metadata_cache

    path = _metadata_path()
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
    """Versión real del artefacto; cae a '1.0.0' si no hay ficha técnica."""
    return str(load_metadata().get("model_version", DEFAULT_MODEL_VERSION))


def get_classification_thresholds() -> Dict[str, float]:
    """
    Umbrales clínicos (bajo/moderado/alto) con los que se entrenó el modelo.
    Si la ficha no los trae, se usan los del MVP (0.30 / 0.60).
    """
    valores = load_metadata().get("umbrales_clasificacion_clinica")
    if not isinstance(valores, dict):
        return dict(DEFAULT_THRESHOLDS)
    return {
        "bajo_max": float(valores.get("bajo_max", DEFAULT_THRESHOLDS["bajo_max"])),
        "moderado_max": float(valores.get("moderado_max", DEFAULT_THRESHOLDS["moderado_max"])),
    }


def reload_metadata() -> Dict[str, Any]:
    """Fuerza la relectura de la ficha técnica (útil tras reentrenar)."""
    global _metadata_cache
    _metadata_cache = None
    return load_metadata()
