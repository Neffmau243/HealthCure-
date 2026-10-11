"""
evaluacion_repository.py — REPOSITORY: OPERACIONES DE BD PARA EVALUACIONES

Maneja la persistencia de las evaluaciones cardíacas (predicciones ML).
Cada evaluación se guarda con TODOS los datos para auditoría futura.
"""
from sqlalchemy import func
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

    # ── AGREGADOS (para el resumen del dashboard y la cola de triaje) ──────
    # Se resuelven con COUNT en SQL: no traen filas al cliente y son exactos
    # a diferencia de contar una página en el navegador.

    def contar(self) -> int:
        """Total de evaluaciones registradas (sin paginar)."""
        return int(self.db.query(func.count(Evaluacion.id)).scalar() or 0)

    def contar_por_clasificacion(self) -> dict[str, int]:
        """
        Cuántas evaluaciones hay de cada nivel de riesgo.
        Agrupa por la columna `clasificacion` (enum bajo/moderado/alto).
        """
        filas = (
            self.db.query(Evaluacion.clasificacion, func.count(Evaluacion.id))
            .group_by(Evaluacion.clasificacion)
            .all()
        )
        return {
            (nivel.value if hasattr(nivel, "value") else str(nivel)): int(total)
            for nivel, total in filas
        }

    def contar_hoy(self, hoy: str) -> int:
        """Evaluaciones creadas HOY. `hoy` en formato 'YYYY-MM-DD'."""
        return int(
            self.db.query(func.count(Evaluacion.id))
            .filter(func.date(Evaluacion.created_at) == hoy)
            .scalar()
            or 0
        )

    def pacientes_evaluados_hoy(self, hoy: str) -> list[int]:
        """
        IDs (únicos) de los pacientes que YA tienen una evaluación de HOY.
        Es lo que define la cola de 'pendientes de triaje': un paciente con
        una evaluación de la semana pasada vuelve a estar pendiente hoy.
        """
        filas = (
            self.db.query(Evaluacion.paciente_id)
            .filter(func.date(Evaluacion.created_at) == hoy)
            .distinct()
            .all()
        )
        return [int(pid) for (pid,) in filas]

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
