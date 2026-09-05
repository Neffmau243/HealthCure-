"""
auth.py — ENDPOINTS DE AUTENTICACIÓN

Rutas:
  POST /api/v1/auth/register  → Registrar un usuario nuevo
  POST /api/v1/auth/login     → Iniciar sesión (retorna JWT)
  GET  /api/v1/auth/me        → Datos del usuario autenticado

Autenticación: NO requiere token (son públicas, excepto /me).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.auth_service import AuthService
from app.schemas.usuario import UsuarioCreate, UsuarioLogin, UsuarioResponse, TokenResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def register(data: UsuarioCreate, db: Session = Depends(get_db)):
    """
    Registrar un nuevo usuario en el sistema.

    Body JSON:
      {"nombre": "Dr. García", "email": "garcia@h.com", "password": "123456"}

    SEGURIDAD: El registro público SIEMPRE crea usuarios con rol
    "usuario" (no existe campo rol en este endpoint). Para crear un
    admin, un admin existente debe usar POST /api/v1/admin/usuarios.

    Retorna 201 con los datos del usuario creado (sin password).
    Retorna 409 si el email ya está registrado.
    """
    service = AuthService(db)
    try:
        return service.register(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login", response_model=TokenResponse)
def login(data: UsuarioLogin, db: Session = Depends(get_db)):
    """
    Iniciar sesión y obtener token JWT.

    Body JSON:
      {"email": "garcia@h.com", "password": "123456"}

    Retorna 200 con el token JWT + datos del usuario.
    Retorna 401 si las credenciales son incorrectas.

    El frontend guarda el token y lo envía en cada request:
      Header: Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
    """
    service = AuthService(db)
    try:
        return service.login(data.email, data.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me", response_model=UsuarioResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    """
    Obtener datos del usuario autenticado.

    Requiere: Header Authorization con token JWT válido.

    Retorna 200 con los datos del usuario.
    Retorna 401 si el token es inválido/expirado.
    """
    return current_user
