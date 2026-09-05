"""
deps.py — DEPENDENCIAS COMPARTIDAS DE FASTAPI

Las "dependencies" de FastAPI son funciones que se ejecutan ANTES
de cada endpoint y pueden:
  - Extraer datos del request (token JWT, headers, etc.)
  - Inyectar servicios (db session, repositories, etc.)
  - Validar permisos (¿es admin? ¿está autenticado?)

Se usan con Depends() en los endpoints:
    @router.get("/algo")
    def mi_endpoint(current_user: dict = Depends(get_current_user)):
        ...  # current_user ya tiene los datos del usuario autenticado
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.auth_service import AuthService

# Configuración del token OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
# tokenUrl = dónde el frontend puede obtener el token (ruta de login)
# FastAPI muestra el botón "Authorize" en /docs gracias a esto


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> dict:
    """
    DEPENDENCY: Extrae y valida el usuario del JWT.

    Se ejecuta en CADA endpoint que requiere autenticación.
    Flujo:
      1. FastAPI extrae el token del header Authorization: Bearer <token>
      2. Decodificamos el token con JWT
      3. Buscamos el usuario en la BD via AuthService
      4. Verificamos que esté activo
      5. Retornamos los datos del usuario

    Si algo falla → retorna 401 (Unauthorized)

    Uso:
        @router.get("/algo")
        def mi_endpoint(current_user: dict = Depends(get_current_user)):
            # current_user = {"id": 1, "nombre": "Dr. García", ...}
            print(current_user["id"])  # ID del usuario autenticado
    """
    # Solo AuthService maneja JWT + lookup de usuario.
    # Antes esto usaba UsuarioRepository directamente, lo cual
    # bypaseaba la capa de service. Ahora todo pasa por AuthService.
    auth_service = AuthService(db)
    payload = auth_service.decode_token(token)

    if payload is None:
        # Token inválido, expirado o con firma incorrecta.
        # NO se expone el contenido del token en el mensaje de error
        # (antes se hacía con get_unverified_claims para debug, pero
        # eso filtraba claims del token al cliente — riesgo de info leak).
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado. Envía: Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # "sub" = subject = ID del usuario dentro del JWT
    usuario_id = int(payload.get("sub"))
    usuario = auth_service.get_user_by_id(usuario_id)

    if not usuario or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )

    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "rol": usuario.rol,
        "activo": usuario.activo,
        "created_at": usuario.created_at,
    }


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    DEPENDENCY: Verifica que el usuario autenticado sea ADMIN.

    Se encadena con get_current_user:
      1. Primero se valida el token (get_current_user)
      2. Luego se verifica el rol (require_admin)

    Si el rol no es "admin" → retorna 403 (Forbidden)

    Uso:
        @router.get("/admin/usuarios")
        def listar_usuarios(admin: dict = Depends(require_admin)):
            ...  # Solo llegan admins aquí
    """
    if current_user["rol"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador",
        )
    return current_user
