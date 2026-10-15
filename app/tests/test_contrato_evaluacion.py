"""Regresiones del contrato académico, persistencia y compatibilidad histórica."""
from datetime import date, datetime, timezone, timedelta

import pytest
from sqlalchemy import create_engine, text, inspect

from app.models.evaluacion import Evaluacion
from app.schemas.evaluacion import EvaluacionCreate
from app.tests.test_evaluacion_mapper import DATOS_VALIDOS, _build_evaluacion_orm
from app.mappers.evaluacion_mapper import EvaluacionMapper
from app.services.evaluacion_triaje_service import generar_triaje_clinico
from scripts.aplicar_migracion_003 import aplicar


@pytest.mark.parametrize("campo", [k for k in DATOS_VALIDOS if k != "paciente_id"])
def test_cada_predictor_es_obligatorio(campo):
    with pytest.raises(ValueError):
        EvaluacionCreate(**{k: v for k, v in DATOS_VALIDOS.items() if k != campo})


@pytest.mark.parametrize("edad", [1, 17, 121])
def test_edad_fuera_de_poblacion_se_rechaza(edad):
    with pytest.raises(ValueError):
        EvaluacionCreate(**{**DATOS_VALIDOS, "edad": edad})


@pytest.mark.parametrize("datos", [
    {"diabetes": False, "estado_diabetes": "prediabetes"},
    {"diabetes": True, "estado_diabetes": "ninguna"},
    {"presion_sistolica": 140},
    {"presion_sistolica": 80, "presion_diastolica": 120},
])
def test_datos_originales_incoherentes_se_rechazan(datos):
    with pytest.raises(ValueError):
        EvaluacionCreate(**{**DATOS_VALIDOS, **datos})


def _post(env, usuarios, paciente, **extras):
    hoy = datetime.now(timezone(timedelta(hours=-5))).date()
    edad = hoy.year - paciente.fecha_nacimiento.year - ((hoy.month, hoy.day) < (paciente.fecha_nacimiento.month, paciente.fecha_nacimiento.day))
    return env.client.post("/api/v1/evaluaciones/",
        headers=env.auth_header(usuarios["doctor"].id, "usuario"),
        json={**DATOS_VALIDOS, "paciente_id": paciente.id, "edad": edad, **extras})


def test_menor_no_puede_evaluarse_fingiendo_edad_adulta(env, usuarios_base):
    anio = datetime.now(timezone(timedelta(hours=-5))).year
    menor = env.create_paciente("44444444", fecha_nacimiento=date(anio - 17, 1, 1))
    r = _post(env, usuarios_base, menor, edad=25)
    assert r.status_code == 400
    assert "adultos" in r.json()["detail"]
    with env.new_session() as db:
        assert db.query(Evaluacion).count() == 0


def test_edad_discrepante_se_rechaza_sin_guardar(env, usuarios_base):
    paciente = usuarios_base["paciente_doctor"]
    r = _post(env, usuarios_base, paciente, edad=99)
    assert r.status_code == 400
    assert "no coincide" in r.json()["detail"]
    with env.new_session() as db:
        assert db.query(Evaluacion).count() == 0


def test_prediabetes_y_presion_se_conservan_en_historial_y_pdf(env, usuarios_base):
    paciente = usuarios_base["paciente_doctor"]
    r = _post(env, usuarios_base, paciente, estado_diabetes="prediabetes",
              presion_alta=False, presion_sistolica=160, presion_diastolica=95)
    assert r.status_code == 201, r.text
    ev = r.json()
    assert ev["diabetes"] is True
    assert ev["estado_diabetes"] == "prediabetes"
    assert ev["presion_alta"] is False
    assert ev["presion_sistolica"] == 160
    assert "Prediabetes declarada" in ev["triaje_clinico"]["factores_riesgo_detectados"]
    auth = env.auth_header(usuarios_base["doctor"].id, "usuario")
    historial = env.client.get(f"/api/v1/evaluaciones/by-paciente/{paciente.id}", headers=auth).json()
    assert historial[0]["estado_diabetes"] == "prediabetes"
    assert historial[0]["presion_diastolica"] == 95
    with env.new_session() as db:
        guardada = db.get(Evaluacion, ev["id"])
        assert guardada.estado_diabetes == "prediabetes"
        assert guardada.presion_sistolica == 160
    pdf = env.client.get(f"/api/v1/evaluaciones/{ev['id']}/fua", headers=auth)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF-")


def test_cliente_booleano_sigue_funcionando_sin_inventar_subtipo(env, usuarios_base):
    r = _post(env, usuarios_base, usuarios_base["paciente_doctor"])
    assert r.status_code == 201, r.text
    assert r.json()["estado_diabetes"] is None
    assert "Prediabetes o diabetes (sin detalle registrado)" in r.json()["triaje_clinico"]["factores_riesgo_detectados"]


def test_historial_persistido_no_se_reescribe():
    original = _build_evaluacion_orm(nivel_alerta="Texto histórico", codigo_color="rojo",
        accion_sugerida="Acción histórica", factores_riesgo_detectados=["Diabetes Mellitus"],
        factores_protectores=[], recomendaciones_medicas=["Texto original"])
    respuesta = EvaluacionMapper.to_response(original)
    assert respuesta.estado_diabetes is None
    assert respuesta.triaje_clinico.accion_sugerida == "Acción histórica"
    assert respuesta.triaje_clinico.factores_riesgo_detectados == ["Diabetes Mellitus"]


def test_reglas_no_inventan_tabaco_activo_ni_indican_tratamiento():
    triaje = generar_triaje_clinico({"tabaquismo": True, "diabetes": True, "estado_diabetes": "prediabetes"}, .9, "alto")
    texto = " ".join(triaje["factores_riesgo_detectados"] + triaje["recomendaciones_medicas"])
    assert "Prediabetes declarada" in texto
    assert "Tabaco Activo" not in texto
    assert "ECG" not in texto
    assert "Regla académica sin validación clínica" in texto


def test_migracion_es_repetible_y_conserva_el_historial():
    engine = create_engine("sqlite://")
    with engine.begin() as db:
        db.execute(text("CREATE TABLE evaluaciones (id INTEGER PRIMARY KEY, probabilidad NUMERIC, diabetes BOOLEAN)"))
        db.execute(text("INSERT INTO evaluaciones VALUES (1, 0.7, 1)"))
    aplicar(engine)
    aplicar(engine)
    assert {"estado_diabetes", "presion_sistolica", "presion_diastolica"} <= {c["name"] for c in inspect(engine).get_columns("evaluaciones")}
    with engine.connect() as db:
        assert tuple(db.execute(text("SELECT probabilidad, diabetes, estado_diabetes, presion_sistolica FROM evaluaciones")).one()) == (.7, 1, None, None)
    engine.dispose()
