"""
atencion.py — SCHEMAS (DTOs) PARA ATENCIONES DEL CONSULTORIO

Contratos de entrada/salida del acto médico:
  - AtencionCreate   → registrar el diagnóstico/tratamiento de una consulta
  - AtencionResponse → lo que se retorna al frontend

La atención referencia al paciente (obligatorio) y opcionalmente a la
evaluación cardíaca que la originó.
"""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from datetime import datetime


class AtencionCreate(BaseModel):
    """
    DTO de ENTRADA — registrar una atención.

    Ejemplo JSON:
    {
        "paciente_id": 1,
        "evaluacion_id": 8,
        "diagnostico": "HTA no controlada + dislipidemia mixta.",
        "tratamiento": "Losartán 50mg cada 12h por 30 días.",
        "indicaciones": "Dieta hiposódica y control en 15 días."
    }
    """
    paciente_id: int = Field(..., gt=0)

    evaluacion_id: Optional[int] = Field(None, gt=0)
    # Opcional: la evaluación que se revisó en esta consulta

    diagnostico: str = Field(..., min_length=3, max_length=2000)

    tratamiento: str = Field(..., min_length=3, max_length=2000)

    indicaciones: Optional[str] = Field(None, max_length=2000)


class AtencionResponse(BaseModel):
    """
    DTO de SALIDA — atención completa para el frontend.

    Ejemplo JSON:
    {
        "id": 1,
        "paciente_id": 1,
        "paciente_nombre": "PÉREZ RODRÍGUEZ, Juan",
        "evaluacion_id": 8,
        "usuario_id": 2,
        "diagnostico": "HTA no controlada + dislipidemia mixta.",
        "tratamiento": "Losartán 50mg cada 12h por 30 días.",
        "indicaciones": "Dieta hiposódica y control en 15 días.",
        "created_at": "2026-10-06T10:30:00",
        "updated_at": "2026-10-06T10:30:00"
    }
    """
    id: int
    paciente_id: int
    paciente_nombre: Optional[str] = None   # Resuelto del ORM (display)
    evaluacion_id: Optional[int] = None
    usuario_id: int
    diagnostico: str
    tratamiento: str
    indicaciones: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_validator("paciente_nombre", mode="before")
    @classmethod
    def _extraer_nombre_paciente(cls, v):
        """
        Si llega un objeto ORM Paciente en vez del nombre, extrae
        nombre_completo. Si ya es string (o None), lo deja igual.
        """
        if hasattr(v, "nombre_completo"):
            return v.nombre_completo
        return v

    # Pydantic v2: ConfigDict reemplaza al `class Config` deprecado.
    model_config = ConfigDict(from_attributes=True)
