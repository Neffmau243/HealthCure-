"""Registro, cambios de categoría por visita y FUA sin alterar el historial ni el ML."""
from datetime import date, timedelta
from io import BytesIO
from unittest.mock import patch

import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine, inspect, text

from app.mappers.evaluacion_mapper import EvaluacionMapper
from app.schemas.evaluacion import EvaluacionCreate
from app.tests.test_contexto_atencion import _login, _paciente, _atender
from scripts.migrar_categoria_paciente import migrar


def test_general_gestante_puerpera_conserva_cada_fua(env):
    h = _login(env)
    paciente = _paciente(env, h, edad=20)
    probable = (date.today() + timedelta(days=150)).isoformat()
    parto = (date.today() - timedelta(days=7)).isoformat()
    etapas = [
        ("ninguna", None),
        ("gestante", {"fecha_probable_parto": probable, "edad_gestacional_semanas": 20,
                       "numero_control_prenatal": 3, "altura_uterina_cm": 21}),
        ("puerpera", {"fecha_parto": parto, "numero_control_puerperal": 2}),
    ]
    guardadas = []
    for categoria, datos in etapas:
        r = _atender(env, h, paciente, condicion_materna=categoria, datos_maternos=datos)
        assert r.status_code == 201, r.text
        visita = r.json()
        guardadas.append(visita)
        actual = env.client.get(f"/api/v1/pacientes/{paciente['id']}", headers=h).json()
        assert actual["grupo_etario"] == "adulto"
        assert actual["contexto_atencion"]["condicion_materna"] == categoria
        assert visita["evaluacion_id"] is None
        assert visita["grupo_etario"] == "adulto"
        for anterior in guardadas:
            respuesta = env.client.get(f"/api/v1/atenciones/{anterior['id']}", headers=h)
            assert respuesta.json() == anterior
        pdf = env.client.get(f"/api/v1/atenciones/{visita['id']}/fua", headers=h)
        assert pdf.status_code == 200
        contenido = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages[1:])
        assert "Adulto/a" in contenido
        if datos:
            assert visita["observaciones_clinicas"]["datos_maternos"] == {**{k: None for k in [
                "fecha_probable_parto", "edad_gestacional_semanas", "numero_control_prenatal",
                "altura_uterina_cm", "fecha_parto", "numero_control_puerperal"]}, **datos}
            fecha = datos.get("fecha_probable_parto") or datos.get("fecha_parto")
            assert "/".join(fecha.split("-")[::-1]) in contenido
    # El FUA de la visita gestante sigue mostrando la gestación tras pasar a puérpera.
    anterior = env.client.get(f"/api/v1/atenciones/{guardadas[1]['id']}/fua", headers=h)
    anexo = "\n".join(p.extract_text() for p in PdfReader(BytesIO(anterior.content)).pages[1:])
    assert "/".join(probable.split("-")[::-1]) in anexo
    assert "Fecha de parto" not in anexo


def test_registro_administrativo_guarda_categoria_y_permite_cambiarla(env):
    h = _login(env)
    cuerpo = {"documento_identidad": "CAT-10001", "apellido_paterno": "Prueba", "nombres": "Gestante",
              "fecha_nacimiento": "2006-01-01", "sexo": "F",
              "contexto_atencion": {"condicion_materna": "gestante", "datos_maternos": {"numero_control_prenatal": 2}}}
    r = env.client.post("/api/v1/pacientes/", headers=h, json=cuerpo)
    assert r.status_code == 201, r.text
    paciente = r.json()
    assert paciente["contexto_atencion"]["condicion_materna"] == "gestante"
    r = env.client.put(f"/api/v1/pacientes/{paciente['id']}", headers=h, json={
        "contexto_atencion": {"condicion_materna": "ninguna"}})
    assert r.status_code == 200, r.text
    assert r.json()["contexto_atencion"] == {"condicion_materna": "ninguna", "datos_maternos": None}


def test_personal_actualiza_solo_categoria_sin_ml_ni_editar_identidad(env):
    h = _login(env)
    paciente = _paciente(env, h)
    otro = env.create_usuario("Otro profesional", "otro@example.com", "password", "usuario")
    headers = {"Authorization": f"Bearer {env.token(otro.id, otro.rol)}"}
    url = f"/api/v1/pacientes/{paciente['id']}/contexto-atencion"
    contexto = {"condicion_materna": "gestante", "datos_maternos": {"numero_control_prenatal": 2}}
    assert env.client.put(url, json=contexto).status_code == 401
    with patch("app.ml.predictor.predict") as modelo:
        r = env.client.put(url, headers=headers, json=contexto)
        assert r.status_code == 200, r.text
        modelo.assert_not_called()
    assert r.json()["contexto_atencion"]["condicion_materna"] == "gestante"
    assert r.json()["documento_identidad"] == paciente["documento_identidad"]
    assert env.client.put(url, headers=headers, json={**contexto, "nombres": "Cambio no permitido"}).status_code == 422
    assert env.client.put(f"/api/v1/pacientes/{paciente['id']}", headers=headers, json={"nombres": "Cambio no permitido"}).status_code == 403
    assert env.client.get(f"/api/v1/evaluaciones/by-paciente/{paciente['id']}", headers=h).json() == []
    assert env.client.put("/api/v1/pacientes/999999/contexto-atencion", headers=headers, json=contexto).status_code == 404


@pytest.mark.parametrize("categoria,datos", [
    ("ninguna", {"fecha_parto": "2020-01-01"}),
    ("gestante", {"fecha_parto": "2020-01-01"}),
    ("puerpera", {"numero_control_prenatal": 2}),
    ("puerpera", {"fecha_parto": (date.today() + timedelta(days=1)).isoformat()}),
    ("gestante", {"numero_control_prenatal": -1}),
    ("gestante", {"campo_desconocido": 1}),
])
def test_datos_invalidos_no_crean_visita_ni_cambian_categoria(env, categoria, datos):
    h = _login(env)
    paciente = _paciente(env, h)
    r = _atender(env, h, paciente, condicion_materna=categoria, datos_maternos=datos)
    assert r.status_code in (400, 422), r.text
    assert env.client.get(f"/api/v1/atenciones/by-paciente/{paciente['id']}", headers=h).json() == []
    assert env.client.get(f"/api/v1/pacientes/{paciente['id']}", headers=h).json()["contexto_atencion"]["condicion_materna"] == "ninguna"


def test_triaje_guarda_contexto_sin_incluir_datos_maternos_en_el_vector_ml(env):
    h = _login(env)
    paciente = _paciente(env, h, edad=20)
    cuerpo = {"paciente_id": paciente["id"], "edad": 20, "observaciones_clinicas": {
        "condicion_materna": "gestante", "datos_maternos": {"numero_control_prenatal": 2}}}
    normal = EvaluacionMapper.request_to_model_input(EvaluacionCreate(paciente_id=paciente["id"], edad=20))
    assert EvaluacionMapper.request_to_model_input(EvaluacionCreate(**cuerpo)) == normal
    r = env.client.post("/api/v1/evaluaciones/", headers=h, json=cuerpo)
    assert r.status_code == 201, r.text
    evaluacion = r.json()
    actual = env.client.get(f"/api/v1/pacientes/{paciente['id']}", headers=h).json()
    assert actual["contexto_atencion"]["condicion_materna"] == "gestante"
    # Reutilizar signos verificados no obliga a copiar la categoría anterior.
    r = _atender(env, h, paciente, condicion_materna="puerpera", datos_maternos={"fecha_parto": date.today().isoformat()},
                 evaluacion_id=evaluacion["id"], usar_observaciones_evaluacion=True)
    assert r.status_code == 201, r.text
    datos = r.json()["observaciones_clinicas"]["datos_maternos"]
    assert datos["fecha_parto"] == date.today().isoformat()
    assert datos["numero_control_prenatal"] is None
    anterior = env.client.get(f"/api/v1/evaluaciones/{evaluacion['id']}", headers=h).json()
    assert anterior["observaciones_clinicas"]["condicion_materna"] == "gestante"


def test_migracion_categoria_es_idempotente_y_conserva_registros():
    motor = create_engine("sqlite://")
    with motor.begin() as conexion:
        conexion.execute(text("CREATE TABLE pacientes (id INTEGER PRIMARY KEY)"))
        conexion.execute(text("INSERT INTO pacientes (id) VALUES (1)"))
    migrar(motor)
    migrar(motor)
    with motor.connect() as conexion:
        assert "contexto_atencion" in {c["name"] for c in inspect(conexion).get_columns("pacientes")}
        assert conexion.execute(text("SELECT id, contexto_atencion FROM pacientes")).one() == (1, None)
    motor.dispose()
