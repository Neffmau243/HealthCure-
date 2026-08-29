"""
evaluacion_service.py — SERVICE: ORQUESTA LA PREDICCIÓN CARDÍACA

Este es el servicio MÁS IMPORTANTE del proyecto.
Es el ÚNICO que sabe tanto del Repository (BD) como del Predictor (ML).

FLUJO COMPLETO DE UNA EVALUACIÓN:
  ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
  │  API Route   │────→│  Service      │────→│  Mapper          │
  │  (recibe     │     │  (orquesta)   │     │  (traduce datos) │
  │  el request) │     │               │     │                  │
  └─────────────┘     └──────┬───────┘     └────────┬────────┘
                              │                      │
                    ┌─────────┴─────────┐    ┌───────┴────────┐
                    │                   │    │                │
              ┌─────┴─────┐      ┌─────┴────┐         ┌─────┴─────┐
              │ Repository │      │ Predictor │         │  Mapper    │
              │ (guarda en │      │ (ML:      │         │  (crea     │
              │  MySQL)    │      │  predice) │         │   dict)    │
              └───────────┘      └──────────┘         └───────────┘

¿POR QUÉ NO SE HACE TODO EN EL REPOSITORY O EN EL PREDICTOR?
Porque SRP (Single Responsibility Principle):
  - Repository: solo habla con MySQL
  - Predictor: solo ejecuta el modelo ML
  - Service: orquesta ambos sin que se conozcan entre sí
"""
from sqlalchemy.orm import Session
from typing import Optional
from app.repositories.evaluacion_repository import EvaluacionRepository
from app.repositories.paciente_repository import PacienteRepository
from app.schemas.evaluacion import EvaluacionCreate, EvaluacionResponse
from app.mappers.evaluacion_mapper import EvaluacionMapper
from app.exceptions.ml_exceptions import MLException


class EvaluacionService:
    """
    Service de evaluaciones cardíacas.
    Orquesta: Repository (BD) + Mapper (traducción) + Predictor (ML)
    """

    def __init__(self, db: Session):
        self.evaluacion_repo = EvaluacionRepository(db)
        self.paciente_repo = PacienteRepository(db)

    def evaluate(self, data: EvaluacionCreate, usuario_id: int) -> EvaluacionResponse:
        """
        FLUJO COMPLETO DE EVALUACIÓN CARDÍACA:

        1. VALIDAR QUE EL PACIENTE EXISTA
           → El frontend envía paciente_id, verificamos que exista

        2. MAPPER: REQUEST → ML INPUT
           → Extraemos solo las variables predictoras
           → Convertimos booleans a int (0/1) para el modelo

        3. PREDICTOR: INPUT → PROBABILIDAD
           → Ejecutamos el modelo ML
           → Obtenemos probabilidad de enfermedad cardíaca

        4. MAPPER: CREAR DICT PARA BD
           → Combinamos datos del request + resultado del ML
           → Agregamos usuario_id (quién hizo la evaluación)

        5. REPOSITORY: PERSISTIR
           → Guardamos todo en MySQL
           → La evaluación queda registrada para auditoría
        """
        # PASO 1: Validar que el paciente exista
        paciente = self.paciente_repo.get_by_id(data.paciente_id)
        if not paciente:
            raise ValueError("Paciente no encontrado")

        # PASO 2: Mapper traduce request → input del modelo
        model_input = EvaluacionMapper.request_to_model_input(data)

        # PASO 3: Predictor ejecuta el modelo ML
        # Import LAZY: solo se importa cuando se ejecuta evaluate().
        # Por qué: si el modelo .joblib no existe, el server sigue
        # funcionando para auth, pacientes, etc. Solo falla al predecir.
        try:
            from app.ml.predictor import predict as ml_predict
            prediction = ml_predict(model_input)
        except (ImportError, Exception) as e:
            raise MLException(f"Modelo ML no disponible: {e}")

        # PASO 4: Mapper crea dict para persistir en BD
        evaluacion_data = EvaluacionMapper.create_to_model(
            data=data,
            prediction=prediction,
            usuario_id=usuario_id,
        )

        # PASO 5: Repository guarda en MySQL
        evaluacion = self.evaluacion_repo.create(**evaluacion_data)
        return EvaluacionMapper.to_response(evaluacion)

    def get_by_id(self, evaluacion_id: int) -> Optional[EvaluacionResponse]:
        """Busca una evaluación por su ID."""
        evaluacion = self.evaluacion_repo.get_by_id(evaluacion_id)
        if not evaluacion:
            return None
        return EvaluacionMapper.to_response(evaluacion)

    def get_by_paciente(self, paciente_id: int) -> list[EvaluacionResponse]:
        """Retorna el historial de evaluaciones de un paciente."""
        evaluaciones = self.evaluacion_repo.get_by_paciente(paciente_id)
        return [EvaluacionMapper.to_response(e) for e in evaluaciones]

    def list_all(self, limit: int = 50, offset: int = 0) -> list[EvaluacionResponse]:
        """Retorna evaluaciones paginadas (para el admin)."""
        evaluaciones = self.evaluacion_repo.list_all(limit=limit, offset=offset)
        return [EvaluacionMapper.to_response(e) for e in evaluaciones]
