"""
evaluacion_mapper.py — MAPPER: TRADUCTOR ENTRE CAPAS

El mapper es el "traidor" que habla con todos pero no pertenece a nadie.
Su trabajo es traducir datos entre las diferentes capas sin que una
sepa que existe la otra:

  ┌─────────────────┐
  │  Request DTO     │  ← Lo que envía el frontend
  │  (EvaluacionCreate)
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  ML Input Dict   │  ← Lo que el modelo ML espera
  │  (dict de ints)  │
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  PredictionResult│  ← Lo que devuelve el modelo ML
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  ORM Dict        │  ← Lo que se guarda en MySQL
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  Response DTO    │  ← Lo que se retorna al frontend
  │  (EvaluacionResponse)
  └─────────────────┘

POR QUÉ NO USAMOS model_validate() DIRECTAMENTE?
Porque el request del frontend tiene campos que NO van al modelo ML
(paciente_id) y el resultado del ML tiene campos que NO existen en
el request original (probabilidad, clasificacion). El mapper
orquesta esta transformación de forma explícita y testeable.
"""
from typing import Optional
from app.schemas.evaluacion import (
    EvaluacionCreate, EvaluacionResponse, PredictionResult, TriajeClinico
)
from app.models.evaluacion import Evaluacion
from app.services.evaluacion_triaje_service import generar_triaje_clinico


class EvaluacionMapper:
    """
    Clase Stateless — solo tiene métodos estáticos, no tiene estado.
    No se instancia: se usa como EvaluacionMapper.method()
    """

    # ---------------------------------------------------------------
    # REQUEST → ML INPUT VECTOR
    # ---------------------------------------------------------------
    @staticmethod
    def request_to_model_input(data: EvaluacionCreate) -> dict:
        """
        Extrae SOLO las variables predictoras del request y las
        convierte al formato que el modelo ML espera.

        Transformaciones importantes:
          - Los booleans se convierten a int (0/1) porque los
            modelos de scikit-learn/XGBoost esperan números
          - Se ELIMINA paciente_id (el modelo no sabe de pacientes)
          - Se ELIMINA cualquier otro campo administrativo

        Ejemplo:
          Input:  EvaluacionCreate(paciente_id=1, edad=55, presion_alta=True, ...)
          Output: {"edad": 55, "presion_alta": 1, ...}  ← dict plano de ints
        """
        return {
            "edad":                    data.edad,
            "presion_alta":            int(data.presion_alta),  # True → 1
            "colesterol_alto":         int(data.colesterol_alto),
            "tabaquismo":              int(data.tabaquismo),
            "actividad_fisica":        int(data.actividad_fisica),
            "antecedente_acv":         int(data.antecedente_acv),
            "diabetes":                int(data.diabetes),
            "salud_general":           data.salud_general,  # Ya es int (1-5)
            "dificultad_para_caminar": int(data.dificultad_para_caminar),
        }

    # ---------------------------------------------------------------
    # ORM MODEL → RESPONSE DTO
    # ---------------------------------------------------------------
    @staticmethod
    def to_response(evaluacion: Evaluacion) -> EvaluacionResponse:
        """
        Convierte un objeto SQLAlchemy (Evaluacion ORM) a un
        DTO de respuesta (EvaluacionResponse) para enviar al frontend.

        Transformaciones:
          - Numeric(7,6) de MySQL → float de Python
          - Enum de SQLAlchemy → ClasificacionEnum de Pydantic
          - Columnas de triaje → TriajeClinico (o se recalcula si falta)

        Por qué no usamos model_validate()?
        Porque la respuesta tiene campos calculados (probabilidad como float)
        y necesitamos mapeo explícito para controlar la conversión.
        """
        return EvaluacionResponse(
            id=evaluacion.id,
            paciente_id=evaluacion.paciente_id,
            usuario_id=evaluacion.usuario_id,
            # Variables predictoras (tal cual se guardaron)
            edad=evaluacion.edad,
            presion_alta=evaluacion.presion_alta,
            colesterol_alto=evaluacion.colesterol_alto,
            tabaquismo=evaluacion.tabaquismo,
            actividad_fisica=evaluacion.actividad_fisica,
            antecedente_acv=evaluacion.antecedente_acv,
            diabetes=evaluacion.diabetes,
            salud_general=evaluacion.salud_general,
            dificultad_para_caminar=evaluacion.dificultad_para_caminar,
            # Resultado del ML
            probabilidad=float(evaluacion.probabilidad),  # Decimal → float
            clasificacion=evaluacion.clasificacion,
            modelo_version=evaluacion.modelo_version,
            triaje_clinico=EvaluacionMapper._triaje_clinico(evaluacion),
            created_at=evaluacion.created_at,
        )

    @staticmethod
    def _triaje_clinico(evaluacion: Evaluacion) -> Optional[TriajeClinico]:
        """
        Construye el objeto TriajeClinico de una evaluación.

        - Si la evaluación tiene el triaje PERSISTIDO (columnas llenas),
          se usa tal cual (fuente de verdad guardada en BD).
        - Si es una evaluación ANTIGUA sin triaje guardado (columnas NULL),
          se RECALCULA con las mismas reglas deterministas del servicio.
          Así las evaluaciones históricas también devuelven interpretación.
        """
        if evaluacion.nivel_alerta is not None:
            return TriajeClinico(
                nivel_alerta=evaluacion.nivel_alerta,
                codigo_color=evaluacion.codigo_color,
                accion_sugerida=evaluacion.accion_sugerida,
                factores_riesgo_detectados=evaluacion.factores_riesgo_detectados or [],
                factores_protectores=evaluacion.factores_protectores or [],
                recomendaciones_medicas=evaluacion.recomendaciones_medicas or [],
            )

        # Fallback: evaluación legacy → recalcular triaje on-the-fly
        triaje = generar_triaje_clinico(
            data={
                "presion_alta": evaluacion.presion_alta,
                "colesterol_alto": evaluacion.colesterol_alto,
                "tabaquismo": evaluacion.tabaquismo,
                "actividad_fisica": evaluacion.actividad_fisica,
                "antecedente_acv": evaluacion.antecedente_acv,
                "diabetes": evaluacion.diabetes,
                "salud_general": evaluacion.salud_general,
                "dificultad_para_caminar": evaluacion.dificultad_para_caminar,
            },
            probabilidad=float(evaluacion.probabilidad),
            clasificacion=evaluacion.clasificacion,
        )
        return TriajeClinico(**triaje)

    # ---------------------------------------------------------------
    # REQUEST + PREDICTION → ORM DICT (para guardar en BD)
    # ---------------------------------------------------------------
    @staticmethod
    def create_to_model(
        data: EvaluacionCreate,
        prediction: PredictionResult,
        usuario_id: int,
    ) -> dict:
        """
        Combina el request original + la predicción del ML en un
        dict listo para crear un objeto Evaluacion ORM.

        Este es el punto donde SE UNEN:
          - Datos del request (paciente_id, edad, presion_alta, etc.)
          - Resultado del ML (probabilidad, clasificacion)
          - Info del contexto (usuario_id quién hizo la evaluación)

        El repository recibe este dict y crea el registro en MySQL.

        El triaje clínico se genera AQUÍ (no en el predictor ML):
        las reglas clínicas son lógica del negocio, no del modelo.
        Se guarda persistido para auditoría y renderizado inmediato.
        """
        triaje = generar_triaje_clinico(
            data={
                "presion_alta":            data.presion_alta,
                "colesterol_alto":         data.colesterol_alto,
                "tabaquismo":              data.tabaquismo,
                "actividad_fisica":        data.actividad_fisica,
                "antecedente_acv":         data.antecedente_acv,
                "diabetes":                data.diabetes,
                "salud_general":           data.salud_general,
                "dificultad_para_caminar": data.dificultad_para_caminar,
            },
            probabilidad=prediction.probabilidad,
            clasificacion=prediction.clasificacion,
        )

        return {
            # --- Quién y de quién ---
            "paciente_id":             data.paciente_id,
            "usuario_id":              usuario_id,

            # --- Variables predictoras (se guardan para auditoría) ---
            "edad":                    data.edad,
            "presion_alta":            data.presion_alta,   # Bool → MySQL BOOLEAN
            "colesterol_alto":         data.colesterol_alto,
            "tabaquismo":              data.tabaquismo,
            "actividad_fisica":        data.actividad_fisica,
            "antecedente_acv":         data.antecedente_acv,
            "diabetes":                data.diabetes,
            "salud_general":           data.salud_general,
            "dificultad_para_caminar": data.dificultad_para_caminar,

            # --- Resultado del modelo ML ---
            "probabilidad":            prediction.probabilidad,
            "clasificacion":           prediction.clasificacion,
            "modelo_version":          prediction.modelo_version,

            # --- Triaje clínico (reglas de negocio) ---
            "nivel_alerta":            triaje["nivel_alerta"],
            "codigo_color":            triaje["codigo_color"],
            "accion_sugerida":         triaje["accion_sugerida"],
            "factores_riesgo_detectados": triaje["factores_riesgo_detectados"],
            "factores_protectores":    triaje["factores_protectores"],
            "recomendaciones_medicas": triaje["recomendaciones_medicas"],
        }
