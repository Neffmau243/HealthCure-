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
from datetime import date
from sqlalchemy.orm import Session
from typing import Optional
from app.repositories.evaluacion_repository import EvaluacionRepository
from app.repositories.paciente_repository import PacienteRepository
from app.schemas.evaluacion import (
    ClasificacionEnum,
    EvaluacionCreate,
    EvaluacionResponse,
    ResumenEvaluaciones,
)
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
        # EXPO-ML 06 | Orquestar la evaluación y comprobar que el paciente exista.
        # Este servicio conecta las capas; los cálculos del modelo van en predictor.
        # La edad se toma del request: aquí no se recalcula desde el nacimiento.
        paciente = self.paciente_repo.get_by_id(data.paciente_id)
        if not paciente:
            raise ValueError("Paciente no encontrado")

        # Continuar en EvaluacionMapper.request_to_model_input, EXPO-ML 07.
        model_input = EvaluacionMapper.request_to_model_input(data)

        # El predictor recorre EXPO-ML 08 a 11: cargar, preparar, inferir y clasificar.
        # Import LAZY: solo se importa cuando se ejecuta evaluate().
        # Por qué: si el modelo .joblib no existe, el server sigue
        # funcionando para auth, pacientes, etc. Solo falla al predecir.
        #
        # Solo capturamos ImportError (módulo faltante) y MLException
        # (errores del pipeline: modelo no encontrado, datos inválidos).
        # NUNCA Exception genérico — eso escondería bugs reales de
        # programación (typos, errores de lógica) como "modelo caído".
        try:
            from app.ml.predictor import predict as ml_predict
            prediction = ml_predict(model_input)
        except (ImportError, MLException) as e:
            raise MLException(f"Modelo ML no disponible: {e}")

        # EXPO-ML 12 comienza en create_to_model: añadir las reglas de triaje.
        evaluacion_data = EvaluacionMapper.create_to_model(
            data=data,
            prediction=prediction,
            usuario_id=usuario_id,
        )

        # Continuar en EvaluacionRepository.create, EXPO-ML 13 (persistencia).
        evaluacion = self.evaluacion_repo.create(**evaluacion_data)
        # Luego to_response arma la salida de la API: EXPO-ML 14.
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

    def resumen(self) -> ResumenEvaluaciones:
        """
        Agregados para el dashboard y la cola de triaje.

        Por qué existe: el frontend calculaba "Evaluaciones realizadas" y
        "Riesgo alto" contando una página de como máximo 200 evaluaciones,
        así que a partir de la 201 el número mostrado era falso sin avisar.
        Aquí los conteos son COUNT en SQL: exactos y sin traer filas.

        `pacientes_evaluados_hoy` define qué pacientes NO están pendientes:
        la cola es diaria (un paciente triado la semana pasada vuelve a
        estar pendiente hoy).
        """
        hoy = date.today().isoformat()
        conteo = self.evaluacion_repo.contar_por_clasificacion()
        return ResumenEvaluaciones(
            total_evaluaciones=self.evaluacion_repo.contar(),
            total_hoy=self.evaluacion_repo.contar_hoy(hoy),
            # Se completan los 3 niveles con 0 para que el frontend no tenga
            # que defenderse de claves ausentes.
            por_clasificacion={
                nivel.value: conteo.get(nivel.value, 0) for nivel in ClasificacionEnum
            },
            pacientes_evaluados_hoy=self.evaluacion_repo.pacientes_evaluados_hoy(hoy),
        )
