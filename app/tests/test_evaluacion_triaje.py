"""
test_evaluacion_triaje.py — TESTS DEL SERVICIO DE REGLAS CLÍNICAS (TRIAGE)

El triaje traduce probabilidad + clasificación del ML en texto clínico
accionable. Como es 100% determinista, se testea con datos fijos:

  - Clasificación → nivel_alerta + codigo_color (semáforo)
  - Inputs bools  → factores de riesgo / protectores detectados
  - Clasificación desconocida → fallback por umbrales de probabilidad
"""
from app.services.evaluacion_triaje_service import generar_triaje_clinico

# Paciente con varios factores de riesgo (caso del JSON real: id 7)
PACIENTE_MODERADO = {
    "presion_alta": True,
    "colesterol_alto": True,
    "tabaquismo": False,
    "actividad_fisica": True,
    "antecedente_acv": False,
    "diabetes": True,
    "salud_general": 3,
    "dificultad_para_caminar": False,
}


# ============================================================
# Clasificación → nivel de alerta + color
# ============================================================

def test_bajo_riesgo_es_verde():
    triaje = generar_triaje_clinico({}, probabilidad=0.1, clasificacion="bajo")
    assert triaje["codigo_color"] == "verde"
    assert "BAJO RIESGO" in triaje["nivel_alerta"]
    assert "anuales" in triaje["accion_sugerida"].lower()


def test_moderado_es_amarillo():
    triaje = generar_triaje_clinico({}, probabilidad=0.459186, clasificacion="moderado")
    assert triaje["codigo_color"] == "amarillo"
    assert "MODERADO" in triaje["nivel_alerta"]
    assert "15 a 30 días" in triaje["accion_sugerida"]


def test_alto_es_rojo():
    triaje = generar_triaje_clinico({}, probabilidad=0.9, clasificacion="alto")
    assert triaje["codigo_color"] == "rojo"
    assert "ALTA PRIORIDAD" in triaje["nivel_alerta"]
    assert "Cardiología" in triaje["accion_sugerida"]


def test_clasificacion_acepta_enum():
    """Debe funcionar tanto con 'bajo' str como con ClasificacionEnum."""
    from app.schemas.evaluacion import ClasificacionEnum
    triaje = generar_triaje_clinico({}, 0.1, ClasificacionEnum.bajo)
    assert triaje["codigo_color"] == "verde"


def test_clasificacion_desconocida_cae_a_probabilidad():
    """Si llega una clasificación rara, se deriva de la probabilidad."""
    triaje = generar_triaje_clinico({}, probabilidad=0.459186, clasificacion="???")
    assert triaje["codigo_color"] == "amarillo"


# ============================================================
# Factores de riesgo / protectores
# ============================================================

def test_detecta_factores_de_riesgo():
    triaje = generar_triaje_clinico(PACIENTE_MODERADO, 0.459186, "moderado")
    assert "Hipertensión Arterial" in triaje["factores_riesgo_detectados"]
    assert "Dislipidemia (Colesterol Alto)" in triaje["factores_riesgo_detectados"]
    assert "Diabetes Mellitus" in triaje["factores_riesgo_detectados"]
    # No fumador ni ACV ni dificultad para caminar → NO deben aparecer
    assert "Consumo de Tabaco Activo" not in triaje["factores_riesgo_detectados"]
    assert "Antecedente de Accidente Cerebrovascular (ACV)" not in triaje["factores_riesgo_detectados"]


def test_detecta_factores_protectores():
    triaje = generar_triaje_clinico(PACIENTE_MODERADO, 0.459186, "moderado")
    assert "Realiza Actividad Física Regular" in triaje["factores_protectores"]
    assert "No Fumador" in triaje["factores_protectores"]


def test_sin_factores_da_listas_vacias():
    triaje = generar_triaje_clinico({}, 0.1, "bajo")
    assert triaje["factores_riesgo_detectados"] == []
    # Sin actividad física y sin tabaquismo → solo "No Fumador" como protector
    assert triaje["factores_protectores"] == ["No Fumador"]


def test_tabaquismo_true_es_riesgo_y_no_protector():
    data = {"tabaquismo": True, "actividad_fisica": False}
    triaje = generar_triaje_clinico(data, 0.7, "alto")
    assert "Consumo de Tabaco Activo" in triaje["factores_riesgo_detectados"]
    assert "No Fumador" not in triaje["factores_protectores"]


def test_salud_general_mala_es_factor_de_riesgo():
    triaje = generar_triaje_clinico({"salud_general": 5}, 0.7, "alto")
    assert "Salud General Regular o Mala" in triaje["factores_riesgo_detectados"][0] or \
           "Salud General" in triaje["factores_riesgo_detectados"][0]


def test_recomendaciones_no_vacias_por_nivel():
    for clasificacion in ("bajo", "moderado", "alto"):
        triaje = generar_triaje_clinico({}, 0.5, clasificacion)
        assert len(triaje["recomendaciones_medicas"]) >= 1