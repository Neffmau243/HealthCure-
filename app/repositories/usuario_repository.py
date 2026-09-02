"""
usuario_repository.py — REPOSITORY: OPERACIONES DE BD PARA USUARIOS

El Repository es la ÚNICA capa que habla directamente con la BD (MySQL).
Su trabajo es ejecutar queries SQL a través de SQLAlchemy ORM.

RESPONSABILIDADES:
  - Buscar usuarios por ID o email
  - Crear nuevos usuarios
  - Listar todos los usuarios
  - Desactivar usuarios

LO QUE NO HACE:
  - No valida reglas de negocio (eso lo hace el Service)
  - No convierte entre DTOs y ORM (eso lo hace el Mapper)
  - No hashea contraseñas (eso lo hace el Service)
"""
from sqlalchemy.orm import Session
from typing import Optional
from app.models.usuario import Usuario


class UsuarioRepository:
    """
    Repository de usuarios. Recibe una sesión de BD en el constructor
    y la usa para todas las operaciones de persistencia.

    Patrón de diseño: Repository Pattern
    - Separa la lógica de acceso a datos de la lógica de negocio
    - Facilita los tests (se puede mockear el repository)
    - Si cambia la BD (MySQL → PostgreSQL), solo cambia este archivo
    """

    def __init__(self, db: Session):
        """Recibe la sesión de BD que crea FastAPI con get_db()."""
        self.db = db

    def get_by_id(self, usuario_id: int) -> Optional[Usuario]:
        """Busca un usuario por su ID. Retorna None si no existe."""
        return self.db.query(Usuario).filter(Usuario.id == usuario_id).first()
        # .query(Usuario) → SELECT * FROM usuarios
        # .filter(...)   → WHERE id = usuario_id
        # .first()       → LIMIT 1 (retorna solo el primero o None)

    def get_by_email(self, email: str) -> Optional[Usuario]:
        """Busca un usuario por su email (usado en login y registro)."""
        return self.db.query(Usuario).filter(Usuario.email == email).first()

    def create(self, nombre: str, email: str, password_hash: str, rol: str = "usuario") -> Usuario:
        """
        Crea un usuario nuevo en la BD.
        NO hashea la contraseña — eso lo hace el Service antes de llamar aquí.
        """
        usuario = Usuario(
            nombre=nombre,
            email=email,
            password_hash=password_hash,
            rol=rol,
        )
        self.db.add(usuario)     # Agrega a la sesión (no a MySQL todavía)
        self.db.flush()          # Genera el ID autoincremental sin commitear
        return usuario           # Retorna el objeto con el ID ya asignado

    def list_all(self) -> list[Usuario]:
        """Retorna TODOS los usuarios. Usado por el admin."""
        return self.db.query(Usuario).all()
        # .all() → SELECT * FROM usuarios (sin filtro)

    def deactivate(self, usuario_id: int) -> bool:
        """
        Desactiva un usuario (no lo borra físicamente).
        Retorna True si se desactivó, False si no se encontró.
        """
        usuario = self.get_by_id(usuario_id)
        if not usuario:
            return False
        usuario.activo = False   # Soft delete -- el registro sigue existiendo
        self.db.flush()          # Marca el cambio en la sesión
        return True

    def activate(self, usuario_id: int) -> bool:
        """
        Reactiva un usuario desactivado.
        Retorna True si se activó, False si no se encontró.
        """
        usuario = self.get_by_id(usuario_id)
        if not usuario:
            return False
        usuario.activo = True
        self.db.flush()
        return True

    def update(self, usuario_id: int, **kwargs) -> Optional[Usuario]:
        """
        Actualiza campos de un usuario.
        Solo actualiza los campos que se pasen en kwargs.
        Retorna el usuario actualizado o None si no existe.

        Ejemplo de uso:
            repo.update(1, nombre="Nuevo Nombre", rol="admin")
        """
        usuario = self.get_by_id(usuario_id)
        if not usuario:
            return None
        for key, value in kwargs.items():
            if hasattr(usuario, key):
                setattr(usuario, key, value)
        self.db.flush()
        return usuario
