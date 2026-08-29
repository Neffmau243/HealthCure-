"""
evaluacion.py — SCHEMAS (DTOs) PARA EVALUACIONES CARDÍACAS

Los schemas de evaluación tienen Doble función:
  1. Definir qué datos RECIBE la API (EvaluacionCreate)
  2. Definir qué datos RETORNA la API (EvaluacionResponse)
  3. Transportar el resultado del modelo ML entre capas (PredictionResult)

Separación clave:
  - EvaluacionCreate incluye paciente_id + variables predictoras
  - EvaluacionResponse incluye TODO + el resultado de la predicción
  - PredictionResult es solo el output del modelo ML (sin DB)
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class ClasificacionEnum(str, Enum):
    """
    Niveles de riesgo cardíaco calculados por el modelo.
    Se derivan de la probabilidad:
      - bajo:     probabilidad < 0.30 (30%)
      - moderado: probabilidad 0.30 - 0.60 (30-60%)
      - alto:     probabilidad > 0.60 (60%)
    """
    bajo = "bajo"
    moderado = "moderado"
    alto = "alto"


class EvaluacionCreate(BaseModel):
    """
    DTO de ENTRADA — lo que el frontend envía para hacer una evaluación.

    Incluye:
      - paciente_id: para saber de quién es la evaluación
      - Variables predictoras: los datos que entran al modelo ML

    Ejemplo JSON:
    {
        "paciente_id": 1,
        "edad": 55,
        "presion_alta": true,
        "colesterol_alto": true,
        "tabaquismo": false,
        "actividad_fisica": true,
        "antecedente_acv": false,
        "diabetes": true,
        "salud_general": 3,
        "dificultad_para_caminar": false
    }
    """
    paciente_id: int  # Obligatorio — debe existir en la tabla pacientes

    # --- Variables predictoras (las que entra al modelo ML) ---
    edad: int = Field(..., ge=1, le=120)
    # ge=1 → greater or equal (mayor o igual a 1)
    # le=120 → less or equal (menor o igual a 120)

    presion_alta: bool = False
    colesterol_alto: bool = False
    tabaquismo: bool = False
    actividad_fisica: bool = False
    antecedente_acv: bool = False
    diabetes: bool = False

    salud_general: int = Field(3, ge=1, le=5)
    # 1=excelente, 2=muy buena, 3=buena, 4=regular, 5=mala

    dificultad_para_caminar: bool = False


class EvaluacionResponse(BaseModel):
    """
    DTO de SALIDA — resultado completo de la evaluación.
    Incluye TODOS los datos que se guardaron + la predicción del ML.

    Ejemplo JSON:
    {
        "id": 1,
        "paciente_id": 1,
        "usuario_id": 1,
        "edad": 55,
        "presion_alta": true,
        "colesterol_alto": true,
        "tabaquismo": false,
        "actividad_fisica": true,
        "antecedente_acv": false,
        "diabetes": true,
        "salud_general": 3,
        "dificultad_para_caminar": false,
        "probabilidad": 0.734521,
        "clasificacion": "alto",
        "modelo_version": "1.0.0",
        "created_at": "2025-01-15T10:30:00"
    }
    """
    id: int
    paciente_id: int
    usuario_id: int

    # Variables predictoras que se evaluaron
    edad: int
    presion_alta: bool
    colesterol_alto: bool
    tabaquismo: bool
    actividad_fisica: bool
    antecedente_acv: bool
    diabetes: bool
    salud_general: int
    dificultad_para_caminar: bool

    # Resultado del modelo ML
    probabilidad: float  # 0.0 a 1.0
    clasificacion: ClasificacionEnum
    modelo_version: Optional[str] = None

    created_at: datetime

    class Config:
        from_attributes = True


class PredictionResult(BaseModel):
    """
    DTO INTERNO — resultado puro del modelo ML.
    NO se retorna al frontend directamente. Se usa internamente
    en el mapper para construir EvaluacionResponse.

    Flujo: preprocessor.py → model_loader.py → predictor.py → PredictionResult
                                ↓
              EvaluacionMapper.create_to_model() → dict → Evaluacion ORM
    """
    probabilidad: float  # 0.0 a 1.0 (6 decimales)
    clasificacion: ClasificacionEnum  # "bajo", "moderado" o "alto"
    modelo_version: str  # Ej: "1.0.0"
