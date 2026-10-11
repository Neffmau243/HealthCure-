"""
atencion.py — MODELO: TABLA DE ATENCIONES (CONSULTORIO)

Registra el resultado del acto médico: lo que el doctor concluyó y prescribió
después de revisar al paciente y su evaluación cardíaca.

Diferencia con `Evaluacion`:
  - Evaluacion = instantánea CLÍNICA + resultado del modelo ML (automático)
  - Atencion   = acto MÉDICO escrito por el profesional (diagnóstico,
                 tratamiento e indicaciones)

Una atención SIEMPRE pertenece a un paciente y puede referenciar la
evaluación que la originó (evaluacion_id), pero no es obligatorio.

Relaciones: se declaran en UNA sola dirección (desde Atencion hacia el
resto) para no tener que modificar los modelos Usuario/Paciente/Evaluacion.
"""
from sqlalchemy import (
    Column, BigInteger, String, Text, DateTime, ForeignKey, Index, func
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Atencion(Base):
    """
    Representa la tabla 'atenciones' en MySQL.
    Un paciente puede tener MUCHAS atenciones a lo largo del tiempo.
    """
    __tablename__ = "atenciones"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # --- Relaciones (FK) ---
    paciente_id = Column(BigInteger, ForeignKey("pacientes.id"), nullable=False)
    # De quién es esta atención. No se puede borrar un paciente con atenciones.

    evaluacion_id = Column(BigInteger, ForeignKey("evaluaciones.id"), nullable=True)
    # Evaluación cardíaca que originó esta atención (opcional).
    # ON DELETE SET NULL: si se borrara la evaluación, la atención sobrevive.

    usuario_id = Column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    # Profesional que atendió (trazabilidad/auditoría)

    # --- Contenido clínico del acto médico ---
    diagnostico = Column(Text, nullable=False)
    # Conclusión del médico (ej: "HTA no controlada + dislipidemia mixta")

    tratamiento = Column(Text, nullable=False)
    # Tratamiento / receta (medicamentos, dosis, frecuencia)

    indicaciones = Column(Text, nullable=True)
    # Indicaciones generales (dieta, exámenes auxiliares, cita de control)

    # --- Timestamps ---
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # --- Relaciones (una sola dirección) ---
    paciente = relationship("Paciente")
    evaluacion = relationship("Evaluacion")
    usuario = relationship("Usuario")

    # --- Índices para queries frecuentes ---
    __table_args__ = (
        Index("ix_atenciones_paciente_id", "paciente_id"),
        Index("ix_atenciones_created_at", "created_at"),
    )

    @property
    def paciente_nombre(self) -> str | None:
        """Nombre del paciente resuelto para mostrar en listados."""
        return self.paciente.nombre_completo if self.paciente else None
