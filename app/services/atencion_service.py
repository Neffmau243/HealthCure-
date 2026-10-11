"""
atencion_service.py — SERVICE: ORQUESTA LAS ATENCIONES DEL CONSULTORIO

Valida las reglas de negocio antes de persistir:
  - El paciente debe existir.
  - Si se envía evaluacion_id, la evaluación debe existir y pertenecer
    al MISMO paciente (evita registrar una atención contra la evaluación
    de otra persona).
"""
from sqlalchemy.orm import Session
from typing import Optional
from app.repositories.atencion_repository import AtencionRepository
from app.repositories.paciente_repository import PacienteRepository
from app.repositories.evaluacion_repository import EvaluacionRepository
from app.schemas.atencion import AtencionCreate, AtencionResponse


class AtencionService:
    """Service de atenciones. Orquesta los repositories + las reglas de negocio."""

    def __init__(self, db: Session):
        self.atencion_repo = AtencionRepository(db)
        self.paciente_repo = PacienteRepository(db)
        self.evaluacion_repo = EvaluacionRepository(db)

    def create(self, data: AtencionCreate, usuario_id: int) -> AtencionResponse:
        """
        Registra una atención nueva.

        Lanza ValueError (→ HTTP 400 en el controller) si:
          - El paciente no existe.
          - La evaluación no existe.
          - La evaluación no corresponde al paciente indicado.
        """
        paciente = self.paciente_repo.get_by_id(data.paciente_id)
        if not paciente:
            raise ValueError("Paciente no encontrado")

        if data.evaluacion_id is not None:
            evaluacion = self.evaluacion_repo.get_by_id(data.evaluacion_id)
            if not evaluacion:
                raise ValueError("Evaluación no encontrada")
            if evaluacion.paciente_id != data.paciente_id:
                raise ValueError(
                    "La evaluación no corresponde al paciente indicado"
                )

        atencion = self.atencion_repo.create(
            paciente_id=data.paciente_id,
            evaluacion_id=data.evaluacion_id,
            usuario_id=usuario_id,
            diagnostico=data.diagnostico,
            tratamiento=data.tratamiento,
            indicaciones=data.indicaciones,
        )
        return AtencionResponse.model_validate(atencion)

    def get_by_id(self, atencion_id: int) -> Optional[AtencionResponse]:
        """Busca una atención por ID. None si no existe."""
        atencion = self.atencion_repo.get_by_id(atencion_id)
        if not atencion:
            return None
        return AtencionResponse.model_validate(atencion)

    def get_by_paciente(self, paciente_id: int) -> list[AtencionResponse]:
        """Historial de atenciones de un paciente."""
        atenciones = self.atencion_repo.get_by_paciente(paciente_id)
        return [AtencionResponse.model_validate(a) for a in atenciones]

    def list_all(self, limit: int = 50, offset: int = 0) -> list[AtencionResponse]:
        """Atenciones paginadas (historial general)."""
        atenciones = self.atencion_repo.list_all(limit=limit, offset=offset)
        return [AtencionResponse.model_validate(a) for a in atenciones]
