"""Carga y valida metadata del bundle activo; falla si faltan datos o son incoherentes.

Las releases 3.x exigen hash y política compatible. Las dos cachés deben recargarse
juntas; reload_model también recarga metadata. No aplicar cortes legacy a v3.
"""
import json
import math
from copy import deepcopy
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
    with open(path, encoding="utf-8") as file:
        meta = json.load(file)
    validar_metadata(meta)
    _metadata_cache = meta
    return _metadata_cache


def validar_metadata(meta):
    from app.ml.preprocessor import FEATURE_COLUMNS
    if not isinstance(meta, dict) or not meta.get("model_version"):
        raise ValueError("Metadata sin versión válida")
    if meta.get("features") != FEATURE_COLUMNS:
        raise ValueError("Features del modelo y aplicación no coinciden")
    cuts = meta.get("umbrales_clasificacion_clinica", {})
    low, high = cuts.get("bajo_max"), cuts.get("moderado_max")
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (low, high)):
        raise ValueError("Umbrales ausentes o no finitos")
    if not 0 < low < high < 1:
        raise ValueError("Umbrales desordenados")
    if meta["model_version"].startswith("3."):
        policy = meta.get("politica_modelo", {})
        if (policy.get("reglas_version") != "bandas-academicas-3.0.0"
                or policy.get("umbrales") != cuts or policy.get("decimales_score") != 6
                or policy.get("semantica_score") != "calibracion_sigmoid_interna"
                or len(meta.get("artifact_sha256", "")) != 64):
            raise ValueError("Política, calibración o hash incompatibles con la release")


def get_model_policy():
    return deepcopy(load_metadata().get("politica_modelo"))


def get_model_version() -> str:
    """Versión real del artefacto; cae a '1.0.0' si no hay ficha técnica."""
    return str(load_metadata().get("model_version", DEFAULT_MODEL_VERSION))


def get_classification_thresholds() -> Dict[str, float]:
    """
    Cortes experimentales de la metadata validada del bundle activo.
    load_metadata rechaza una ficha ausente, incompleta o incompatible.
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
