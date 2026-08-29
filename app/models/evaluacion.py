"""
evaluacion.py — MODELO: TABLA DE EVALUACIONES CARDÍACAS

Cada registro en esta tabla es UNA evaluación cardíaca:
  - Quién la hizo (usuario_id)
  - De quién es (paciente_id)
  - Las variables predictoras que se ingresaron
  - El resultado del modelo ML (probabilidad + clasificación)

Diseño clave: Las variables predictoras se guardan AQUÍ y no en
la tabla pacientes, porque un mismo paciente puede tener diferentes
valores de presión, colesterol, etc. en diferentes evaluaciones.
"""
from sqlalchemy import (
    Column, BigInteger, SmallInteger, Boolean, Enum,
    String, Numeric, DateTime, ForeignKey, Index, func
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Evaluacion(Base):
    """
    Representa la tabla 'evaluaciones' en MySQL.
    Es la tabla central del sistema — cada predicción ML se guarda aquí.
    """
    __tablename__ = "evaluaciones"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # --- Relaciones (FK) ---
    paciente_id = Column(BigInteger, ForeignKey("pacientes.id"), nullable=False)
    # ForeignKey → apunta a pacientes.id. No se puede borrar un paciente
    # que tenga evaluaciones (ON DELETE RESTRICT)

    usuario_id = Column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    # Quién registró esta evaluación (para trazabilidad/auditoría)

    # --- Variables predictoras (las que entra al modelo ML) ---
    edad = Column(SmallInteger, nullable=False)
    # SmallInteger = TINYINT en MySQL (1 byte), suficiente para 1-120

    presion_alta            = Column(Boolean, nullable=False, default=False)
    colesterol_alto         = Column(Boolean, nullable=False, default=False)
    tabaquismo              = Column(Boolean, nullable=False, default=False)
    actividad_fisica        = Column(Boolean, nullable=False, default=False)
    antecedente_acv         = Column(Boolean, nullable=False, default=False)
    diabetes                = Column(Boolean, nullable=False, default=False)
    # Estos 6 booleanos son factores de riesgo del CDC/BRFSS dataset

    salud_general = Column(SmallInteger, nullable=False, default=3)
    # SmallInteger = TINYINT (1 byte). Escala 1-5 del questionario CDC:
    # 1=excelente, 2=muy buena, 3=buena, 4=regular, 5=mala

    dificultad_para_caminar = Column(Boolean, nullable=False, default=False)
    # Indicador de mobility issues (factor de riesgo cardiovascular)

    # --- Resultado del modelo ML ---
    probabilidad = Column(Numeric(7, 6), nullable=False)
    # Numeric(7,6) = 0.000000 a 1.000000 (6 decimales)
    # Ej: 0.734521 = 73.4% de probabilidad de enfermedad cardíaca

    clasificacion = Column(
        Enum("bajo", "moderado", "alto", name="clasificacion_enum"),
        nullable=False
    )
    # Se calcula a partir de la probabilidad en el predictor:
    #   < 0.30 → "bajo"
    #   0.30-0.60 → "moderado"
    #   > 0.60 → "alto"

    modelo_version = Column(String(50), nullable=True)
    # Versión del modelo que se usó (ej: "1.0.0")
    # Útil para auditoría: saber con qué versión se hizo cada predicción

    # --- Timestamp ---
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # --- Relaciones ---
    paciente = relationship("Paciente", back_populates="evaluaciones")
    usuario  = relationship("Usuario", back_populates="evaluaciones")

    # --- Índices para queries frecuentes ---
    __table_args__ = (
        Index("ix_evaluaciones_paciente_id", "paciente_id"),
        # Sin este índice, buscar evaluaciones por paciente sería una
        # búsqueda FULL TABLE SCAN → terrible con miles de registros

        Index("ix_evaluaciones_created_at", "created_at"),
        # Sin este índice, ORDER BY created_at DESC sería lento
    )
