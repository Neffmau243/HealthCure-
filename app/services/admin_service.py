"""
admin_service.py — SERVICE: OPERACIONES DE ADMINISTRACIÓN

Maneja las operaciones que SOLO un administrador puede hacer:
  - Listar todos los usuarios del sistema
  - Desactivar usuarios (soft delete)
  - (Futuro) Crear admins, editar roles, etc.

¿Por qué un AdminService separado?
Porque las operaciones admin tienen reglas diferentes:
  - Solo acceden usuarios con rol "admin"
  - Operan sobre la tabla de usuarios (no pacientes ni evaluaciones)
  - Pueden tener lógica de auditoría (quién desactivó a quién)

Si todo estuviera en AuthService, ese service haría demasiado
(auth + admin = dos responsabilidades distintas).
"""
from sqlalchemy.orm import Session
from typing import Optional
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.usuario import UsuarioResponse


class AdminService:
    """
    Service de administración. Maneja operaciones admin sobre usuarios.
    """

    def __init__(self, db: Session):
        self.repo = UsuarioRepository(db)

    def list_usuarios(self) -> list[UsuarioResponse]:
        """
        Retorna TODOS los usuarios del sistema.
        Usado por el admin para ver quiénes tienen acceso.

        No aplica paginación porque en un hospital típico
        hay pocos usuarios (decenas, no miles).
        """
        usuarios = self.repo.list_all()
        return [UsuarioResponse.model_validate(u) for u in usuarios]

    def deactivate_usuario(self, usuario_id: int) -> Optional[UsuarioResponse]:
        """
        Desactiva un usuario (soft delete).

        ¿Qué es soft delete?
        - El usuario NO se borra de la BD
        - Solo se marca activo=False
        - Sigue existiendo para auditoría
        - Sus evaluaciones siguen intactas
        - NO puede hacer login

        Retorna el usuario desactivado o None si no existe.
        """
        usuario = self.repo.get_by_id(usuario_id)
        if not usuario:
            return None

        self.repo.deactivate(usuario_id)
        return UsuarioResponse.model_validate(usuario)
