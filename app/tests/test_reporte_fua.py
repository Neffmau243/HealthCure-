"""
test_reporte_fua.py — TESTS DEL REPORTE PDF (FORMATO ÚNICO DE ATENCIÓN)

Cubre:
  - Test UNITARIO del generador puro (generar_fua_pdf): genera bytes %PDF
    válidos a partir de objetos ORM construidos en memoria (sin BD).
  - Test de INTEGRACIÓN del endpoint GET /api/v1/evaluaciones/{id}/fua
    (con SQLite en memoria, igual que el resto de la suite).

El PDF tiene DOS partes:
  - página 1: el formulario FUA OFICIAL del SIS (plantilla) con los datos escritos encima
  - páginas siguientes: anexo dibujado con ReportLab (resultado del modelo, factores...)

Los tests verifican el header %PDF, que la página 1 contenga el texto del formulario
oficial MÁS los datos del paciente, y que el anexo exista; el aspecto visual se valida
abriendo el archivo.
"""
from datetime import datetime, date
from io import BytesIO

from pypdf import PdfReader

from app.services.reporte_service import generar_fua_pdf
from app.services.fua_oficial import (
    FuaDatos, RUTA_PLANTILLA, PAGE_W, PAGE_H, _codigo_tdi, pagina_fua_oficial, resumir,
)
from app.models.paciente import Paciente
from app.models.usuario import Usuario
from app.models.evaluacion import Evaluacion


# ============================================================
# Helper: construir objetos ORM en memoria (sin tocar BD)
# ============================================================
def _build_paciente() -> Paciente:
    return Paciente(
        tipo_documento="DNI",
        documento_identidad="1032456789",
        numero_historia_clinica="72769512",
        apellido_paterno="Pérez",
        apellido_materno="Rodríguez",
        nombres="Juan",
        fecha_nacimiento=date(1965, 5, 20),
        sexo="M",
        direccion="Av. Principal 123",
        tipo_seguro="SIS",
        codigo_afiliacion_seguro="040-2-1032456789",
        talla_cm=172.5,
        peso_kg=85.3,
        activo=True,
    )


def _build_usuario() -> Usuario:
    return Usuario(
        nombre="Dr. Carlos García",
        email="dr.garcia@healthcure.com",
        password_hash="x",
        rol="usuario",
        activo=True,
    )


def _build_evaluacion(**overrides) -> Evaluacion:
    """Evaluación moderada con triaje persistido (similar al seed/API)."""
    valores = {
        "id": 8,
        "paciente_id": 1,
        "usuario_id": 2,
        "edad": 55,
        "presion_alta": True,
        "colesterol_alto": True,
        "tabaquismo": False,
        "actividad_fisica": True,
        "antecedente_acv": False,
        "diabetes": True,
        "salud_general": 3,
        "dificultad_para_caminar": False,
        "probabilidad": 0.459186,
        "clasificacion": "moderado",
        "modelo_version": "1.0.0",
        "nivel_alerta": "RIESGO MODERADO - SEGUIMIENTO PREVENTIVO",
        "codigo_color": "amarillo",
        "accion_sugerida": "Programar consulta médica de control en los próximos 15 a 30 días.",
        "factores_riesgo_detectados": ["Hipertensión Arterial", "Diabetes Mellitus"],
        "factores_protectores": ["No Fumador"],
        "recomendaciones_medicas": ["Solicitar perfil lipídico."],
        "created_at": datetime(2026, 9, 5, 8, 30, 13),
    }
    valores.update(overrides)
    evaluacion = Evaluacion(**valores)
    # Relaciones en memoria (sin session): se asignan como atributos
    evaluacion.paciente = _build_paciente()
    evaluacion.usuario = _build_usuario()
    return evaluacion


# ============================================================
# Test unitario del generador
# ============================================================
def test_genera_pdf_valido():
    pdf = generar_fua_pdf(_build_evaluacion())
    assert pdf[:5] == b"%PDF-"          # Header mágico de cualquier PDF
    assert len(pdf) > 3000               # Debe tener contenido real


def test_genera_pdf_para_riesgo_bajo():
    """También debe funcionar con clasificación 'bajo' (color verde)."""
    eval_baja = _build_evaluacion(
        clasificacion="bajo",
        nivel_alerta="BAJO RIESGO - CONTROL DE RUTINA",
        codigo_color="verde",
        probabilidad=0.15,
        presion_alta=False,
        colesterol_alto=False,
        diabetes=False,
    )
    pdf = generar_fua_pdf(eval_baja)
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 3000


def test_genera_pdf_para_riesgo_alto():
    """Y con clasificación 'alto' (color rojo)."""
    eval_alta = _build_evaluacion(
        clasificacion="alto",
        nivel_alerta="ALTA PRIORIDAD - RIESGO ELEVADO",
        codigo_color="rojo",
        probabilidad=0.85,
        tabaquismo=True,
        antecedente_acv=True,
        dificultad_para_caminar=True,
    )
    pdf = generar_fua_pdf(eval_alta)
    assert pdf[:5] == b"%PDF-"


def test_genera_pdf_sin_factores_persistidos():
    """Evaluación 'legacy' (triaje NULL) → el reporte recalcula el triaje."""
    eval_legacy = _build_evaluacion(
        nivel_alerta=None, codigo_color=None, accion_sugerida=None,
        factores_riesgo_detectados=None, factores_protectores=None,
        recomendaciones_medicas=None,
    )
    pdf = generar_fua_pdf(eval_legacy)
    assert pdf[:5] == b"%PDF-"


# ============================================================
# Tests del formulario FUA oficial (plantilla + datos encima)
# ============================================================
def _paginas(pdf: bytes):
    return PdfReader(BytesIO(pdf)).pages


def test_plantilla_oficial_es_una_sola_pagina_sin_texto_de_la_directiva():
    paginas = PdfReader(str(RUTA_PLANTILLA)).pages
    assert len(paginas) == 1
    texto = paginas[0].extract_text()
    assert "FORMATO ÚNICO DE ATENCIÓN - FUA" in texto
    assert "DIRECTIVA ADMINISTRATIVA" not in texto      # el encabezado de la Directiva se recortó


def test_pagina_1_es_el_formulario_oficial_con_los_datos_del_paciente():
    paginas = _paginas(generar_fua_pdf(_build_evaluacion()))
    assert len(paginas) >= 2                              # formulario + anexo
    p1 = paginas[0].extract_text()
    for esperado in ["FORMATO ÚNICO DE ATENCIÓN - FUA",     # texto del formulario oficial
                     "PÉREZ", "RODRÍGUEZ", "JUAN",           # apellidos y nombre
                     "1032456789", "72769512",               # documento e historia clínica
                     "00000008", "172.5", "85.3"]:           # correlativo, talla, peso
        assert esperado in p1, esperado
    assert "ANEXO AL FORMATO UNICO DE ATENCION" in paginas[1].extract_text()


def test_pagina_del_formulario_es_oficio():
    p1 = _paginas(generar_fua_pdf(_build_evaluacion()))[0]
    assert abs(float(p1.mediabox.width) - PAGE_W) < 1
    assert abs(float(p1.mediabox.height) - PAGE_H) < 1


def test_formulario_sin_datos_opcionales_no_falla():
    pdf = pagina_fua_oficial(FuaDatos())                  # todo vacío: solo la plantilla
    assert len(_paginas(pdf)) == 1


def test_formulario_con_seguro_de_otra_iafas_y_emergencia():
    d = FuaDatos(tipo_documento="CE", documento="X123", tipo_seguro="EsSalud",
                 codigo_seguro="67011841PSHR006", emergencia=True,
                 fecha_atencion=datetime(2026, 11, 1, 23, 5))
    texto = _paginas(pagina_fua_oficial(d))[0].extract_text()
    assert "67011841PSHR006" in texto and "X123" in texto


def test_codigo_tdi_segun_directiva():
    assert _codigo_tdi("DNI") == "2"
    assert _codigo_tdi("CE") == "3"
    assert _codigo_tdi("Pasaporte") == ""                 # la Directiva no define código


def test_resumir_diagnostico_largo_una_linea():
    assert resumir("Hipertensión   arterial\nleve") == "Hipertensión arterial leve"
    largo = resumir("x" * 300)
    assert len(largo) == 78 and largo.endswith("…")


# ============================================================
# Test de integración del endpoint
# ============================================================
def _crear_evaluacion_en_bd(env, paciente_id: int, usuario_id: int) -> int:
    """Inserta una evaluación directo en SQLite (evita el ML) y devuelve su ID."""
    db = env.new_session()
    try:
        e = Evaluacion(
            paciente_id=paciente_id,
            usuario_id=usuario_id,
            edad=55,
            presion_alta=True,
            colesterol_alto=True,
            tabaquismo=False,
            actividad_fisica=True,
            antecedente_acv=False,
            diabetes=True,
            salud_general=3,
            dificultad_para_caminar=False,
            probabilidad=0.459186,
            clasificacion="moderado",
            modelo_version="1.0.0",
            nivel_alerta="RIESGO MODERADO - SEGUIMIENTO PREVENTIVO",
            codigo_color="amarillo",
            accion_sugerida="Programar consulta médica de control.",
            factores_riesgo_detectados=["Hipertensión Arterial", "Diabetes Mellitus"],
            factores_protectores=["No Fumador"],
            recomendaciones_medicas=["Solicitar perfil lipídico."],
            created_at=datetime(2026, 9, 5, 8, 30, 13),
        )
        db.add(e)
        db.commit()
        db.refresh(e)
        return e.id
    finally:
        db.close()


def test_endpoint_fua_devuelve_pdf(env, usuarios_base):
    """GET /api/v1/evaluaciones/{id}/fua → 200 con application/pdf."""
    evaluacion_id = _crear_evaluacion_en_bd(
        env,
        paciente_id=usuarios_base["paciente_doctor"].id,
        usuario_id=usuarios_base["doctor"].id,
    )
    h = env.auth_header(usuarios_base["doctor"].id, "usuario")
    r = env.client.get(f"/api/v1/evaluaciones/{evaluacion_id}/fua", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
    assert r.content[:5] == b"%PDF-"


def test_endpoint_fua_404_si_no_existe(env, usuarios_base):
    h = env.auth_header(usuarios_base["doctor"].id, "usuario")
    r = env.client.get("/api/v1/evaluaciones/99999/fua", headers=h)
    assert r.status_code == 404
