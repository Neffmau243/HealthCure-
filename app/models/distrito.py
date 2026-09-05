"""
distrito.py — MODELO: TABLA DE DISTRITOS (CATÁLOGO ADMIN)

Los distritos son un catálogo que gestiona SOLO el administrador.
El doctor/médico NO crea distritos: los ELIGE de una lista desplegable
cuando registra un paciente.

Motivo:
  - Evita datos inconsistentes ("Alto Selva Alegre", "alto selva", "AltoSelva"...)
  - Centraliza la fuente de verdad de ubicaciones
  - El frontend carga las opciones con GET /api/v1/catalogos/distritos

Estructura jerárquica:
  Distrito (1) ──── (N) Localidad
  Ej: "Alto Selva Alegre" → "Chilpinilla", "El Mirador", "La Tomilla"
"""
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Distrito(Base):
    """
    Representa la tabla 'distritos' en MySQL.
    Ejemplos: Alto Selva Alegre, Cayma, Miraflores, Yanahuara...
    """
    __tablename__ = "distritos"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    nombre = Column(String(100), nullable=False, unique=True, index=True)
    # unique=True → no puede haber dos distritos con el mismo nombre

    activo = Column(Boolean, nullable=False, default=True)
    # False = distrito desactivado (ya no aparece en las listas del doctor)

    # --- Timestamps ---
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # --- Relaciones ---
    localidades = relationship("Localidad", back_populates="distrito")
    # Un distrito puede tener MUCHAS localidades