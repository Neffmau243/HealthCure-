"""
paciente.py — SCHEMAS (DTOs) PARA PACIENTES

Contratos de entrada/salida para los datos administrativos del paciente:
  - PacienteCreate   → registrar un paciente nuevo (formato peruano)
  - PacienteUpdate   → actualizar datos existentes (todos opcionales)
  - PacienteResponse → lo que se retorna al frontend

Estos schemas NO tienen nada que ver con el modelo ML.
Las variables predictoras (presión, colesterol, etc.) van en
los schemas de Evaluacion, no aquí.

Distrito y Localidad se envían como ID (distrito_id/localidad_id) y
se retornan como nombre ("distrito": "Alto Selva Alegre") para que el
frontend muestre el texto sin hacer consultas extra.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date, datetime
from enum import Enum


class SexoEnum(str, Enum):
    """Sexo biológico del paciente — coincide con el Enum de MySQL."""
    M = "M"  # Masculino
    F = "F"  # Femenino


class TipoDocumentoEnum(str, Enum):
    """
    Tipos de documento de identidad (Perú).
    - DNI: Documento Nacional de Identidad (nacionales)
    - CE: Carné de Extranjería (extranjeros residentes)
    - Pasaporte (extranjeros sin CE)
    """
    DNI = "DNI"
    CE = "CE"
    Pasaporte = "Pasaporte"


class TipoSeguroEnum(str, Enum):
    """
    Tipos de seguro de salud (Perú).
    - SIS: Seguro Integral de Salud (gratuito, estado)
    - EsSalud: Seguro social (trabajadores formales)
    - Privado: EPS / aseguradora privada
    - Otro: ninguno o no especificado
    """
    SIS = "SIS"
    EsSalud = "EsSalud"
    Privado = "Privado"
    Otro = "Otro"


class PacienteCreate(BaseModel):
    """
    DTO de ENTRADA — registrar un paciente nuevo.

    Ejemplo JSON:
    {
        "tipo_documento": "DNI",
        "documento_identidad": "1032456789",
        "numero_historia_clinica": "72769512",
        "apellido_paterno": "Pérez",
        "apellido_materno": "Rodríguez",
        "nombres": "Juan",
        "fecha_nacimiento": "1965-05-20",
        "sexo": "M",
        "telefono": "987654321",
        "direccion": "Av. Principal 123",
        "distrito_id": 1,
        "localidad_id": 3,
        "tipo_seguro": "SIS",
        "codigo_afiliacion_seguro": "040-2-1032456789",
        "talla_cm": 172.5,
        "peso_kg": 85.3
    }
    """
    # --- Identidad ---
    tipo_documento: TipoDocumentoEnum = TipoDocumentoEnum.DNI
    documento_identidad: str = Field(..., min_length=5, max_length=30)
    # Cédula, DNI, o cualquier documento de identidad del paciente
    # unique en la BD → no se puede duplicar

    numero_historia_clinica: Optional[str] = Field(None, max_length=30)
    # Opcional: número de historia clínica del hospital

    # --- Nombres (formato peruano) ---
    apellido_paterno: str = Field(..., min_length=2, max_length=100)
    apellido_materno: Optional[str] = Field(None, max_length=100)
    nombres: str = Field(..., min_length=2, max_length=100)

    fecha_nacimiento: date
    # Formato ISO: "YYYY-MM-DD" (ej: "1985-03-15")

    sexo: SexoEnum
    # "M" o "F" — validado por el Enum

    # --- Contacto / ubicación ---
    telefono: Optional[str] = Field(None, max_length=20)
    direccion: Optional[str] = Field(None, max_length=200)

    distrito_id: Optional[int] = Field(None, gt=0)
    # ID del distrito (catálogo admin). El frontend lo elige de un dropdown.
    # Si no se envía, el paciente queda sin ubicación (se llena después).

    localidad_id: Optional[int] = Field(None, gt=0)
    # ID de la localidad (debe pertenecer al distrito elegido)

    # --- Seguro ---
    tipo_seguro: TipoSeguroEnum = TipoSeguroEnum.SIS
    codigo_afiliacion_seguro: Optional[str] = Field(None, max_length=50)

    # --- Mediciones (opcionales) ---
    talla_cm: Optional[float] = Field(None, gt=0, le=300)
    peso_kg: Optional[float] = Field(None, gt=0, le=500)


class PacienteUpdate(BaseModel):
    """
    DTO de ENTRADA — actualizar un paciente existente.
    TODOS los campos son opcionales (solo se actualiza lo que se envíe).

    Ejemplo JSON (solo actualizar talla y teléfono):
    {
        "talla_cm": 166.0,
        "telefono": "987654322"
    }
    """
    tipo_documento: Optional[TipoDocumentoEnum] = None
    numero_historia_clinica: Optional[str] = Field(None, max_length=30)
    apellido_paterno: Optional[str] = Field(None, min_length=2, max_length=100)
    apellido_materno: Optional[str] = Field(None, max_length=100)
    nombres: Optional[str] = Field(None, min_length=2, max_length=100)
    fecha_nacimiento: Optional[date] = None
    sexo: Optional[SexoEnum] = None
    telefono: Optional[str] = Field(None, max_length=20)
    direccion: Optional[str] = Field(None, max_length=200)
    distrito_id: Optional[int] = Field(None, gt=0)
    localidad_id: Optional[int] = Field(None, gt=0)
    tipo_seguro: Optional[TipoSeguroEnum] = None
    codigo_afiliacion_seguro: Optional[str] = Field(None, max_length=50)
    activo: Optional[bool] = None
    talla_cm: Optional[float] = Field(None, gt=0, le=300)
    peso_kg: Optional[float] = Field(None, gt=0, le=500)
    # No se puede actualizar documento_identidad (es unique y se usa como búsqueda)


class PacienteResponse(BaseModel):
    """
    DTO de SALIDA — todos los datos del paciente para el frontend.
    Incluye el NOMBRE del distrito/localidad (resueltos desde el catálogo).

    Ejemplo JSON:
    {
        "id": 1,
        "tipo_documento": "DNI",
        "documento_identidad": "1032456789",
        "numero_historia_clinica": "72769512",
        "apellido_paterno": "Pérez",
        "apellido_materno": "Rodríguez",
        "nombres": "Juan",
        "nombre_completo": "PEREZ RODRIGUEZ, Juan",
        "fecha_nacimiento": "1965-05-20",
        "sexo": "M",
        "telefono": "987654321",
        "direccion": "Av. Principal 123",
        "distrito_id": 1,
        "distrito": "Alto Selva Alegre",
        "localidad_id": 3,
        "localidad": "Chilpinilla",
        "tipo_seguro": "SIS",
        "codigo_afiliacion_seguro": "040-2-1032456789",
        "usuario_creador_id": 2,
        "activo": true,
        "talla_cm": 172.5,
        "peso_kg": 85.3,
        "created_at": "2026-09-01T16:02:54",
        "updated_at": "2026-09-01T16:02:54"
    }
    """
    id: int
    tipo_documento: TipoDocumentoEnum
    documento_identidad: str
    numero_historia_clinica: Optional[str] = None
    apellido_paterno: str
    apellido_materno: Optional[str] = None
    nombres: str
    nombre_completo: str
    fecha_nacimiento: date
    sexo: SexoEnum
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    distrito_id: Optional[int] = None
    distrito: Optional[str] = None       # Nombre del distrito (display)
    localidad_id: Optional[int] = None
    localidad: Optional[str] = None      # Nombre de la localidad (display)
    tipo_seguro: TipoSeguroEnum
    codigo_afiliacion_seguro: Optional[str] = None
    usuario_creador_id: Optional[int] = None
    activo: bool
    talla_cm: Optional[float] = None
    peso_kg: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_validator("distrito", "localidad", mode="before")
    @classmethod
    def _extraer_nombre_catalogo(cls, v):
        """
        Convierte el objeto ORM de la relación (Distrito/Localidad) en su
        nombre. Ej: v=Distrito(nombre="Cayma") → "Cayma".
        Si ya es string (o None), lo deja igual.
        """
        if hasattr(v, "nombre"):
            return v.nombre
        return v

    class Config:
        from_attributes = True
        # Permite crear desde objetos SQLAlchemy (ORM)