"""
evaluacion_repository.py — REPOSITORY: OPERACIONES DE BD PARA EVALUACIONES

Maneja la persistencia de las evaluaciones cardíacas (predicciones ML).
Cada evaluación se guarda con TODOS los datos para auditoría futura.
"""
from sqlalchemy.orm import Session
from typing import Optional
from app.models.evaluacion import Evaluacion


class EvaluacionRepository:
    """
    Repository de evaluaciones cardíacas.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, evaluacion_id: int) -> Optional[Evaluacion]:
        """Busca una evaluación por su ID."""
        return (
            self.db.query(Evaluacion)
            .filter(Evaluacion.id == evaluacion_id)
            .first()
        )

    def create(self, **kwargs) -> Evaluacion:
        """
        Guarda una nueva evaluación en la BD.
        Incluye: datos del paciente + variables predictoras + resultado ML.

        Flujo típico:
          1. Service llama a ml_predict() → obtiene predicción
          2. Mapper convierte request + predicción → dict
          3. Repository recibe el dict y lo guarda aquí
        """
        evaluacion = Evaluacion(**kwargs)
        self.db.add(evaluacion)
        self.db.flush()
        return evaluacion

    def get_by_paciente(self, paciente_id: int) -> list[Evaluacion]:
        """
        Retorna TODAS las evaluaciones de un paciente específico,
        ordenadas de más reciente a más antigua.

        Usa el índice ix_evaluaciones_paciente_id para performance.
        """
        return (
            self.db.query(Evaluacion)
            .filter(Evaluacion.paciente_id == paciente_id)
            .order_by(Evaluacion.created_at.desc())  # Más recientes primero
            .all()
        )

    def list_all(self, limit: int = 50, offset: int = 0) -> list[Evaluacion]:
        """
        Retorna evaluaciones paginadas (todas, de todos los pacientes).
        Usado por el admin para ver el historial general.

        Paginación:
          - offset=0, limit=50 → primeras 50 evaluaciones
          - offset=50, limit=50 → siguientes 50 evaluaciones
        """
        return (
            self.db.query(Evaluacion)
            .order_by(Evaluacion.created_at.desc())
            .offset(offset)  # Saltar las primeras N filas
            .limit(limit)    # Retornar máximo M filas
            .all()
        )
