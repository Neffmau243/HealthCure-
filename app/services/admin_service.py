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
from app.schemas.usuario import UsuarioResponse, UsuarioUpdate, UsuarioAdminCreate


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

        Que es soft delete?
        - El usuario NO se borra de la BD
        - Solo se marca activo=False
        - Sigue existiendo para auditoria
        - Sus evaluaciones siguen intactas
        - NO puede hacer login

        Retorna el usuario desactivado o None si no existe.
        """
        usuario = self.repo.get_by_id(usuario_id)
        if not usuario:
            return None

        self.repo.deactivate(usuario_id)
        return UsuarioResponse.model_validate(usuario)

    # --- CRUD COMPLETO PARA EL ADMIN ---

    def get_usuario(self, usuario_id: int) -> Optional[UsuarioResponse]:
        """
        Obtiene un usuario por ID.
        Retorna UsuarioResponse o None si no existe.
        """
        usuario = self.repo.get_by_id(usuario_id)
        if not usuario:
            return None
        return UsuarioResponse.model_validate(usuario)

    def create_usuario(self, data: UsuarioAdminCreate) -> UsuarioResponse:
        """
        Crea un usuario nuevo (como admin).

        Diferencia con AuthService.register():
        - El admin SÍ puede elegir el rol (admin o usuario)
        - El admin puede crear otros admins
        - No requiere estar autenticado como el nuevo usuario

        Lanza ValueError si el email ya existe.
        """
        if self.repo.get_by_email(data.email):
            raise ValueError("Ya existe un usuario con ese email")

        from app.services.auth_service import AuthService
        auth = AuthService(self.repo.db)

        usuario = self.repo.create(
            nombre=data.nombre,
            email=data.email,
            password_hash=auth.hash_password(data.password),
            rol=data.rol.value,
        )
        return UsuarioResponse.model_validate(usuario)

    def update_usuario(self, usuario_id: int, data: UsuarioUpdate) -> Optional[UsuarioResponse]:
        """
        Actualiza campos de un usuario.
        Solo actualiza los campos enviados (update parcial).
        Si se cambia el email, verifica que no este en uso.
        Si se cambia la password, la hashea.

        Retorna el usuario actualizado o None si no existe.
        Lanza ValueError si el email ya esta en uso por otro usuario.
        """
        usuario = self.repo.get_by_id(usuario_id)
        if not usuario:
            return None

        update_data = data.model_dump(exclude_unset=True)
        # exclude_unset=True: solo toma los campos que el usuario envió
        # Si no envio "nombre", no se actualiza nombre

        # Verificar email duplicado si se esta cambiando
        if "email" in update_data and update_data["email"] != usuario.email:
            existing = self.repo.get_by_email(update_data["email"])
            if existing:
                raise ValueError("Ya existe otro usuario con ese email")

        # Hashear password si se esta cambiando
        if "password" in update_data:
            from app.services.auth_service import AuthService
            auth = AuthService(self.repo.db)
            update_data["password_hash"] = auth.hash_password(update_data.pop("password"))

        # Convertir enums a strings para SQLAlchemy
        if "rol" in update_data and update_data["rol"] is not None:
            update_data["rol"] = update_data["rol"].value

        self.repo.update(usuario_id, **update_data)
        # Recargar el usuario actualizado
        usuario = self.repo.get_by_id(usuario_id)
        return UsuarioResponse.model_validate(usuario)

    def activate_usuario(self, usuario_id: int) -> Optional[UsuarioResponse]:
        """
        Reactiva un usuario desactivado.
        Retorna el usuario activado o None si no existe.
        """
        usuario = self.repo.get_by_id(usuario_id)
        if not usuario:
            return None

        self.repo.activate(usuario_id)
        return UsuarioResponse.model_validate(usuario)
