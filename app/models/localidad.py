"""
localidad.py — MODELO: TABLA DE LOCALIDADES (CATÁLOGO ADMIN)

Una localidad es un sector/barrio/centro poblado DENTRO de un distrito.
También es un catálogo administrado por el admin.

Ejemplo de jerarquía:
  Distrito "Alto Selva Alegre" → Localidades: "Chilpinilla", "El Mirador"

La localidad depende del distrito (FK), así que al elegir un distrito
en el formulario, el frontend filtra las localidades de ese distrito.
"""
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Localidad(Base):
    """
    Representa la tabla 'localidades' en MySQL.
    Pertenece SIEMPRE a un distrito (no puede existir sola).
    """
    __tablename__ = "localidades"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    nombre = Column(String(100), nullable=False)
    # Nombre de la localidad (ej: "Chilpinilla")

    distrito_id = Column(BigInteger, ForeignKey("distritos.id"), nullable=False)
    # FK → distritos.id. Una localidad sin distrito no tiene sentido.
    # ON DELETE RESTRICT: no se puede borrar un distrito con localidades.

    activo = Column(Boolean, nullable=False, default=True)
    # False = localidad desactivada (no aparece en las listas)

    # --- Timestamps ---
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # --- Relaciones ---
    distrito = relationship("Distrito", back_populates="localidades")
    # Permite acceder a la localidad.distrito.nombre

    __table_args__ = (
        Index("ix_localidades_distrito_id", "distrito_id"),
        # Búsquedas frecuentes: "dame las localidades del distrito X"
        # Sin índice sería FULL TABLE SCAN

        Index("ix_localidades_nombre", "nombre"),
    )