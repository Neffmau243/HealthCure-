"""
Tests del dashboard analítico y los reportes (app/api/v1/reportes.py).

Se siembran evaluaciones con fechas, bandas, edades y distritos conocidos para
comprobar que los agregados SQL coinciden con lo esperado (y que los días sin
datos aparecen con cero), más permisos, filtros y exportación CSV.
"""
from datetime import date, datetime, time, timedelta

import pytest

from app.models.distrito import Distrito
from app.models.evaluacion import Evaluacion
from app.models.paciente import Paciente

HOY = date.today()


def _dt(dias_atras: int, hora: int = 10) -> datetime:
    return datetime.combine(HOY - timedelta(days=dias_atras), time(hora, 0))


def _evaluar(db, paciente_id, usuario_id, *, dias_atras, banda, indice, edad=50, **factores):
    db.add(Evaluacion(
        paciente_id=paciente_id, usuario_id=usuario_id, edad=edad,
        presion_alta=factores.get("presion_alta", False), colesterol_alto=factores.get("colesterol_alto", False),
        tabaquismo=factores.get("tabaquismo", False), actividad_fisica=factores.get("actividad_fisica", True),
        antecedente_acv=False, diabetes=factores.get("diabetes", False), salud_general=3,
        dificultad_para_caminar=False, probabilidad=indice, clasificacion=banda,
        modelo_version="test", created_at=_dt(dias_atras),
        alerta_clinica=factores.get("alerta"),
    ))


@pytest.fixture()
def datos(env, usuarios_base):
    """
    Distritos: Cayma (2 pacientes), Yanahuara (1), y un paciente sin distrito.
    Evaluaciones (hoy = día 0):
      hoy:      Juan  moderado 0.45 (edad 50, presión alta)
      hoy:      Maria alto     0.80 (edad 65, diabetes, sedentaria)
      ayer:     Juan  bajo     0.10 (edad 30)
      hace 3d:  Legacy alto    0.70 (edad 70, presión alta)  [sin distrito]
      hace 40d: Maria bajo     0.20 (edad 25)  → fuera del periodo de 30 días
    """
    u = usuarios_base
    with env.new_session() as db:
        cayma, yana = Distrito(nombre="Cayma"), Distrito(nombre="Yanahuara")
        db.add_all([cayma, yana])
        db.flush()
        db.get(Paciente, u["paciente_doctor"].id).distrito_id = cayma.id       # Juan
        db.get(Paciente, u["paciente_enfermera"].id).distrito_id = cayma.id    # Maria
        # Legacy queda sin distrito; sumamos un tercer paciente en Yanahuara sin evaluaciones
        db.add(Paciente(tipo_documento="DNI", documento_identidad="44444444", apellido_paterno="Zeta",
                        apellido_materno="Y", nombres="Pedro", fecha_nacimiento=date(1990, 1, 1), sexo="M",
                        tipo_seguro="SIS", activo=True, distrito_id=yana.id))
        j, m, l = u["paciente_doctor"].id, u["paciente_enfermera"].id, u["paciente_legacy"].id
        d = u["doctor"].id
        _evaluar(db, j, d, dias_atras=0, banda="moderado", indice=0.45, edad=50, presion_alta=True)
        _evaluar(db, m, d, dias_atras=0, banda="alto", indice=0.80, edad=65, diabetes=True, actividad_fisica=False,
                 alerta={"nivel": "inmediata", "titulo": "Signos de alarma: valoración inmediata"})
        _evaluar(db, j, d, dias_atras=1, banda="bajo", indice=0.10, edad=30)
        _evaluar(db, l, d, dias_atras=3, banda="alto", indice=0.70, edad=70, presion_alta=True)
        _evaluar(db, m, d, dias_atras=40, banda="bajo", indice=0.20, edad=25)
        db.commit()
    return {"h": env.auth_header(u["doctor"].id, "usuario"), "a": env.auth_header(u["admin"].id, "admin"), **u}


def _get(env, ruta, h, **params):
    return env.client.get(f"/api/v1/reportes{ruta}", headers=h, params=params)


# ── Dashboard ───────────────────────────────────────────────────────────
def test_dashboard_exige_autenticacion(env):
    assert env.client.get("/api/v1/reportes/dashboard").status_code == 401


def test_dashboard_vacio_devuelve_ceros_sin_dividir_por_cero(env, usuarios_base):
    r = _get(env, "/dashboard", env.auth_header(usuarios_base["doctor"].id, "usuario"), dias=7)
    assert r.status_code == 200
    d = r.json()
    assert d["kpis"]["evaluaciones"] == 0 and d["kpis"]["porcentaje_alto"] == 0 and d["kpis"]["indice_promedio"] == 0
    assert len(d["serie_diaria"]) == 7 and all(p["total"] == 0 for p in d["serie_diaria"])
    assert d["por_distrito"] == [] and all(f["cantidad"] == 0 and f["porcentaje"] == 0 for f in d["factores"])


def test_dashboard_kpis_y_distribucion_del_periodo(env, datos):
    d = _get(env, "/dashboard", datos["h"], dias=30).json()
    k = d["kpis"]
    assert (k["evaluaciones"], k["evaluaciones_hoy"], k["pacientes_evaluados"]) == (4, 2, 3)   # excluye la de hace 40 días
    assert (k["riesgo_alto"], k["riesgo_moderado"], k["riesgo_bajo"]) == (2, 1, 1)
    assert k["porcentaje_alto"] == 50.0
    assert k["indice_promedio"] == pytest.approx(51.2, abs=0.1)        # (45+80+10+70)/4
    assert k["pacientes_registrados"] == 4
    assert d["distribucion"] == {"bajo": 1, "moderado": 1, "alto": 2}
    assert d["desde"] == (HOY - timedelta(days=29)).isoformat() and d["hasta"] == HOY.isoformat()


def test_serie_diaria_rellena_dias_sin_evaluaciones(env, datos):
    serie = _get(env, "/dashboard", datos["h"], dias=7).json()["serie_diaria"]
    assert len(serie) == 7 and serie[-1]["fecha"] == HOY.isoformat()
    por_fecha = {p["fecha"]: p for p in serie}
    assert por_fecha[HOY.isoformat()] == {"fecha": HOY.isoformat(), "total": 2, "bajo": 0, "moderado": 1, "alto": 1}
    assert por_fecha[(HOY - timedelta(days=1)).isoformat()]["bajo"] == 1
    assert por_fecha[(HOY - timedelta(days=2)).isoformat()]["total"] == 0          # día vacío = 0
    assert por_fecha[(HOY - timedelta(days=3)).isoformat()]["alto"] == 1
    assert sum(p["total"] for p in serie) == 4


def test_periodo_corto_deja_fuera_lo_antiguo(env, datos):
    assert _get(env, "/dashboard", datos["h"], dias=7).json()["kpis"]["evaluaciones"] == 4
    assert _get(env, "/dashboard", datos["h"], dias=90).json()["kpis"]["evaluaciones"] == 5


def test_distritos_ordenados_y_con_sin_distrito(env, datos):
    filas = _get(env, "/dashboard", datos["h"], dias=30).json()["por_distrito"]
    assert [f["distrito"] for f in filas] == ["Cayma", "Sin distrito"]       # Yanahuara no tiene evaluaciones
    cayma = filas[0]
    assert (cayma["evaluaciones"], cayma["pacientes"], cayma["alto"]) == (3, 2, 1)
    assert filas[1]["evaluaciones"] == 1 and filas[1]["alto"] == 1


def test_factores_y_grupos_de_edad(env, datos):
    d = _get(env, "/dashboard", datos["h"], dias=30).json()
    f = {x["clave"]: x for x in d["factores"]}
    assert f["presion_alta"]["cantidad"] == 2 and f["presion_alta"]["porcentaje"] == 50.0
    assert f["diabetes"]["cantidad"] == 1 and f["actividad_fisica"]["etiqueta"] == "Sedentarismo"
    assert f["actividad_fisica"]["cantidad"] == 1                          # solo Maria es sedentaria
    assert [x["clave"] for x in d["factores"]][0] == "presion_alta"       # ordenados de mayor a menor
    g = {x["grupo"]: x for x in d["por_grupo_edad"]}
    assert (g["18-39"]["total"], g["40-59"]["total"], g["60+"]["total"], g["0-17"]["total"]) == (1, 1, 2, 0)
    assert g["60+"]["alto"] == 2


@pytest.mark.parametrize("dias", [0, 5, 31, 1000, -7])
def test_periodo_no_permitido_es_400(env, datos, dias):
    assert _get(env, "/dashboard", datos["h"], dias=dias).status_code == 400


# ── Tabla filtrable ─────────────────────────────────────────────────────
def test_tabla_paginada_mas_recientes_primero(env, datos):
    r = _get(env, "/evaluaciones", datos["h"], limit=2, offset=0).json()
    assert r["total"] == 5 and len(r["items"]) == 2
    assert r["items"][0]["fecha"] >= r["items"][1]["fecha"]
    resto = _get(env, "/evaluaciones", datos["h"], limit=2, offset=4).json()
    assert len(resto["items"]) == 1 and resto["items"][0]["edad"] == 25


def test_tabla_filtra_por_banda_fechas_distrito_y_texto(env, datos):
    h = datos["h"]
    altos = _get(env, "/evaluaciones", h, clasificacion="alto").json()
    assert altos["total"] == 2 and {i["clasificacion"] for i in altos["items"]} == {"alto"}
    assert _get(env, "/evaluaciones", h, desde=(HOY - timedelta(days=1)).isoformat()).json()["total"] == 3
    assert _get(env, "/evaluaciones", h, hasta=(HOY - timedelta(days=39)).isoformat()).json()["total"] == 1
    with env.new_session() as db:
        cayma_id = db.query(Distrito).filter_by(nombre="Cayma").one().id
    assert _get(env, "/evaluaciones", h, distrito_id=cayma_id).json()["total"] == 4
    assert _get(env, "/evaluaciones", h, q="juan").json()["total"] == 2
    assert _get(env, "/evaluaciones", h, q="33333333").json()["total"] == 1       # por documento
    assert _get(env, "/evaluaciones", h, q="no-existe").json()["total"] == 0


def test_fila_trae_indice_distrito_y_alerta(env, datos):
    fila = _get(env, "/evaluaciones", datos["h"], clasificacion="alto", q="maria").json()["items"][0]
    assert fila["indice"] == 80.0 and fila["distrito"] == "Cayma" and fila["edad"] == 65
    assert fila["alerta"] == "Signos de alarma: valoración inmediata"
    sin = _get(env, "/evaluaciones", datos["h"], q="legacy").json()["items"][0]
    assert sin["distrito"] is None and sin["alerta"] is None


def test_tabla_valida_parametros(env, datos):
    h = datos["h"]
    assert _get(env, "/evaluaciones", h, desde="2026-12-01", hasta="2026-01-01").status_code == 400
    assert _get(env, "/evaluaciones", h, clasificacion="critico").status_code == 422
    assert _get(env, "/evaluaciones", h, limit=1000).status_code == 422
    assert _get(env, "/evaluaciones", h, offset=-1).status_code == 422
    assert env.client.get("/api/v1/reportes/evaluaciones").status_code == 401


# ── Exportación CSV ─────────────────────────────────────────────────────
def test_exportar_solo_admin(env, datos):
    assert _get(env, "/evaluaciones/export", datos["h"]).status_code == 403
    assert env.client.get("/api/v1/reportes/evaluaciones/export").status_code == 401


def test_csv_sin_datos_personales_y_con_filtros(env, datos):
    r = _get(env, "/evaluaciones/export", datos["a"], clasificacion="alto")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"] and ".csv" in r.headers["content-disposition"]
    texto = r.content.decode("utf-8")
    assert texto.startswith("﻿")                                   # BOM para Excel
    lineas = [l for l in texto.lstrip("﻿").split("\r\n") if l]
    assert len(lineas) == 3                                              # cabecera + 2 evaluaciones altas
    assert lineas[0].startswith("id_evaluacion,fecha,edad,sexo,distrito,banda_modelo,indice_0_100")
    for prohibido in ("Juan", "Maria", "Legacy", "Apellido", "11111111", "22222222", "33333333"):
        assert prohibido not in texto
    assert "inmediata" in texto and "80.0" in texto


def test_csv_neutraliza_formulas_en_texto_libre(env, datos):
    with env.new_session() as db:
        db.query(Distrito).filter_by(nombre="Cayma").one().nombre = "=HYPERLINK(\"http://x\")"
        db.commit()
    texto = _get(env, "/evaluaciones/export", datos["a"]).content.decode("utf-8")
    assert "'=HYPERLINK" in texto
    assert ",=HYPERLINK" not in texto


def test_csv_rango_invertido_es_400(env, datos):
    assert _get(env, "/evaluaciones/export", datos["a"], desde="2026-12-01", hasta="2026-01-01").status_code == 400
