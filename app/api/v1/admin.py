"""
admin.py — ENDPOINTS DE ADMINISTRACIÓN

Solo los usuarios con rol "admin" pueden acceder a estas rutas.
Si un usuario normal intenta acceder → retorna 403 Forbidden.

Rutas:
  GET /api/v1/admin/usuarios              → Listar todos los usuarios
  PUT /api/v1/admin/usuarios/{id}/deactivate → Desactivar un usuario

Autenticación: Requiere token JWT + rol "admin".
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.admin_service import AdminService
from app.schemas.usuario import UsuarioResponse
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
