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
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Optional
from datetime import datetime
from enum import Enum


class ClasificacionEnum(str, Enum):
    """
    Bandas experimentales del score no calibrado.
    Los cortes vigentes se leen de la metadata del modelo:
      - bajo:     score < 0.30
      - moderado: 0.30 <= score < 0.60
      - alto:     score >= 0.60
    No representan probabilidades clínicas ni criterios de urgencia.
    """
    bajo = "bajo"
    moderado = "moderado"
    alto = "alto"


class EstadoDiabetes(str, Enum):
    ninguna = "ninguna"
    prediabetes = "prediabetes"
    diabetes = "diabetes"


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
    paciente_id: int = Field(..., gt=0)

    # --- Variables predictoras (las que entra al modelo ML) ---
    edad: int = Field(..., ge=18, le=120)
    # ge=18: población adulta del modelo
    # le=120 → less or equal (menor o igual a 120)

    presion_alta: bool
    colesterol_alto: bool
    tabaquismo: bool
    actividad_fisica: bool
    antecedente_acv: bool
    diabetes: bool

    salud_general: int = Field(..., ge=1, le=5)
    # 1=excelente, 2=muy buena, 3=buena, 4=regular, 5=mala

    dificultad_para_caminar: bool

    # Datos originales de consulta: se conservan, pero no añaden features al ML.
    # None conserva compatibilidad con clientes que solo conocen el booleano.
    estado_diabetes: Optional[EstadoDiabetes] = None
    presion_sistolica: Optional[int] = Field(None, gt=0, le=400)
    presion_diastolica: Optional[int] = Field(None, gt=0, le=400)

    @model_validator(mode="after")
    def validar_datos_originales(self):
        if self.estado_diabetes is not None:
            if self.diabetes != (self.estado_diabetes != EstadoDiabetes.ninguna):
                raise ValueError("diabetes debe coincidir con estado_diabetes")
        if (self.presion_sistolica is None) != (self.presion_diastolica is None):
            raise ValueError("Envía ambas mediciones de presión o ninguna")
        if self.presion_sistolica is not None and self.presion_sistolica <= self.presion_diastolica:
            raise ValueError("La presión sistólica debe ser mayor que la diastólica")
        return self


class TriajeClinico(BaseModel):
    """
    Orientación experimental asociada al resultado ML.

    TODO es texto plano / listas de strings — SIN HTML ni estilos.
    El frontend renderiza colores y tarjetas a partir de codigo_color
    ("verde" / "amarillo" / "rojo").

    Ejemplo JSON:
    {
        "nivel_alerta": "RIESGO MODERADO - SEGUIMIENTO PREVENTIVO",
        "codigo_color": "amarillo",
        "accion_sugerida": "Revisar los antecedentes durante la consulta; prioridad experimental moderada.",
        "factores_riesgo_detectados": ["Hipertensión Arterial", ...],
        "factores_protectores": ["Actividad física declarada en los últimos 30 días"],
        "recomendaciones_medicas": ["Regla académica sin validación clínica; no determina urgencia ni diagnóstico."]
    }
    """
    nivel_alerta: str
    codigo_color: str  # "verde" | "amarillo" | "rojo" (semáforo)
    accion_sugerida: str
    factores_riesgo_detectados: list[str]
    factores_protectores: list[str]
    recomendaciones_medicas: list[str]


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
        "triaje_clinico": {
            "nivel_alerta": "ALTA PRIORIDAD - RIESGO ELEVADO",
            "codigo_color": "rojo",
            "accion_sugerida": "Revisar el perfil con el profesional responsable; prioridad experimental alta.",
            "factores_riesgo_detectados": ["Hipertensión Arterial", "Dislipidemia (Colesterol Alto)"],
            "factores_protectores": ["No declara haber fumado 100 cigarrillos en la vida"],
            "recomendaciones_medicas": ["Regla académica sin validación clínica; no determina urgencia ni diagnóstico."]
        },
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
    estado_diabetes: Optional[EstadoDiabetes] = None
    presion_sistolica: Optional[int] = None
    presion_diastolica: Optional[int] = None

    # Resultado del modelo ML
    probabilidad: float = Field(..., ge=0, le=1, description="Score [0,1]; su calibración y bandas dependen de politica_modelo y versión. No es probabilidad clínica.")
    clasificacion: ClasificacionEnum
    modelo_version: Optional[str] = None
    politica_modelo: Optional[dict] = None

    # Orientación experimental; se conserva el nombre del contrato histórico.
    triaje_clinico: Optional[TriajeClinico] = None
    # None si la evaluación es antigua y no tiene triaje persistido

    created_at: datetime

    # Pydantic v2: ConfigDict reemplaza al `class Config` deprecado.
    model_config = ConfigDict(from_attributes=True)


class ResumenEvaluaciones(BaseModel):
    """
    DTO de SALIDA — agregados para el dashboard (SOLO LECTURA).

    Existe para que los KPIs y la cola de triaje no se calculen contando
    una página de resultados en el navegador: si el front pide `limit=200`
    y hay 201 evaluaciones, el número mostrado sería falso sin avisar.

    Aquí los conteos se hacen con COUNT en SQL, así que son exactos y no
    traen filas al cliente.

    Ejemplo JSON:
    {
        "total_evaluaciones": 39,
        "total_hoy": 5,
        "por_clasificacion": {"bajo": 17, "moderado": 10, "alto": 12},
        "pacientes_evaluados_hoy": [1, 4, 7]
    }
    """
    total_evaluaciones: int
    total_hoy: int
    # Claves siempre presentes (con 0 si no hay casos de ese nivel)
    por_clasificacion: dict[str, int]
    # IDs de pacientes ya triados HOY: define la cola de "pendientes"
    pacientes_evaluados_hoy: list[int]


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
    politica_modelo: Optional[dict] = None
