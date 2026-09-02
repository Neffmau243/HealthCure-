"""
admin.py — ENDPOINTS DE ADMINISTRACIÓN (CRUD de Usuarios)

Solo los usuarios con rol "admin" pueden acceder a estas rutas.
Si un usuario normal intenta acceder → retorna 403 Forbidden.

Rutas:
  GET    /api/v1/admin/usuarios                    → Listar todos los usuarios
  GET    /api/v1/admin/usuarios/{id}               → Obtener usuario por ID
  POST   /api/v1/admin/usuarios                    → Crear usuario (admin elige rol)
  PUT    /api/v1/admin/usuarios/{id}               → Actualizar usuario (parcial)
  PUT    /api/v1/admin/usuarios/{id}/activate      → Reactivar usuario
  PUT    /api/v1/admin/usuarios/{id}/deactivate    → Desactivar usuario (soft delete)

Autenticación: Requiere token JWT + rol "admin".

Nota de seguridad:
  - El registro Púbrico (/auth/register) SIEMPRE crea usuarios como "usuario"
  - Solo desde AQUÍ un admin puede crear otros admins o cambiar roles
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.admin_service import AdminService
from app.schemas.usuario import UsuarioResponse, UsuarioUpdate, UsuarioAdminCreate
from app.api.deps import require_admin  # Solo admins pueden usar estas rutas

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/usuarios", response_model=list[UsuarioResponse])
def list_usuarios(
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """
    Listar TODOS los usuarios del sistema.
    Solo accesible por administradores.

    Retorna la lista completa de usuarios (sin passwords).
    """
    service = AdminService(db)
    return service.list_usuarios()


@router.get("/usuarios/{usuario_id}", response_model=UsuarioResponse)
def get_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """
    Obtener un usuario por ID.
    Solo accesible por administradores.

    Retorna 404 si el usuario no existe.
    """
    service = AdminService(db)
    usuario = service.get_usuario(usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    return usuario


@router.post("/usuarios", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def create_usuario(
    data: UsuarioAdminCreate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """
    Crear un usuario nuevo (como admin).
    El admin SÍ puede elegir el rol (admin o usuario).

    Retorna 409 si el email ya esta en uso.
    """
    service = AdminService(db)
    try:
        return service.create_usuario(data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.put("/usuarios/{usuario_id}", response_model=UsuarioResponse)
def update_usuario(
    usuario_id: int,
    data: UsuarioUpdate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """
    Actualizar un usuario existente (update parcial).
    Solo los campos enviados se actualizan.

    El admin puede cambiar: nombre, email, password, rol, activo.
    Retorna 404 si no existe, 409 si el email ya esta en uso.
    """
    service = AdminService(db)
    try:
        usuario = service.update_usuario(usuario_id, data)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        return usuario
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.put("/usuarios/{usuario_id}/activate", response_model=UsuarioResponse)
def activate_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """
    Reactivar un usuario desactivado.
    Solo accesible por administradores.

    Retorna 404 si el usuario no existe.
    """
    service = AdminService(db)
    usuario = service.activate_usuario(usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    return usuario


@router.put("/usuarios/{usuario_id}/deactivate")
def deactivate_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """
    Desactivar un usuario (soft delete).
    El usuario no se borra físicamente, solo se marca como inactivo.

    Un usuario desactivado:
      - NO puede hacer login
      - Sigue existiendo en la BD (para auditoría)
      - Sus evaluaciones siguen intactas

    Retorna 200 si se desactivó.
    Retorna 404 si el usuario no existe.
    """
    service = AdminService(db)
    usuario = service.deactivate_usuario(usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    return {"message": "Usuario desactivado correctamente"}
