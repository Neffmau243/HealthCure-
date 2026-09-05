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
from app.repositories.distrito_repository import DistritoRepository
from app.repositories.localidad_repository import LocalidadRepository
from app.services.auth_service import AuthService
from app.schemas.usuario import UsuarioResponse, UsuarioUpdate, UsuarioAdminCreate
from app.schemas.catalogo import (
    DistritoCreate, DistritoUpdate, DistritoResponse,
    LocalidadCreate, LocalidadUpdate, LocalidadResponse,
)


class AdminService:
    """
    Service de administración. Maneja operaciones admin sobre usuarios.
    """

    def __init__(self, db: Session):
        self.db = db  # Sesión de BD (usada por AuthService para hashear)
        self.repo = UsuarioRepository(db)
        self.distrito_repo = DistritoRepository(db)
        self.localidad_repo = LocalidadRepository(db)

    # --- GUARDS DE SEGURIDAD (evitan el lockout total del sistema) ---

    def _es_ultimo_admin_activo(self, target) -> bool:
        """
        True si el usuario objetivo es un admin ACTIVO y es el ÚNICO
        admin activo del sistema. Si se le quita el rol o se le desactiva,
        nadie podría gestionar la app → lo bloqueamos.
        """
        if target.rol != "admin" or not target.activo:
            return False
        return self.repo.count_active_admins() <= 1

    def _guardar_desactivacion(self, target, current_admin_id: int):
        """
        Reglas antes de desactivar a un usuario o quitarle el rol admin:
          1. Un admin NO puede desactivarse/autodegradarse a sí mismo.
          2. Nadie puede dejar al sistema sin administradores activos.
        Lanza ValueError (→ HTTP 409 en el controller).
        """
        if target.id == current_admin_id:
            raise ValueError(
                "No puedes desactivar ni cambiar el rol de tu propia cuenta. "
                "Pide a otro administrador que lo haga."
            )
        if self._es_ultimo_admin_activo(target):
            raise ValueError(
                "No puedes desactivar al último administrador activo. "
                "Crea otro admin antes de hacerlo."
            )

    def list_usuarios(self) -> list[UsuarioResponse]:
        """
        Retorna TODOS los usuarios del sistema.
        Usado por el admin para ver quiénes tienen acceso.

        No aplica paginación porque en un hospital típico
        hay pocos usuarios (decenas, no miles).
        """
        usuarios = self.repo.list_all()
        return [UsuarioResponse.model_validate(u) for u in usuarios]

    def deactivate_usuario(self, usuario_id: int, current_admin_id: int = None) -> Optional[UsuarioResponse]:
        """
        Desactiva un usuario (soft delete).

        Que es soft delete?
        - El usuario NO se borra de la BD
        - Solo se marca activo=False
        - Sigue existiendo para auditoria
        - Sus evaluaciones siguen intactas
        - NO puede hacer login

        SEGURIDAD (guards):
          - No puedes desactivar tu propia cuenta
          - No puedes desactivar al ÚLTIMO admin activo (lockout)

        Retorna el usuario desactivado o None si no existe.
        Lanza ValueError si la acción viola un guard.
        """
        usuario = self.repo.get_by_id(usuario_id)
        if not usuario:
            return None

        self._guardar_desactivacion(usuario, current_admin_id)

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

        auth = AuthService(self.db)

        usuario = self.repo.create(
            nombre=data.nombre,
            email=data.email,
            password_hash=auth.hash_password(data.password),
            rol=data.rol.value,
        )
        return UsuarioResponse.model_validate(usuario)

    def update_usuario(
        self,
        usuario_id: int,
        data: UsuarioUpdate,
        current_admin_id: int = None,
    ) -> Optional[UsuarioResponse]:
        """
        Actualiza campos de un usuario.
        Solo actualiza los campos enviados (update parcial).
        Si se cambia el email, verifica que no este en uso.
        Si se cambia la password, la hashea.

        SEGURIDAD (guards):
          - No puedes quitarte el rol admin ni desactivar tu propia cuenta
          - No puedes degradar/desactivar al ÚLTIMO admin activo (lockout)

        Retorna el usuario actualizado o None si no existe.
        Lanza ValueError si el email ya esta en uso o la acción viola un guard.
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
            auth = AuthService(self.db)
            update_data["password_hash"] = auth.hash_password(update_data.pop("password"))

        # Convertir enums a strings para SQLAlchemy
        nuevo_rol = usuario.rol
        if "rol" in update_data and update_data["rol"] is not None:
            nuevo_rol = update_data["rol"].value
            update_data["rol"] = nuevo_rol

        # --- Guards anti-lockout (solo si se toca rol o activo) ---
        toca_rol = "rol" in update_data and nuevo_rol != usuario.rol
        toca_activo = "activo" in update_data and update_data["activo"] is False
        if toca_rol or toca_activo:
            # Simula el estado post-cambio para validar contra el último admin
            original_rol, original_activo = usuario.rol, usuario.activo
            if toca_rol:
                usuario.rol = nuevo_rol
            if toca_activo:
                usuario.activo = False
            try:
                self._guardar_desactivacion(usuario, current_admin_id)
            finally:
                # Restaurar el estado real (aún no persistido)
                usuario.rol, usuario.activo = original_rol, original_activo

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

    # ============================================================
    # CATÁLOGOS: DISTRITOS
    # ============================================================

    def list_distritos(self) -> list[DistritoResponse]:
        """Retorna TODOS los distritos (activos e inactivos) para el admin."""
        return [DistritoResponse.model_validate(d) for d in self.distrito_repo.list_all()]

    def get_distrito(self, distrito_id: int) -> Optional[DistritoResponse]:
        """Obtiene un distrito por ID. None si no existe."""
        distrito = self.distrito_repo.get_by_id(distrito_id)
        if not distrito:
            return None
        return DistritoResponse.model_validate(distrito)

    def create_distrito(self, data: DistritoCreate) -> DistritoResponse:
        """
        Crea un distrito nuevo. Lanza ValueError si el nombre ya existe.
        """
        if self.distrito_repo.get_by_nombre(data.nombre):
            raise ValueError("Ya existe un distrito con ese nombre")
        distrito = self.distrito_repo.create(nombre=data.nombre)
        return DistritoResponse.model_validate(distrito)

    def update_distrito(self, distrito_id: int, data: DistritoUpdate) -> Optional[DistritoResponse]:
        """
        Actualiza un distrito (nombre y/o activo).
        Si renombra, verifica que el nuevo nombre no esté en uso.
        Retorna None si no existe.
        """
        distrito = self.distrito_repo.get_by_id(distrito_id)
        if not distrito:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "nombre" in update_data and update_data["nombre"] != distrito.nombre:
            if self.distrito_repo.get_by_nombre(update_data["nombre"]):
                raise ValueError("Ya existe otro distrito con ese nombre")

        self.distrito_repo.update(distrito_id, **update_data)
        distrito = self.distrito_repo.get_by_id(distrito_id)
        return DistritoResponse.model_validate(distrito)

    def deactivate_distrito(self, distrito_id: int) -> Optional[DistritoResponse]:
        """
        Desactiva un distrito (soft delete): ya no aparece en los
        dropdowns del doctor, pero sus datos siguen en la BD.
        """
        distrito = self.distrito_repo.get_by_id(distrito_id)
        if not distrito:
            return None
        self.distrito_repo.update(distrito_id, activo=False)
        return DistritoResponse.model_validate(distrito)

    # ============================================================
    # CATÁLOGOS: LOCALIDADES
    # ============================================================

    def list_localidades(self, distrito_id: int | None = None) -> list[LocalidadResponse]:
        """
        Retorna localidades (para el admin).
        Con distrito_id filtra por distrito; sin él, todas.
        """
        if distrito_id is not None:
            localidades = self.localidad_repo.list_by_distrito(distrito_id, solo_activas=False)
        else:
            localidades = self.localidad_repo.list_all()
        return [LocalidadResponse.model_validate(l) for l in localidades]

    def get_localidad(self, localidad_id: int) -> Optional[LocalidadResponse]:
        """Obtiene una localidad por ID. None si no existe."""
        localidad = self.localidad_repo.get_by_id(localidad_id)
        if not localidad:
            return None
        return LocalidadResponse.model_validate(localidad)

    def create_localidad(self, data: LocalidadCreate) -> LocalidadResponse:
        """
        Crea una localidad dentro de un distrito.
        Lanza ValueError si el distrito no existe o la localidad ya está
        registrada en ese distrito.
        """
        if not self.distrito_repo.get_by_id(data.distrito_id):
            raise ValueError("El distrito no existe")
        if self.localidad_repo.get_by_nombre(data.nombre, data.distrito_id):
            raise ValueError("Ya existe una localidad con ese nombre en ese distrito")

        localidad = self.localidad_repo.create(
            nombre=data.nombre,
            distrito_id=data.distrito_id,
        )
        return LocalidadResponse.model_validate(localidad)

    def update_localidad(self, localidad_id: int, data: LocalidadUpdate) -> Optional[LocalidadResponse]:
        """
        Actualiza una localidad (nombre, distrito y/o activo).
        Retorna None si no existe. Lanza ValueError si hay conflicto.
        """
        localidad = self.localidad_repo.get_by_id(localidad_id)
        if not localidad:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Si cambia de distrito, verificar que exista
        nuevo_distrito_id = update_data.get("distrito_id", localidad.distrito_id)
        if not self.distrito_repo.get_by_id(nuevo_distrito_id):
            raise ValueError("El distrito no existe")

        # Duplicado de nombre dentro del distrito (excluyéndose a sí misma)
        nuevo_nombre = update_data.get("nombre", localidad.nombre)
        existing = self.localidad_repo.get_by_nombre(nuevo_nombre, nuevo_distrito_id)
        if existing and existing.id != localidad_id:
            raise ValueError("Ya existe una localidad con ese nombre en ese distrito")

        self.localidad_repo.update(localidad_id, **update_data)
        localidad = self.localidad_repo.get_by_id(localidad_id)
        return LocalidadResponse.model_validate(localidad)

    def deactivate_localidad(self, localidad_id: int) -> Optional[LocalidadResponse]:
        """
        Desactiva una localidad (soft delete): ya no aparece en los
        dropdowns del doctor.
        """
        localidad = self.localidad_repo.get_by_id(localidad_id)
        if not localidad:
            return None
        self.localidad_repo.update(localidad_id, activo=False)
        return LocalidadResponse.model_validate(localidad)
