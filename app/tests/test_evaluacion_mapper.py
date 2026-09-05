"""
test_evaluacion_mapper.py — TESTS DEL MAPPER DE EVALUACIONES

El mapper es el traductor entre capas y es 100% lógico (sin BD):
  - request_to_model_input: request → vector del modelo ML
  - create_to_model:        request + predicción → dict para BD
  - to_response:            ORM → DTO de respuesta

Probar estas transformaciones es clave porque un error aquí produce
predicciones o respuestas incorrectas silenciosamente.
"""
from datetime import datetime
from decimal import Decimal

from app.mappers.evaluacion_mapper import EvaluacionMapper
from app.schemas.evaluacion import EvaluacionCreate, PredictionResult, ClasificacionEnum
from app.models.evaluacion import Evaluacion

# --- Datos base reutilizables ---

DATOS_VALIDOS = {
    "paciente_id": 7,
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


def _create_request(**overrides) -> EvaluacionCreate:
    data = {**DATOS_VALIDOS, **overrides}
    return EvaluacionCreate(**data)


# ============================================================
# request_to_model_input
# ============================================================

def test_request_a_model_input_convierte_bools_a_ints():
    """El modelo ML espera números: True → 1, False → 0."""
    result = EvaluacionMapper.request_to_model_input(_create_request())

    assert result["edad"] == 55
    assert result["presion_alta"] == 1
    assert result["colesterol_alto"] == 1
    assert result["tabaquismo"] == 0
    assert result["actividad_fisica"] == 1
    assert result["antecedente_acv"] == 0
    assert result["diabetes"] == 1
    assert result["salud_general"] == 3
    assert result["dificultad_para_caminar"] == 0


def test_request_a_model_input_descarta_paciente_id():
    """paciente_id es administrativo: el modelo no debe recibirlo."""
    result = EvaluacionMapper.request_to_model_input(_create_request())
    assert "paciente_id" not in result


def test_request_a_model_input_tiene_las_9_variables():
    """El modelo fue entrenado con exactamente 9 features."""
    result = EvaluacionMapper.request_to_model_input(_create_request())
    assert len(result) == 9
    assert set(result.keys()) == {
        "edad", "presion_alta", "colesterol_alto", "tabaquismo",
        "actividad_fisica", "antecedente_acv", "diabetes",
        "salud_general", "dificultad_para_caminar",
    }


# ============================================================
# create_to_model
# ============================================================

def test_create_to_model_une_request_y_prediccion():
    """El dict para BD debe tener request + predicción + usuario_id."""
    request = _create_request()
    prediccion = PredictionResult(
        probabilidad=0.734521,
        clasificacion=ClasificacionEnum.alto,
        modelo_version="1.0.0",
    )

    result = EvaluacionMapper.create_to_model(request, prediccion, usuario_id=3)

    # Datos del request (bools se guardan como bool en BD)
    assert result["paciente_id"] == 7
    assert result["usuario_id"] == 3
    assert result["edad"] == 55
    assert result["presion_alta"] is True
    assert result["diabetes"] is True

    # Resultado del ML
    assert result["probabilidad"] == 0.734521
    assert result["clasificacion"] == ClasificacionEnum.alto
    assert result["modelo_version"] == "1.0.0"


def test_create_to_model_guardar_clasificacion_enum():
    """La clasificación debe persistirse como Enum (no string suelto)."""
    request = _create_request()
    prediccion = PredictionResult(
        probabilidad=0.1,
        clasificacion=ClasificacionEnum.bajo,
        modelo_version="1.0.0",
    )
    result = EvaluacionMapper.create_to_model(request, prediccion, usuario_id=1)
    assert result["clasificacion"] == ClasificacionEnum.bajo


# ============================================================
# to_response
# ============================================================

def _build_evaluacion_orm(**overrides) -> Evaluacion:
    """Construye un objeto ORM Evaluacion sin tocar BD."""
    valores = {
        "id": 1,
        "paciente_id": 7,
        "usuario_id": 3,
        "edad": 55,
        "presion_alta": True,
        "colesterol_alto": True,
        "tabaquismo": False,
        "actividad_fisica": True,
        "antecedente_acv": False,
        "diabetes": True,
        "salud_general": 3,
        "dificultad_para_caminar": False,
        "probabilidad": Decimal("0.734521"),
        "clasificacion": "alto",
        "modelo_version": "1.0.0",
        "created_at": datetime(2026, 9, 1, 12, 0, 0),
    }
    valores.update(overrides)
    return Evaluacion(**valores)


def test_to_response_convierte_decimal_a_float():
    """MySQL guarda DECIMAL(7,6); la API debe retornar float."""
    response = EvaluacionMapper.to_response(_build_evaluacion_orm())
    assert response.probabilidad == 0.734521
    assert isinstance(response.probabilidad, float)


def test_to_response_convierte_string_a_clasificacion_enum():
    response = EvaluacionMapper.to_response(_build_evaluacion_orm())
    assert response.clasificacion == ClasificacionEnum.alto


def test_to_response_pasa_campos_esenciales():
    response = EvaluacionMapper.to_response(_build_evaluacion_orm())
    assert response.paciente_id == 7
    assert response.usuario_id == 3
    assert response.edad == 55
    assert response.presion_alta is True
    assert response.modelo_version == "1.0.0"
