"""
test_atenciones.py — Tests de los endpoints de atenciones del consultorio.

Cubren:
  - Crear atención (201) y consultarla.
  - Listado paginado.
  - Historial por paciente.
  - Validaciones: paciente inexistente (400), evaluación inexistente (400),
    evaluación de otro paciente (400).
  - 404 al pedir una atención que no existe.
  - 401 sin token.
"""
from datetime import date

from app.models.evaluacion import Evaluacion


def _crear_evaluacion(env, paciente_id: int, usuario_id: int, clasificacion="moderado", prob=0.45) -> int:
    """Crea una evaluación directo en BD para poder referenciarla."""
    db = env.new_session()
    try:
        ev = Evaluacion(
            paciente_id=paciente_id,
            usuario_id=usuario_id,
            edad=55,
            presion_alta=True,
            colesterol_alto=False,
            tabaquismo=False,
            actividad_fisica=True,
            antecedente_acv=False,
            diabetes=False,
            salud_general=3,
            dificultad_para_caminar=False,
            probabilidad=prob,
            clasificacion=clasificacion,
            modelo_version="1.0.0",
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)
        return ev.id
    finally:
        db.close()


# ---------------------------------------------------------------
# Crear
# ---------------------------------------------------------------

def test_crear_atencion_ok(env, usuarios_base):
    doctor = usuarios_base["doctor"]
    paciente = usuarios_base["paciente_doctor"]
    headers = env.auth_header(doctor.id, "usuario")

    resp = env.client.post(
        "/api/v1/atenciones/",
        headers=headers,
        json={
            "paciente_id": paciente.id,
            "diagnostico": "HTA no controlada + dislipidemia mixta.",
            "tratamiento": "Losartán 50mg cada 12h por 30 días.",
            "indicaciones": "Dieta hiposódica y control en 15 días.",
        },
    )

    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["paciente_id"] == paciente.id
    assert data["usuario_id"] == doctor.id
    assert data["evaluacion_id"] is None
    assert data["diagnostico"].startswith("HTA")
    assert data["paciente_nombre"]  # nombre resuelto para display
    assert data["id"] > 0


def test_crear_atencion_con_evaluacion(env, usuarios_base):
    doctor = usuarios_base["doctor"]
    paciente = usuarios_base["paciente_doctor"]
    evaluacion_id = _crear_evaluacion(env, paciente.id, doctor.id)
    headers = env.auth_header(doctor.id, "usuario")

    resp = env.client.post(
        "/api/v1/atenciones/",
        headers=headers,
        json={
            "paciente_id": paciente.id,
            "evaluacion_id": evaluacion_id,
            "diagnostico": "Riesgo moderado confirmado.",
            "tratamiento": "Cambios de estilo de vida.",
        },
    )

    assert resp.status_code == 201, resp.text
    assert resp.json()["evaluacion_id"] == evaluacion_id


def test_crear_atencion_paciente_inexistente(env, usuarios_base):
    doctor = usuarios_base["doctor"]
    headers = env.auth_header(doctor.id, "usuario")

    resp = env.client.post(
        "/api/v1/atenciones/",
        headers=headers,
        json={
            "paciente_id": 99999,
            "diagnostico": "Diagnóstico de prueba.",
            "tratamiento": "Tratamiento de prueba.",
        },
    )

    assert resp.status_code == 400, resp.text
    assert "Paciente no encontrado" in resp.json()["detail"]


def test_crear_atencion_evaluacion_inexistente(env, usuarios_base):
    doctor = usuarios_base["doctor"]
    paciente = usuarios_base["paciente_doctor"]
    headers = env.auth_header(doctor.id, "usuario")

    resp = env.client.post(
        "/api/v1/atenciones/",
        headers=headers,
        json={
            "paciente_id": paciente.id,
            "evaluacion_id": 99999,
            "diagnostico": "Diagnóstico de prueba.",
            "tratamiento": "Tratamiento de prueba.",
        },
    )

    assert resp.status_code == 400, resp.text
    assert "Evaluación no encontrada" in resp.json()["detail"]


def test_crear_atencion_evaluacion_de_otro_paciente(env, usuarios_base):
    doctor = usuarios_base["doctor"]
    paciente_doctor = usuarios_base["paciente_doctor"]
    paciente_enfermera = usuarios_base["paciente_enfermera"]

    # Evaluación del paciente de la enfermera...
    evaluacion_id = _crear_evaluacion(env, paciente_enfermera.id, doctor.id)

    # ...referenciada desde una atención del paciente del doctor → 400
    headers = env.auth_header(doctor.id, "usuario")
    resp = env.client.post(
        "/api/v1/atenciones/",
        headers=headers,
        json={
            "paciente_id": paciente_doctor.id,
            "evaluacion_id": evaluacion_id,
            "diagnostico": "Diagnóstico de prueba.",
            "tratamiento": "Tratamiento de prueba.",
        },
    )

    assert resp.status_code == 400, resp.text
    assert "no corresponde al paciente" in resp.json()["detail"]


# ---------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------

def test_listar_y_obtener_atencion(env, usuarios_base):
    doctor = usuarios_base["doctor"]
    paciente = usuarios_base["paciente_doctor"]
    headers = env.auth_header(doctor.id, "usuario")

    creada = env.client.post(
        "/api/v1/atenciones/",
        headers=headers,
        json={
            "paciente_id": paciente.id,
            "diagnostico": "Control de rutina.",
            "tratamiento": "Sin cambios.",
        },
    ).json()

    listado = env.client.get("/api/v1/atenciones/", headers=headers)
    assert listado.status_code == 200, listado.text
    assert any(a["id"] == creada["id"] for a in listado.json())

    detalle = env.client.get(f"/api/v1/atenciones/{creada['id']}", headers=headers)
    assert detalle.status_code == 200, detalle.text
    assert detalle.json()["id"] == creada["id"]


def test_historial_por_paciente(env, usuarios_base):
    doctor = usuarios_base["doctor"]
    paciente = usuarios_base["paciente_doctor"]
    headers = env.auth_header(doctor.id, "usuario")

    for i in range(2):
        env.client.post(
            "/api/v1/atenciones/",
            headers=headers,
            json={
                "paciente_id": paciente.id,
                "diagnostico": f"Consulta {i}",
                "tratamiento": "Tratamiento",
            },
        )

    resp = env.client.get(
        f"/api/v1/atenciones/by-paciente/{paciente.id}", headers=headers
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 2


def test_atencion_no_encontrada(env, usuarios_base):
    doctor = usuarios_base["doctor"]
    headers = env.auth_header(doctor.id, "usuario")

    resp = env.client.get("/api/v1/atenciones/99999", headers=headers)
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------
# Seguridad
# ---------------------------------------------------------------

def test_atenciones_requieren_token(env, usuarios_base):
    assert env.client.get("/api/v1/atenciones/").status_code == 401
    assert env.client.post(
        "/api/v1/atenciones/",
        json={"paciente_id": 1, "diagnostico": "x", "tratamiento": "y"},
    ).status_code == 401
