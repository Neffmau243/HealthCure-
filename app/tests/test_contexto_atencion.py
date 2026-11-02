"""Recorrido HTTP real: login, paciente, atención, historial y FUA por visita."""
from datetime import date
from io import BytesIO
from unittest.mock import patch

import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine, inspect, text

from app.core.clinica import calcular_edad, grupo_por_edad
from app.models.atencion import Atencion
from scripts.migrar_contexto_atencion import migrar


@pytest.mark.parametrize("edad,grupo", [(0, "nino"), (11, "nino"), (17, "nino"), (18, "adulto"), (59, "adulto"), (60, "adulto_mayor"), (95, "adulto_mayor")])
def test_grupos_y_limites(edad, grupo):
    assert grupo_por_edad(edad).value == grupo


def test_edad_antes_y_despues_del_cumpleanos():
    assert calcular_edad(date(1966, 10, 25), date(2026, 10, 24)) == 59
    assert calcular_edad(date(1966, 10, 25), date(2026, 10, 25)) == 60
    assert calcular_edad(date(2024, 2, 29), date(2025, 2, 28)) == 0
    assert calcular_edad(date(2024, 2, 29), date(2025, 3, 1)) == 1
    with pytest.raises(ValueError):
        calcular_edad(date(2030, 1, 1), date(2026, 1, 1))


def _login(env):
    user = env.create_usuario("Profesional E2E", "e2e@example.com", "e2e-password", "usuario")
    response = env.client.post("/api/v1/auth/login", json={"email": user.email, "password": "e2e-password"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _paciente(env, headers, edad=30, sexo="F", documento="E2E-10001"):
    hoy = date.today()
    nacimiento = date(hoy.year - edad, 1, 1)
    response = env.client.post("/api/v1/pacientes/", headers=headers, json={
        "documento_identidad": documento, "apellido_paterno": "Prueba",
        "nombres": "Paciente E2E", "fecha_nacimiento": nacimiento.isoformat(), "sexo": sexo,
    })
    assert response.status_code == 201, response.text
    return response.json()


def _atender(env, headers, paciente, **cambios):
    return env.client.post("/api/v1/atenciones/", headers=headers, json={
        "paciente_id": paciente["id"], "tipo_atencion": "ambulatoria", "condicion_materna": "ninguna",
        "diagnostico": "Diagnóstico de prueba E2E", "tratamiento": "Tratamiento de prueba E2E",
        "indicaciones": "Control de prueba E2E", **cambios,
    })


def _pdf(env, headers, atencion_id):
    r = env.client.get(f"/api/v1/atenciones/{atencion_id}/fua", headers=headers)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert f"fua_atencion_{atencion_id}.pdf" in r.headers["content-disposition"]
    reader = PdfReader(BytesIO(r.content))
    return "\n".join(page.extract_text() for page in reader.pages)


@pytest.mark.parametrize("edad,grupo,tipo,condicion,etiqueta", [
    (7, "nino", "emergencia", "ninguna", "Niño/a"),
    (17, "nino", "ambulatoria", "ninguna", "Niño/a"),
    (30, "adulto", "emergencia", "gestante", "Adulto/a"),
    (30, "adulto", "ambulatoria", "puerpera", "Adulto/a"),
    (70, "adulto_mayor", "ambulatoria", "ninguna", "Adulto/a mayor"),
])
def test_e2e_contexto_de_visita_hasta_el_fua(env, edad, grupo, tipo, condicion, etiqueta):
    headers = _login(env)
    paciente = _paciente(env, headers, edad)
    assert paciente["grupo_etario"] == grupo
    r = _atender(env, headers, paciente, tipo_atencion=tipo, condicion_materna=condicion)
    assert r.status_code == 201, r.text
    atencion = r.json()
    assert atencion["tipo_atencion"] == tipo
    assert atencion["condicion_materna"] == condicion
    assert atencion["grupo_etario"] == grupo
    assert atencion["edad_al_atender"] == edad
    assert atencion["evaluacion_id"] is None
    for url in [f"/api/v1/atenciones/{atencion['id']}", f"/api/v1/atenciones/by-paciente/{paciente['id']}", "/api/v1/atenciones/"]:
        respuesta = env.client.get(url, headers=headers)
        assert respuesta.status_code == 200
        body = respuesta.json()
        registro = body[0] if isinstance(body, list) else body
        assert registro == atencion
    with env.new_session() as db:
        guardada = db.get(Atencion, atencion["id"])
        assert (guardada.tipo_atencion, guardada.grupo_etario, guardada.condicion_materna) == (tipo, grupo, condicion)
    contenido = _pdf(env, headers, atencion["id"])
    assert etiqueta in contenido
    assert tipo.capitalize() in contenido
    assert {"ninguna": "Ninguna", "gestante": "Gestante", "puerpera": "Puérpera"}[condicion] in contenido
    assert "Diagnóstico de prueba E2E" in contenido
    assert "Tratamiento de prueba E2E" in contenido
    assert "Sin evaluación ML asociada" in contenido


def test_e2e_visitas_preservan_su_contexto_y_edad(env):
    h = _login(env)
    p = _paciente(env, h, 30)
    primera = _atender(env, h, p, tipo_atencion="emergencia", condicion_materna="gestante").json()
    segunda = _atender(env, h, p, condicion_materna="puerpera").json()
    # Corregir el registro administrativo no reescribe instantáneas de atenciones.
    r = env.client.put(f"/api/v1/pacientes/{p['id']}", headers=h, json={"fecha_nacimiento": "1950-01-01"})
    assert r.status_code == 200
    assert r.json()["grupo_etario"] == "adulto_mayor"
    for visita, condicion in [(primera, "gestante"), (segunda, "puerpera")]:
        datos = env.client.get(f"/api/v1/atenciones/{visita['id']}", headers=h).json()
        assert datos["grupo_etario"] == "adulto"
        assert datos["edad_al_atender"] == 30
        assert datos["condicion_materna"] == condicion
    assert "Gestante" in _pdf(env, h, primera["id"])
    assert "Puérpera" in _pdf(env, h, segunda["id"])


def test_e2e_adulto_mantiene_prediccion_y_fua_incluye_contexto(env):
    h = _login(env)
    p = _paciente(env, h, 55)
    payload = {"paciente_id": p["id"], "edad": 55, "presion_alta": True,
               "colesterol_alto": True, "diabetes": True, "actividad_fisica": True}
    ev = env.client.post("/api/v1/evaluaciones/", headers=h, json=payload)
    assert ev.status_code == 201, ev.text
    assert ev.json()["probabilidad"] == pytest.approx(0.513150, abs=1e-6)
    r = _atender(env, h, p, evaluacion_id=ev.json()["id"], tipo_atencion="emergencia", condicion_materna="gestante")
    assert r.status_code == 201, r.text
    contenido = _pdf(env, h, r.json()["id"])
    assert "Emergencia" in contenido and "Gestante" in contenido
    assert "Índice de riesgo" in contenido and "51.31" in contenido
    assert "Evaluación cardiovascular asociada" in contenido
    # El reporte previo por evaluación sigue disponible.
    assert env.client.get(f"/api/v1/evaluaciones/{ev.json()['id']}/fua", headers=h).status_code == 200


def test_menor_no_ejecuta_ml_aunque_envie_edad_adulta(env):
    h = _login(env)
    p = _paciente(env, h, 10)
    with patch("app.ml.predictor.predict") as predict:
        for edad in [10, 50]:
            r = env.client.post("/api/v1/evaluaciones/", headers=h, json={"paciente_id": p["id"], "edad": edad})
            assert r.status_code == 400
        predict.assert_not_called()


def test_validaciones_contexto_y_acceso_pdf(env):
    h = _login(env)
    p = _paciente(env, h, sexo="M")
    assert _atender(env, h, p, condicion_materna="gestante").status_code == 400
    assert _atender(env, h, p, condicion_materna="puerpera").status_code == 400
    assert _atender(env, h, p, tipo_atencion="inventada").status_code == 422
    assert _atender(env, h, p, condicion_materna="inventada").status_code == 422
    assert env.client.get("/api/v1/atenciones/999999/fua", headers=h).status_code == 404
    assert env.client.get("/api/v1/atenciones/1/fua").status_code == 401


def test_atencion_antigua_no_inventa_contexto(env):
    h = _login(env)
    p = _paciente(env, h)
    with env.new_session() as db:
        user_id = env.client.get("/api/v1/auth/me", headers=h).json()["id"]
        antigua = Atencion(paciente_id=p["id"], usuario_id=user_id, diagnostico="Registro antiguo", tratamiento="Tratamiento antiguo")
        db.add(antigua)
        db.commit()
        atencion_id = antigua.id
    body = env.client.get(f"/api/v1/atenciones/{atencion_id}", headers=h).json()
    assert all(body[k] is None for k in ["tipo_atencion", "grupo_etario", "condicion_materna", "edad_al_atender"])
    assert "No registrado" in _pdf(env, h, atencion_id)


def test_fua_pagina_textos_largos_sin_perder_datos(env):
    h = _login(env)
    p = _paciente(env, h)
    r = _atender(env, h, p, diagnostico=("Diagnóstico largo " * 100) + "FIN-DX", tratamiento=("Tratamiento largo " * 100) + "FIN-TX", indicaciones=("Control largo " * 100) + "FIN-IND")
    assert r.status_code == 201
    contenido = _pdf(env, h, r.json()["id"])
    for marcador in ["FIN-DX", "FIN-TX", "FIN-IND", "Firmas y conformidad"]:
        assert marcador in contenido


def test_migracion_aditiva_idempotente_conserva_historial():
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as db:
            db.execute(text("CREATE TABLE atenciones (id INTEGER PRIMARY KEY, diagnostico TEXT)"))
            db.execute(text("INSERT INTO atenciones VALUES (1, 'Registro previo')"))
        migrar(engine)
        migrar(engine)
        assert len(inspect(engine).get_columns("atenciones")) == 6
        with engine.connect() as db:
            row = db.execute(text("SELECT diagnostico, tipo_atencion, grupo_etario, condicion_materna, edad_al_atender FROM atenciones")).one()
            assert tuple(row) == ("Registro previo", None, None, None, None)
    finally:
        engine.dispose()
