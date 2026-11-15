"""
atencion_repository.py — REPOSITORY: OPERACIONES DE BD PARA ATENCIONES

Única capa que hace queries a MySQL sobre la tabla `atenciones`.
Incluye joinedload del paciente para resolver el nombre en la respuesta
sin generar consultas N+1.
"""
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from app.models.atencion import Atencion


class AtencionRepository:
    """Repository de atenciones del consultorio."""

    def __init__(self, db: Session):
        self.db = db

    def _query_con_paciente(self):
        """
        Query base con joinedload del paciente y su catálogo de ubicación.
        Así el nombre del paciente se resuelve sin queries extra.
        """
        return self.db.query(Atencion).options(joinedload(Atencion.paciente))

    def get_by_id(self, atencion_id: int) -> Optional[Atencion]:
        """Busca una atención por su ID."""
        return (
            self._query_con_paciente()
            .filter(Atencion.id == atencion_id)
            .first()
        )

    def create(self, **kwargs) -> Atencion:
        """
        Guarda una atención nueva.

        Ejemplo:
            repo.create(
                paciente_id=1,
                evaluacion_id=8,
                usuario_id=2,
                diagnostico="...",
                tratamiento="...",
            )
        """
        atencion = Atencion(**kwargs)
        self.db.add(atencion)
        self.db.flush()
        return atencion

    def get_by_paciente(self, paciente_id: int) -> list[Atencion]:
        """Retorna las atenciones de un paciente, la más reciente primero."""
        return (
            self._query_con_paciente()
            .filter(Atencion.paciente_id == paciente_id)
            .order_by(Atencion.created_at.desc())
            .all()
        )

    def get_by_evaluacion(self, evaluacion_id: int) -> list[Atencion]:
        """Retorna las atenciones asociadas a una evaluación."""
        return (
            self._query_con_paciente()
            .filter(Atencion.evaluacion_id == evaluacion_id)
            .order_by(Atencion.created_at.desc())
            .all()
        )

    def list_all(self, limit: int = 50, offset: int = 0) -> list[Atencion]:
        """
        Retorna atenciones paginadas (todas, de todos los pacientes).
        Usado por el historial general de atenciones.
        """
        return (
            self._query_con_paciente()
            .order_by(Atencion.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
