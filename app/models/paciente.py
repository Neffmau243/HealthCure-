"""
paciente.py — MODELO: TABLA DE PACIENTES

Almacena los datos ADMINISTRATIVOS de cada paciente:
  nombre, documento de identidad, fecha de nacimiento, sexo, talla, peso

IMPORTANTE: Este modelo NO tiene nada que ver con el modelo de ML.
Las variables predictoras (presión alta, colesterol, etc.) van en
la tabla Evaluacion, porque CADA evaluación es una instantánea
clínica diferente del mismo paciente.
"""
from sqlalchemy import (
    Column, BigInteger, String, Enum, Date, Numeric, DateTime, func
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Paciente(Base):
    """
    Representa la tabla 'pacientes' en MySQL.
    Un paciente puede tener MÚLTIPLES evaluaciones cardíacas a lo largo del tiempo.
    """
    __tablename__ = "pacientes"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # --- Datos demográficos ---
    nombre              = Column(String(150), nullable=False)
    documento_identidad = Column(String(30), nullable=False, unique=True, index=True)
    # Cada paciente se identifica por su documento (cédula, DNI, etc.)
    # unique + index = no se puede duplicar y las búsquedas son rápidas

    fecha_nacimiento    = Column(Date, nullable=False)
    # Se usa para calcular la edad cuando se hace la evaluación

    sexo = Column(Enum("M", "F", name="sexo_enum"), nullable=False)
    # M = Masculino, F = Femenino

    # --- Mediciones físicas (opcionales, se pueden llenar después) ---
    talla_cm = Column(Numeric(5, 1), nullable=True)
    # Numeric(5,1) = hasta 999.9 cm (ej: 175.5 cm)

    peso_kg  = Column(Numeric(5, 1), nullable=True)
    # Numeric(5,1) = hasta 999.9 kg (ej: 72.3 kg)

    # --- Timestamps ---
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # --- Relaciones ---
    evaluaciones = relationship("Evaluacion", back_populates="paciente")
    # Un paciente puede tener MUCHAS evaluaciones cardíacas
