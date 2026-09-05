"""
usuario.py — SCHEMAS (DTOs) PARA USUARIOS

Los schemas definen la FORMA de los datos que entran y salen de la API.
Son los "contratos" entre el frontend y el backend:

  - UsuarioCreate       → lo que el frontend envía al registrarse (registro PÚBLICO)
  - UsuarioAdminCreate  → lo que el admin envía al crear un usuario (puede elegir rol)
  - UsuarioLogin        → lo que el frontend envía al hacer login
  - UsuarioResponse     → lo que el backend retorna al frontend
  - TokenResponse       → lo que el backend retorna después de un login exitoso

IMPORTANTE: Pydantic valida automáticamente que los datos cumplan
las restricciones (email válido, password mínimo 6 caracteres, etc.)
Si algo falla, FastAPI retorna un error 422 con los campos inválidos.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class RolEnum(str, Enum):
    """
    Roles disponibles en el sistema.
    - admin: puede ver y desactivar usuarios
    - usuario: solo puede registrar pacientes y hacer evaluaciones
    """
    admin = "admin"
    usuario = "usuario"


class UsuarioCreate(BaseModel):
    """
    DTO de ENTRADA — lo que el frontend envía al REGISTRO PÚBLICO
    (POST /api/v1/auth/register).

    Ejemplo JSON:
    {
        "nombre": "Dr. García",
        "email": "garcia@hospital.com",
        "password": "mi_password_seguro"
    }

    NOTA DE SEGURIDAD: NO existe campo "rol" aquí a propósito.
    El registro público SIEMPRE crea usuarios con rol "usuario".
    Si se necesitara crear un admin, eso lo hace un admin existente
    desde POST /api/v1/admin/usuarios (schema UsuarioAdminCreate).
    """
    nombre: str = Field(..., min_length=2, max_length=150)
    # ... = obligatorio (no tiene valor por defecto)
    # min_length/max_length = validación de Pydantic automática

    email: EmailStr  # Valida que sea un email real (con @ y dominio)

    password: str = Field(..., min_length=6, max_length=128)
    # La contraseña NUNCA se retorna en las respuestas, solo se recibe


class UsuarioLogin(BaseModel):
    """
    DTO de ENTRADA — lo que el frontend envía para hacer login.

    Ejemplo JSON:
    {
        "email": "garcia@hospital.com",
        "password": "mi_password_seguro"
    }
    """
    email: EmailStr
    password: str


class UsuarioResponse(BaseModel):
    """
    DTO de SALIDA — lo que el backend retorna al frontend.
    NUNCA incluye password_hash (eso es secreto).

    Ejemplo JSON:
    {
        "id": 1,
        "nombre": "Dr. García",
        "email": "garcia@hospital.com",
        "rol": "usuario",
        "activo": true,
        "created_at": "2025-01-15T10:30:00"
    }
    """
    id: int
    nombre: str
    email: str
    rol: RolEnum
    activo: bool
    created_at: datetime

    class Config:
        from_attributes = True
        # Permite crear el schema desde un objeto SQLAlchemy (ORM)
        # Sin esto, model_validate(usuario_orm) daría error


class UsuarioUpdate(BaseModel):
    """
    DTO de ENTRADA — lo que el admin envía para editar un usuario existente.
    Todos los campos son opcionales (update parcial).

    Ejemplo JSON:
    {
        "nombre": "Dr. García (Editado)",
        "rol": "admin",
        "activo": false
    }
    """
    nombre: Optional[str] = Field(None, min_length=2, max_length=150)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6, max_length=128)
    rol: Optional[RolEnum] = None
    activo: Optional[bool] = None


class UsuarioAdminCreate(BaseModel):
    """
    DTO de ENTRADA — lo que el admin envía para crear un usuario.
    A diferencia de UsuarioCreate (registro público), aquí el admin SÍ puede
    elegir el rol (admin o usuario) y asignar una contraseña.

    Ejemplo JSON:
    {
        "nombre": "Dr. García",
        "email": "garcia@hospital.com",
        "password": "mi_password_seguro",
        "rol": "admin"
    }
    """
    nombre: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    rol: RolEnum = RolEnum.usuario


class TokenResponse(BaseModel):
    """
    DTO de SALIDA — respuesta del login exitoso.
    Incluye el JWT token para que el frontend lo guarde y lo envíe
    en cada request como header: Authorization: Bearer <token>

    Ejemplo JSON:
    {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "bearer",
        "usuario": { ... }
    }
    """
    access_token: str
    token_type: str = "bearer"  # Siempre "bearer" para JWT
    usuario: UsuarioResponse    # Datos del usuario (sin password)
