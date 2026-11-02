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
from app.core.clinica import calcular_edad, calcular_edad_meses, grupo_por_edad, CondicionMaterna
from datetime import date
from app.schemas.clinica import ObservacionesClinicas
from app.services.alerta_clinica_service import evaluar_alertas


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

        edad = calcular_edad(paciente.fecha_nacimiento)
        if data.condicion_materna != CondicionMaterna.ninguna and paciente.sexo != "F":
            raise ValueError("Gestante o puérpera requiere un paciente registrado con sexo femenino")

        evaluacion = None
        if data.evaluacion_id is not None:
            evaluacion = self.evaluacion_repo.get_by_id(data.evaluacion_id)
            if not evaluacion:
                raise ValueError("Evaluación no encontrada")
            if evaluacion.paciente_id != data.paciente_id:
                raise ValueError(
                    "La evaluación no corresponde al paciente indicado"
                )
            if edad < 18:
                raise ValueError("Los menores se atienden sin vincular el modelo de riesgo para adultos")

        observaciones = data.observaciones_clinicas
        if data.usar_observaciones_evaluacion:
            if observaciones is not None:
                raise ValueError("Elige mediciones nuevas o las de la evaluación, no ambas")
            if evaluacion is None or not evaluacion.observaciones_clinicas:
                raise ValueError("La evaluación asociada no tiene mediciones para reutilizar")
            if evaluacion.created_at.date() != date.today():
                raise ValueError("Las mediciones de otra fecha no son observaciones actuales; registra mediciones nuevas")
            observaciones = ObservacionesClinicas.model_validate(evaluacion.observaciones_clinicas).model_copy(update={"condicion_materna": data.condicion_materna})
        elif observaciones and observaciones.condicion_materna is not None and observaciones.condicion_materna != data.condicion_materna:
            raise ValueError("La condición materna de las mediciones no coincide con la atención")
        alerta = evaluar_alertas(observaciones, edad, data.condicion_materna, sexo=paciente.sexo, edad_meses=calcular_edad_meses(paciente.fecha_nacimiento))
        if data.usar_observaciones_evaluacion:
            alerta["origen_evaluacion_id"] = evaluacion.id

        atencion = self.atencion_repo.create(
            paciente_id=data.paciente_id,
            evaluacion_id=data.evaluacion_id,
            usuario_id=usuario_id,
            diagnostico=data.diagnostico,
            tratamiento=data.tratamiento,
            indicaciones=data.indicaciones,
            tipo_atencion=data.tipo_atencion.value,
            condicion_materna=data.condicion_materna.value,
            grupo_etario=grupo_por_edad(edad).value,
            edad_al_atender=edad,
            observaciones_clinicas=observaciones.model_dump(mode="json") if observaciones else None,
            alerta_clinica=alerta,
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
