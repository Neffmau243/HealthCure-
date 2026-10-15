"""Regresión de release, políticas históricas, adaptación externa y persistencia."""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, text, inspect

from app.ml.metadata import load_metadata, validar_metadata
from app.ml.policy import seleccionar_bandas
from app.ml.predictor import predict, _classify
from app.ml.external_brfss import adaptar
from app.mappers.evaluacion_mapper import EvaluacionMapper
from app.services.evaluacion_triaje_service import generar_triaje_clinico
from app.tests.test_modelo_real import PERFIL_ALTO_RIESGO
from app.tests.test_evaluacion_mapper import _build_evaluacion_orm
from scripts.aplicar_migracion_004 import aplicar


def test_release_calibrada_y_snapshot_inmutable():
    result = predict(PERFIL_ALTO_RIESGO)
    assert result.modelo_version == "3.0.0"
    assert result.politica_modelo["reglas_version"] == "bandas-academicas-3.0.0"
    result.politica_modelo["umbrales"]["bajo_max"] = .99
    assert load_metadata()["politica_modelo"]["umbrales"]["bajo_max"] < .1


@pytest.mark.parametrize("change", ["cuts", "rules", "features", "hash"])
def test_metadata_incoherente_se_rechaza(change):
    meta = deepcopy(load_metadata())
    if change == "cuts": meta["umbrales_clasificacion_clinica"]["bajo_max"] = .9
    if change == "rules": meta["politica_modelo"]["reglas_version"] = "desconocida"
    if change == "features": meta["features"] = list(reversed(meta["features"]))
    if change == "hash": meta["artifact_sha256"] = ""
    with pytest.raises(ValueError): validar_metadata(meta)


def test_bordes_de_bandas_del_score_persistido():
    cuts = load_metadata()["politica_modelo"]["umbrales"]
    assert _classify(cuts["bajo_max"]-1e-6).value == "bajo"
    assert _classify(cuts["bajo_max"]).value == "moderado"
    assert _classify(cuts["moderado_max"]-1e-6).value == "moderado"
    assert _classify(cuts["moderado_max"]).value == "alto"


def test_hash_real_del_artefacto_se_verifica_antes_de_cargar(monkeypatch):
    import app.ml.model_loader as loader
    import app.ml.metadata as metadata
    from app.exceptions.ml_exceptions import ModelLoadError
    wrong = deepcopy(load_metadata())
    wrong["artifact_sha256"] = "0"*64
    monkeypatch.setattr(loader, "_model_instance", None)
    monkeypatch.setattr(metadata, "_metadata_cache", wrong)
    with pytest.raises(ModelLoadError, match="hash"):
        loader.load_model()


def test_criterio_de_banda_inferior_se_cumple_solo_en_validacion():
    meta = load_metadata()
    assert meta["metricas_validation_bandas"]["bajo_max"]["recall"] >= .90
    assert meta["politica_modelo"]["umbrales"] == {"bajo_max": .051065, "moderado_max": .210469}


def test_modelo_calibrado_no_puede_publicarse_como_version_legacy(monkeypatch):
    import app.ml.model_loader as loader
    import app.ml.metadata as metadata
    from app.exceptions.ml_exceptions import ModelLoadError
    legacy = json.loads((Path("app/resources/modelos/2.0.0")/"modelo_cardiaco_metadata.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(loader, "_model_instance", None)
    monkeypatch.setattr(metadata, "_metadata_cache", legacy)
    with pytest.raises(ModelLoadError, match="calibración"):
        loader.load_model()


def test_historico_sin_politica_no_recibe_reglas_v3():
    old = EvaluacionMapper.to_response(_build_evaluacion_orm(probabilidad=.1, clasificacion="bajo"))
    assert old.politica_modelo is None
    assert "BAJO RIESGO" in old.triaje_clinico.nivel_alerta
    # El fallback antiguo usa 0.30/0.60, no los cortes calibrados actuales.
    assert generar_triaje_clinico({}, .1, "?")["codigo_color"] == "verde"


def test_politica_guardada_se_usa_aunque_cambie_metadata_actual():
    policy = deepcopy(load_metadata()["politica_modelo"])
    response = EvaluacionMapper.to_response(_build_evaluacion_orm(
        modelo_version="3.0.0", probabilidad=.1, clasificacion="moderado", politica_modelo=policy))
    assert response.politica_modelo == policy
    assert "BANDA INTERMEDIA" in response.triaje_clinico.nivel_alerta


def test_migracion_004_repetible_no_cambia_valores():
    engine = create_engine("sqlite://")
    with engine.begin() as db:
        db.execute(text("CREATE TABLE evaluaciones (id INTEGER PRIMARY KEY, probabilidad NUMERIC)"))
        db.execute(text("INSERT INTO evaluaciones VALUES (1, .7)"))
    aplicar(engine); aplicar(engine)
    assert "politica_modelo" in {c["name"] for c in inspect(engine).get_columns("evaluaciones")}
    with engine.connect() as db:
        assert tuple(db.execute(text("SELECT probabilidad, politica_modelo FROM evaluaciones")).one()) == (.7, None)


def test_post_persiste_snapshot_y_pdf(env, usuarios_base):
    from app.tests.test_contrato_evaluacion import _post
    patient = usuarios_base["paciente_doctor"]
    doctor = usuarios_base["doctor"]
    r = _post(env, usuarios_base, patient)
    assert r.status_code == 201, r.text
    ev = r.json()
    assert ev["modelo_version"] == "3.0.0"
    assert ev["politica_modelo"] == load_metadata()["politica_modelo"]
    headers = env.auth_header(doctor.id, "usuario")
    stored = env.client.get(f"/api/v1/evaluaciones/{ev['id']}", headers=headers).json()
    assert stored["politica_modelo"] == ev["politica_modelo"]
    assert env.client.get(f"/api/v1/evaluaciones/{ev['id']}/fua", headers=headers).content.startswith(b"%PDF")


def test_adaptacion_2017_no_imputa_desconocidos_ni_confunde_diabetes():
    row = dict(GENHLTH=3, BPHIGH4=2, TOLDHI2=1, CVDSTRK3=2, DIABETE3=4,
               SEX=2, DIFFWALK=2, SMOKE100=2, EXERANY2=1, _MICHD=1, _AGEG5YR=8)
    raw = pd.DataFrame([row, {**row, "DIABETE3": 2}, {**row, "TOLDHI2": 7}])
    X, y, sex, flow = adaptar(raw)
    assert len(X) == 2 and flow["excluidas"] == 1
    assert X.diabetes.tolist() == [1, 0]  # Prediabetes positiva, solo embarazo negativo.
    assert X.presion_alta.tolist() == [0, 0]
    assert y.tolist() == [1, 1] and sex.tolist() == [0, 0]
