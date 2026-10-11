"""
test_modelo_real.py — TESTS DEL MODELO REAL Y SU FICHA TÉCNICA

A diferencia de test_evaluacion_mapper.py (que usa un PredictionResult fijo),
estos tests cargan el artefacto REAL (app/resources/modelo_cardiaco.joblib)
y su metadata, y verifican:

  1. Que el artefacto y su ficha técnica existan (versionado).
  2. Que la ficha técnica tenga los campos mínimos y métricas sanas.
  3. Que el modelo tenga las 9 features y esté entrenado con el dataset real.
  4. Que el pipeline REAL preprocess → predict() funcione end-to-end.
  5. Que las predicciones sean coherentes con el riesgo clínico.
  6. Que la versión que reporta la API coincida con la del artefacto.

Si el modelo no está entrenado, estos tests FALLAN con un mensaje claro
(no se saltan): el artefacto es parte del entregable y debe estar presente.
"""
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.ml.preprocessor import FEATURE_COLUMNS
from app.ml.metadata import (
    load_metadata, get_model_version, get_classification_thresholds,
)

# ── Perfil de riesgo BAJO: joven, sin factores, buena salud, activo ─────────
PERFIL_BAJO_RIESGO = {
    "edad": 30,
    "presion_alta": 0,
    "colesterol_alto": 0,
    "tabaquismo": 0,
    "actividad_fisica": 1,
    "antecedente_acv": 0,
    "diabetes": 0,
    "salud_general": 1,
    "dificultad_para_caminar": 0,
}

# ── Perfil de riesgo ALTO: mayor, con casi todos los factores ──────────────
PERFIL_ALTO_RIESGO = {
    "edad": 75,
    "presion_alta": 1,
    "colesterol_alto": 1,
    "tabaquismo": 1,
    "actividad_fisica": 0,
    "antecedente_acv": 1,
    "diabetes": 1,
    "salud_general": 5,
    "dificultad_para_caminar": 1,
}


def _model_path() -> Path:
    return Path(get_settings().MODEL_PATH)


@pytest.fixture(scope="module")
def metadata() -> dict:
    """Carga la ficha técnica; falla con mensaje claro si no existe."""
    path = _model_path().with_name(f"{_model_path().stem}_metadata.json")
    if not path.exists():
        pytest.fail(
            f"Falta la ficha técnica del modelo ({path}). "
            "Ejecuta: python entrenar_modelo.py"
        )
    meta = load_metadata()
    assert meta, "La ficha técnica existe pero está vacía o corrupta."
    return meta


@pytest.fixture(scope="module")
def modelo():
    """Carga el modelo real; falla con mensaje claro si no existe."""
    path = _model_path()
    if not path.exists():
        pytest.fail(
            f"Falta el modelo entrenado ({path}). "
            "Ejecuta: python entrenar_modelo.py"
        )
    from app.ml.model_loader import load_model
    return load_model()


# ══════════════════════════════════════════════════════════════════════════
# 1. Versionado del artefacto
# ══════════════════════════════════════════════════════════════════════════
def test_artefacto_y_ficha_tecnica_existen():
    assert _model_path().exists(), "El modelo .joblib no está entrenado"
    ficha = _model_path().with_name(f"{_model_path().stem}_metadata.json")
    assert ficha.exists(), "La ficha técnica (metadata) no existe"


def test_metadata_tiene_campos_minimos(metadata):
    obligatorios = {
        "model_version", "algoritmo", "entrenado_en", "dataset",
        "features", "target", "hiperparametros", "validacion_cruzada",
        "metricas_test_umbral_0.50", "umbrales_clasificacion_clinica", "librerias",
    }
    faltan = obligatorios - set(metadata)
    assert not faltan, f"Faltan campos en la ficha técnica: {faltan}"
    assert metadata["model_version"]
    assert metadata["algoritmo"] in {"RandomForest", "XGBoost"}


def test_metadata_declara_el_dataset_real(metadata):
    """Guardia anti-dataset-sintético: el artefacto debe ser del BRFSS real."""
    ds = metadata["dataset"]
    assert ds["n_rows"] > 200_000, "El modelo parece entrenado con datos sintéticos"
    assert ds["n_features"] == 9
    assert 0.05 < ds["positive_rate"] < 0.15  # ~9.4% en el BRFSS real


def test_metadata_metricas_son_sanas(metadata):
    m = metadata["metricas_test_umbral_0.50"]
    assert 0.70 <= m["roc_auc"] <= 1.0, "ROC AUC bajo: el modelo no aprendió"
    assert 0.0 <= m["f1"] <= 1.0
    assert len(m["matriz_confusion"]) == 2
    assert [len(fila) for fila in m["matriz_confusion"]] == [2, 2]


def test_metadata_features_coinciden_con_el_preprocessor(metadata):
    """El orden de features de la metadata debe ser el que usa la inferencia."""
    assert metadata["features"] == FEATURE_COLUMNS


def test_version_reportada_es_la_del_artefacto(metadata):
    assert get_model_version() == metadata["model_version"]


# ══════════════════════════════════════════════════════════════════════════
# 2. El modelo real
# ══════════════════════════════════════════════════════════════════════════
def test_modelo_esta_entrenado_con_9_features(modelo):
    assert int(modelo.n_features_in_) == len(FEATURE_COLUMNS)
    # Ambos estimadores del pipeline (sklearn API) fijan nombres al entrenar
    # con un DataFrame; si están, deben coincidir EXACTAMENTE con el orden.
    nombres = list(getattr(modelo, "feature_names_in_", []))
    if nombres:
        assert nombres == FEATURE_COLUMNS


def test_modelo_tiene_predict_proba(modelo):
    assert hasattr(modelo, "predict_proba")


# ══════════════════════════════════════════════════════════════════════════
# 3. Pipeline real end-to-end
# ══════════════════════════════════════════════════════════════════════════
def test_predict_end_to_end_funciona(metadata):
    from app.ml.predictor import predict
    resultado = predict(dict(PERFIL_ALTO_RIESGO))
    assert 0.0 <= resultado.probabilidad <= 1.0
    assert resultado.clasificacion.value in {"bajo", "moderado", "alto"}
    assert resultado.modelo_version == metadata["model_version"]


def test_prediccion_es_determinista():
    from app.ml.predictor import predict
    a = predict(dict(PERFIL_ALTO_RIESGO))
    b = predict(dict(PERFIL_ALTO_RIESGO))
    assert a.probabilidad == b.probabilidad


def test_prediccion_coherente_con_el_riesgo_clinico():
    from app.ml.predictor import predict
    bajo = predict(dict(PERFIL_BAJO_RIESGO)).probabilidad
    alto = predict(dict(PERFIL_ALTO_RIESGO)).probabilidad
    assert alto > bajo, "El perfil de alto riesgo debería tener mayor probabilidad"
    assert alto > 0.5, "Un perfil con casi todos los factores debería superar 0.5"
    assert bajo < 0.3, "Un perfil joven y sano debería quedar por debajo de 0.3"


# ══════════════════════════════════════════════════════════════════════════
# 4. Coherencia de umbrales entre entrenamiento e inferencia
# ══════════════════════════════════════════════════════════════════════════
def test_umbrales_de_clasificacion_son_coherentes():
    t = get_classification_thresholds()
    assert 0.0 < t["bajo_max"] < t["moderado_max"] < 1.0


def test_classify_respeta_los_umbrales():
    from app.ml.predictor import _classify
    from app.schemas.evaluacion import ClasificacionEnum
    t = get_classification_thresholds()
    assert _classify(0.0) == ClasificacionEnum.bajo
    assert _classify(t["bajo_max"] - 0.001) == ClasificacionEnum.bajo
    assert _classify(t["bajo_max"]) == ClasificacionEnum.moderado
    assert _classify(t["moderado_max"]) == ClasificacionEnum.alto
    assert _classify(1.0) == ClasificacionEnum.alto


# ══════════════════════════════════════════════════════════════════════
# 5. E2E POR HTTP — pipeline completo a través de POST /evaluaciones/
#    (TestClient → router → service → mapper → modelo real → repositorio)
# ══════════════════════════════════════════════════════════════════════
PERFIL_MODERADO = {
    "edad": 55,
    "presion_alta": True,
    "colesterol_alto": True,
    "tabaquismo": False,
    "actividad_fisica": True,
    "antecedente_acv": False,
    "diabetes": True,
    "salud_general": 3,
    "dificultad_para_caminar": False,
}


def _payload(paciente_id: int, **overrides) -> dict:
    return {"paciente_id": paciente_id, **PERFIL_MODERADO, **overrides}


def test_e2e_post_evaluacion_predice_y_persiste(env, usuarios_base):
    """POST /api/v1/evaluaciones/ end-to-end con el modelo REAL."""
    doctor = usuarios_base["doctor"]
    paciente = usuarios_base["paciente_doctor"]
    headers = env.auth_header(doctor.id, "usuario")

    resp = env.client.post(
        "/api/v1/evaluaciones/",
        json=_payload(paciente.id),
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    # Predicción del modelo real
    assert 0.0 <= body["probabilidad"] <= 1.0
    assert body["modelo_version"] == get_model_version()

    # Coherencia clasificación ↔ probabilidad según los umbrales de la ficha
    t = get_classification_thresholds()
    esperado = (
        "bajo" if body["probabilidad"] < t["bajo_max"]
        else "moderado" if body["probabilidad"] < t["moderado_max"]
        else "alto"
    )
    assert body["clasificacion"] == esperado

    # Triaje clínico generado en el mapper
    assert body["triaje_clinico"]["codigo_color"] in {"verde", "amarillo", "rojo"}
    assert body["triaje_clinico"]["recomendaciones_medicas"]

    # Persistencia real (GET por id y por paciente devuelven lo mismo)
    evaluacion_id = body["id"]
    r_detalle = env.client.get(f"/api/v1/evaluaciones/{evaluacion_id}", headers=headers)
    assert r_detalle.status_code == 200
    assert r_detalle.json()["probabilidad"] == body["probabilidad"]

    r_historial = env.client.get(
        f"/api/v1/evaluaciones/by-paciente/{paciente.id}", headers=headers
    )
    assert r_historial.status_code == 200
    assert any(e["id"] == evaluacion_id for e in r_historial.json())


def test_e2e_orden_de_riesgo_por_http(env, usuarios_base):
    """El perfil de alto riesgo debe superar al de bajo riesgo vía HTTP."""
    doctor = usuarios_base["doctor"]
    paciente = usuarios_base["paciente_doctor"]
    headers = env.auth_header(doctor.id, "usuario")

    bajo = env.client.post(
        "/api/v1/evaluaciones/",
        json=_payload(paciente.id, **PERFIL_BAJO_RIESGO),
        headers=headers,
    )
    alto = env.client.post(
        "/api/v1/evaluaciones/",
        json=_payload(paciente.id, **PERFIL_ALTO_RIESGO),
        headers=headers,
    )
    assert bajo.status_code == 201, bajo.text
    assert alto.status_code == 201, alto.text
    assert alto.json()["probabilidad"] > bajo.json()["probabilidad"]
    assert bajo.json()["clasificacion"] == "bajo"
    assert alto.json()["clasificacion"] == "alto"


def test_e2e_evaluacion_sin_token_devuelve_401(env, usuarios_base):
    paciente = usuarios_base["paciente_doctor"]
    resp = env.client.post(
        "/api/v1/evaluaciones/",
        json=_payload(paciente.id),
    )
    assert resp.status_code == 401


def test_e2e_evaluacion_paciente_inexistente_devuelve_400(env, usuarios_base):
    doctor = usuarios_base["doctor"]
    headers = env.auth_header(doctor.id, "usuario")
    resp = env.client.post(
        "/api/v1/evaluaciones/",
        json=_payload(99999),
        headers=headers,
    )
    assert resp.status_code == 400
