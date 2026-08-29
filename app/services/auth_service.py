"""
auth_service.py — SERVICE: AUTENTICACIÓN Y AUTORIZACIÓN

Este servicio maneja todo lo relacionado con:
  - Registrar nuevos usuarios
  - Iniciar sesión (login)
  - Crear y validar tokens JWT
  - Hashear y verificar contraseñas

¿Por qué bcrypt?
Porque es el algoritmo estándar para guardar contraseñas.
NUNCA se guarda la contraseña en texto plano.
Si un hacker roba la BD, solo ve hashes ilegibles.

¿Por qué JWT?
JSON Web Token permite autenticar al usuario SIN guardar sesión
en el servidor. El frontend guarda el token y lo envía en cada request.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt  # python-jose: librería para JWT
from passlib.context import CryptContext  # passlib: librería para bcrypt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.usuario import UsuarioCreate, UsuarioResponse, TokenResponse

settings = get_settings()

# Configuración de bcrypt: algoritmo con salt automático
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# bcrypt genera un hash con "salt" (ruido aleatorio) para que
# dos contraseñas iguales tengan hashes diferentes


class AuthService:
    """
    Service de autenticación. Maneja JWT + bcrypt + registro/login.
    """

    def __init__(self, db: Session):
        self.repo = UsuarioRepository(db)

    # --- BCRYPT: Hashing de contraseñas ---

    def hash_password(self, password: str) -> str:
        """
        Convierte una contraseña en texto a un hash bcrypt.
        Ejemplo: "mi_password" → "$2b$12$LJ3m4ys3G..."

        El hash incluye:
          - Algoritmo (bcrypt)
          - Salt (ruido aleatorio)
          - Hash resultante
        """
        return pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        """
        Verifica si una contraseña en texto plano coincide con un hash.
        Ejemplo: verify_password("mi_password", "$2b$12$LJ3m4ys3G...") → True
        """
        return pwd_context.verify(plain, hashed)

    # --- JWT: Tokens de autenticación ---

    def create_token(self, usuario_id: int, rol: str) -> str:
        """
        Crea un token JWT que contiene:
          - sub: ID del usuario (subject)
          - rol: "admin" o "usuario"
          - exp: fecha de expiración (1 hora por defecto)

        El token se firma con JWT_SECRET_KEY para que nadie lo falsifique.
        """
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
        payload = {
            "sub": str(usuario_id),  # ID del usuario
            "rol": rol,              # Rol para autorización
            "exp": expire,           # Expiración
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def decode_token(self, token: str) -> Optional[dict]:
        """
        Decodifica y valida un token JWT.
        Retorna el payload si es válido, None si expiró o es inválido.
        """
        try:
            return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        except JWTError:
            return None  # Token inválido, expirado, o firma incorrecta

    # --- LOOKUP DE USUARIO ---

    def get_user_by_id(self, usuario_id: int):
        """
        Busca un usuario por ID. Usado por deps.py para validar el JWT.
        Retorna el objeto ORM o None si no existe.
        """
        return self.repo.get_by_id(usuario_id)

    # --- LÓGICA DE NEGOCIO ---

    def register(self, data: UsuarioCreate) -> UsuarioResponse:
        """
        Registra un usuario nuevo.
        1. Verifica que no exista otro usuario con ese email
        2. Hashea la contraseña
        3. Crea el usuario en la BD
        4. Retorna los datos (sin la contraseña)

        SEGURIDAD: Cualquier usuario nuevo se registra como "usuario".
        Solo un admin puede crear otros admins (desde el endpoint /admin).
        """
        if self.repo.get_by_email(data.email):
            raise ValueError("Ya existe un usuario con ese email")

        usuario = self.repo.create(
            nombre=data.nombre,
            email=data.email,
            password_hash=self.hash_password(data.password),
            rol="usuario",  # SEGURIDAD: Siempre "usuario" — ignora data.rol
        )
        return UsuarioResponse.model_validate(usuario)

    def login(self, email: str, password: str) -> TokenResponse:
        """
        Inicia sesión y retorna un token JWT.
        1. Busca el usuario por email
        2. Verifica que esté activo
        3. Compara la contraseña con el hash
        4. Crea y retorna el token JWT
        """
        usuario = self.repo.get_by_email(email)
        if not usuario or not usuario.activo:
            raise ValueError("Credenciales inválidas")
        if not self.verify_password(password, usuario.password_hash):
            raise ValueError("Credenciales inválidas")

        token = self.create_token(usuario.id, usuario.rol)
        return TokenResponse(
            access_token=token,
            usuario=UsuarioResponse.model_validate(usuario),
        )
