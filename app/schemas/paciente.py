"""
paciente.py — SCHEMAS (DTOs) PARA PACIENTES

Contratos de entrada/salida para los datos administrativos del paciente:
  - PacienteCreate   → registrar un paciente nuevo
  - PacienteUpdate   → actualizar datos existentes (todos opcionales)
  - PacienteResponse → lo que se retorna al frontend

Estos schemas NO tienen nada que ver con el modelo ML.
Las variables predictoras (presión, colesterol, etc.) van en
los schemas de Evaluacion, no aquí.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from enum import Enum


class SexoEnum(str, Enum):
    """Sexo biológico del paciente — coincide con el Enum de MySQL."""
    M = "M"  # Masculino
    F = "F"  # Femenino


class PacienteCreate(BaseModel):
    """
    DTO de ENTRADA — registrar un paciente nuevo.

    Ejemplo JSON:
    {
        "nombre": "María López",
        "documento_identidad": "1234567890",
        "fecha_nacimiento": "1985-03-15",
        "sexo": "F",
        "talla_cm": 165.5,
        "peso_kg": 70.2
    }
    """
    nombre: str = Field(..., min_length=2, max_length=150)

    documento_identidad: str = Field(..., min_length=5, max_length=30)
    # Cédula, DNI, o cualquier documento de identidad del paciente
    # unique en la BD → no se puede duplicar

    fecha_nacimiento: date
    # Formato ISO: "YYYY-MM-DD" (ej: "1985-03-15")

    sexo: SexoEnum
    # "M" o "F" — validado por el Enum

    talla_cm: Optional[float] = Field(None, gt=0, le=300)
    # Optional = puede no enviarse (None)
    # gt=0 → mayor que 0, le=300 → menor o igual a 300

    peso_kg: Optional[float] = Field(None, gt=0, le=500)
    # Opcional también — se puede registrar el paciente y llenar después


class PacienteUpdate(BaseModel):
    """
    DTO de ENTRADA — actualizar un paciente existente.
    TODOS los campos son opcionales (solo se actualiza lo que se envíe).

    Ejemplo JSON (solo actualizar talla y peso):
    {
        "talla_cm": 166.0,
        "peso_kg": 71.5
    }
    """
    nombre: Optional[str] = Field(None, min_length=2, max_length=150)
    fecha_nacimiento: Optional[date] = None
    sexo: Optional[SexoEnum] = None
    talla_cm: Optional[float] = Field(None, gt=0, le=300)
    peso_kg: Optional[float] = Field(None, gt=0, le=500)
    # No se puede actualizar documento_identidad (es unique y se usa como búsqueda)


class PacienteResponse(BaseModel):
    """
    DTO de SALIDA — todos los datos del paciente para el frontend.

    Ejemplo JSON:
    {
        "id": 1,
        "nombre": "María López",
        "documento_identidad": "1234567890",
        "fecha_nacimiento": "1985-03-15",
        "sexo": "F",
        "talla_cm": 165.5,
        "peso_kg": 70.2,
        "created_at": "2025-01-15T10:30:00"
    }
    """
    id: int
    nombre: str
    documento_identidad: str
    fecha_nacimiento: date
    sexo: SexoEnum
    talla_cm: Optional[float] = None
    peso_kg: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True
        # Permite crear desde objetos SQLAlchemy (ORM)
