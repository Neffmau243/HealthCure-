"""
test_evaluaciones_resumen.py — TESTS DEL RESUMEN AGREGADO DE EVALUACIONES

Cubre `GET /api/v1/evaluaciones/resumen`, el endpoint de solo lectura que
alimenta los KPIs del dashboard y la cola diaria de triaje.

Lo importante que se prueba aquí es la REGLA DEL DÍA: un paciente con una
evaluación de ayer NO cuenta como evaluado hoy, porque la cola de triaje es
por visita/día (antes el frontend marcaba como "evaluado" a todo paciente
con cualquier evaluación histórica, así que la cola se vaciaba sola).
"""
from datetime import datetime, timedelta

from sqlalchemy import text


def _crear_evaluacion(env, paciente_id: int, usuario_id: int, edad: int = 60) -> dict:
    """Crea una evaluación real por HTTP (ejecuta el modelo XGBoost)."""
    r = env.client.post(
        "/api/v1/evaluaciones/",
        headers=env.auth_header(usuario_id, "usuario"),
        json={
            "paciente_id": paciente_id,
            "edad": edad,
            "presion_alta": True,
            "colesterol_alto": True,
            "tabaquismo": False,
            "actividad_fisica": True,
            "antecedente_acv": False,
            "diabetes": False,
            "salud_general": 3,
            "dificultad_para_caminar": False,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _retroceder_fecha(env, evaluacion_id: int, dias: int) -> None:
    """Mueve el created_at de una evaluación al pasado (simula 'ayer')."""
    momento = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
    db = env.new_session()
    try:
        db.execute(
            text("UPDATE evaluaciones SET created_at = :f WHERE id = :i"),
            {"f": momento, "i": evaluacion_id},
        )
        db.commit()
    finally:
        db.close()


def test_resumen_requiere_token(env, usuarios_base):
    """Sin token → 401. El resumen no es público."""
    assert env.client.get("/api/v1/evaluaciones/resumen").status_code == 401


def test_resumen_vacio_devuelve_ceros_y_las_tres_claves(env, usuarios_base):
    """Sin datos: todo en 0 y las 3 bandas presentes (el front no se defiende)."""
    r = env.client.get(
        "/api/v1/evaluaciones/resumen",
        headers=env.auth_header(usuarios_base["doctor"].id, "usuario"),
    )
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["total_evaluaciones"] == 0
    assert datos["total_hoy"] == 0
    assert datos["pacientes_evaluados_hoy"] == []
    assert datos["por_clasificacion"] == {"bajo": 0, "moderado": 0, "alto": 0}


def test_resumen_cuenta_total_y_por_clasificacion(env, usuarios_base):
    """El total y los conteos por banda son exactos (COUNT en SQL, no páginas)."""
    paciente = usuarios_base["paciente_doctor"]
    usuario = usuarios_base["doctor"]
    esperado = {}

    for i in range(3):
        ev = _crear_evaluacion(env, paciente.id, usuario.id, edad=50 + i)
        esperado[ev["clasificacion"]] = esperado.get(ev["clasificacion"], 0) + 1

    r = env.client.get(
        "/api/v1/evaluaciones/resumen",
        headers=env.auth_header(usuario.id, "usuario"),
    )
    datos = r.json()
    assert datos["total_evaluaciones"] == 3
    assert datos["por_clasificacion"]["bajo"] == esperado.get("bajo", 0)
    assert datos["por_clasificacion"]["moderado"] == esperado.get("moderado", 0)
    assert datos["por_clasificacion"]["alto"] == esperado.get("alto", 0)
    assert sum(datos["por_clasificacion"].values()) == 3


def test_resumen_marca_evaluado_hoy_solo_si_es_de_hoy(env, usuarios_base):
    """
    REGLA DEL DÍA: el paciente evaluado ayer vuelve a estar pendiente hoy.
    Es la diferencia con el comportamiento anterior (histórico = evaluado).
    """
    usuario = usuarios_base["doctor"]
    paciente_hoy = usuarios_base["paciente_doctor"]
    paciente_ayer = usuarios_base["paciente_enfermera"]

    ev_hoy = _crear_evaluacion(env, paciente_hoy.id, usuario.id)
    ev_ayer = _crear_evaluacion(env, paciente_ayer.id, usuario.id)
    _retroceder_fecha(env, ev_ayer["id"], dias=1)

    datos = env.client.get(
        "/api/v1/evaluaciones/resumen",
        headers=env.auth_header(usuario.id, "usuario"),
    ).json()

    assert datos["total_evaluaciones"] == 2, "el total cuenta el histórico completo"
    assert datos["total_hoy"] == 1, "solo la evaluación de hoy"
    assert datos["pacientes_evaluados_hoy"] == [paciente_hoy.id]
    assert paciente_ayer.id not in datos["pacientes_evaluados_hoy"], (
        "un paciente triado ayer debe seguir pendiente hoy"
    )
    assert ev_hoy["id"] != ev_ayer["id"]
