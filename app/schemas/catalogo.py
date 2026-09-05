"""
catalogo.py — SCHEMAS (DTOs) PARA CATÁLOGOS ADMIN

Catálogos = tablas de opciones que gestiona el administrador:
  - Distrito:   "Alto Selva Alegre", "Cayma", "Miraflores"...
  - Localidad:  "Chilpinilla", "El Mirador" (dentro de un distrito)

Flujo:
  Admin  → CRUD de distritos/localidades (POST/PUT/DELETE)
  Doctor → Solo LEE las opciones activas para llenar sus formularios

Los DTOs:
  - XCreate   → lo que el admin envía al crear
  - XUpdate   → lo que el admin envía al editar (todo opcional)
  - XResponse → lo que la API retorna
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


# ============================================================
# DISTRITO
# ============================================================
class DistritoCreate(BaseModel):
    """
    DTO de ENTRADA — crear un distrito.

    Ejemplo JSON:
      {"nombre": "Alto Selva Alegre"}
    """
    nombre: str = Field(..., min_length=2, max_length=100)


class DistritoUpdate(BaseModel):
    """
    DTO de ENTRADA — editar un distrito (update parcial).
    El admin puede renombrarlo o desactivarlo (no aparece más para el doctor).
    """
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    activo: Optional[bool] = None


class DistritoResponse(BaseModel):
    """
    DTO de SALIDA — distrito completo.
    Ejemplo JSON:
      {"id": 1, "nombre": "Alto Selva Alegre", "activo": true,
       "created_at": "2026-09-01T16:02:54"}
    """
    id: int
    nombre: str
    activo: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# LOCALIDAD
# ============================================================
class LocalidadCreate(BaseModel):
    """
    DTO de ENTRADA — crear una localidad.
    Debe pertenecer a un distrito.

    Ejemplo JSON:
      {"nombre": "Chilpinilla", "distrito_id": 1}
    """
    nombre: str = Field(..., min_length=2, max_length=100)
    distrito_id: int = Field(..., gt=0)


class LocalidadUpdate(BaseModel):
    """
    DTO de ENTRADA — editar una localidad (update parcial).
    """
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    distrito_id: Optional[int] = Field(None, gt=0)
    activo: Optional[bool] = None


class LocalidadResponse(BaseModel):
    """
    DTO de SALIDA — localidad completa.
    Incluye el nombre del distrito al que pertenece (para mostrarlo
    en las listas del admin sin hacer otra consulta).

    Ejemplo JSON:
      {"id": 1, "nombre": "Chilpinilla", "distrito_id": 1,
       "distrito": "Alto Selva Alegre", "activo": true,
       "created_at": "2026-09-01T16:02:54"}
    """
    id: int
    nombre: str
    distrito_id: int
    distrito: Optional[str] = None  # Nombre del distrito (para display)
    activo: bool
    created_at: datetime

    @field_validator("distrito", mode="before")
    @classmethod
    def _extraer_nombre_distrito(cls, v):
        """
        Convierte el objeto ORM de la relación Distrito en su nombre.
        Ej: v=Distrito(nombre="Cayma") → "Cayma".
        Si ya es string (o None), lo deja igual.
        """
        if hasattr(v, "nombre"):
            return v.nombre
        return v

    class Config:
        from_attributes = True