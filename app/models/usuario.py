"""
usuario.py — MODELO: TABLA DE USUARIOS DEL SISTEMA

Cada usuario es una persona que tiene acceso al sistema:
  - Médicos que registran pacientes y hacen evaluaciones
  - Administradores que gestionan usuarios

Esta tabla es la fuente de verdad para la autenticación (login/registro).
La contraseña NUNCA se guarda en texto plano — se almacena como hash bcrypt.
"""
from sqlalchemy import (
    Column, BigInteger, String, Enum, Boolean, DateTime, func
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Usuario(Base):
    """
    Representa la tabla 'usuarios' en MySQL.
    SQLAlchemy mapea cada atributo a una columna de la tabla.
    """
    __tablename__ = "usuarios"

    # --- Identificador único ---
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # BigInteger = BIGINT en MySQL (hasta 9.2 quintillones de registros)

    # --- Datos del usuario ---
    nombre        = Column(String(150), nullable=False)
    email         = Column(String(255), nullable=False, unique=True, index=True)
    # unique=True → no puede haber dos usuarios con el mismo email
    # index=True  → búsquedas por email son rápidas (índice automático)

    password_hash = Column(String(255), nullable=False)
    # Almacena el hash bcrypt de la contraseña, NUNCA el texto plano

    # --- Rol de acceso ---
    rol = Column(
        Enum("admin", "usuario", name="rol_enum"),
        # MySQL solo acepta estos dos valores. El name="rol_enum" es el nombre
        # del tipo Enum en MySQL (para poder hacer DROP después si hace falta)
        nullable=False,
        default="usuario"  # Por defecto, todos los nuevos usuarios son "usuario"
    )

    # --- Estado de la cuenta ---
    activo = Column(Boolean, nullable=False, default=True)
    # False = usuario desactivado (no puede hacer login)

    # --- Timestamps ---
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    # server_default=func.now() → MySQL pone CURRENT_TIMESTAMP automáticamente

    updated_at = Column(
        DateTime, server_default=func.now(),
        onupdate=func.now(),  # Se actualiza SOLO cuando cambia un campo
        nullable=False
    )

    # --- Relaciones con otras tablas ---
    evaluaciones = relationship("Evaluacion", back_populates="usuario")
    # Un usuario puede crear MUCHAS evaluaciones
    # back_populates="usuario" → desde Evaluacion se puede acceder al usuario padre
