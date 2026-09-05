"""
admin.py — ENDPOINTS DE ADMINISTRACIÓN (CRUD de Usuarios)

Solo los usuarios con rol "admin" pueden acceder a estas rutas.
Si un usuario normal intenta acceder → retorna 403 Forbidden.

Rutas — Usuarios:
  GET    /api/v1/admin/usuarios                    → Listar todos los usuarios
  GET    /api/v1/admin/usuarios/{id}               → Obtener usuario por ID
  POST   /api/v1/admin/usuarios                    → Crear usuario (admin elige rol)
  PUT    /api/v1/admin/usuarios/{id}               → Actualizar usuario (parcial)
  PUT    /api/v1/admin/usuarios/{id}/activate      → Reactivar usuario
  PUT    /api/v1/admin/usuarios/{id}/deactivate    → Desactivar usuario (soft delete)

Rutas — Catálogos (distritos/localidades):
  GET    /api/v1/admin/distritos                           → Listar todos
  POST   /api/v1/admin/distritos                           → Crear
  PUT    /api/v1/admin/distritos/{id}                      → Actualizar (nombre/activo)
  PUT    /api/v1/admin/distritos/{id}/deactivate           → Desactivar
  GET    /api/v1/admin/localidades                         → Listar (filtro ?distrito_id=)
  POST   /api/v1/admin/localidades                         → Crear
  PUT    /api/v1/admin/localidades/{id}                    → Actualizar (nombre/distrito/activo)
  PUT    /api/v1/admin/localidades/{id}/deactivate         → Desactivar

Autenticación: Requiere token JWT + rol "admin".

Nota de seguridad:
  - El registro Púbrico (/auth/register) SIEMPRE crea usuarios como "usuario"
  - Solo desde AQUÍ un admin puede crear otros admins o cambiar roles
  - El admin también gestiona los catálogos de distritos/localidades que
    el médico usa como dropdowns (ver /api/v1/catalogos/*)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.admin_service import AdminService
from app.schemas.usuario import UsuarioResponse, UsuarioUpdate, UsuarioAdminCreate
from app.schemas.catalogo import (
    DistritoCreate, DistritoUpdate, DistritoResponse,
    LocalidadCreate, LocalidadUpdate, LocalidadResponse,
)
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
    admin: dict = Depends(require_admin),
):
    """
    Actualizar un usuario existente (update parcial).
    Solo los campos enviados se actualizan.

    El admin puede cambiar: nombre, email, password, rol, activo.

    SEGURIDAD:
      - No puedes quitarte el rol admin ni desactivar tu propia cuenta
      - No puedes degradar/desactivar al ÚLTIMO admin activo

    Retorna 404 si no existe, 409 si el email ya esta en uso
    o la acción viola una regla de seguridad.
    """
    service = AdminService(db)
    try:
        usuario = service.update_usuario(
            usuario_id, data, current_admin_id=admin["id"]
        )
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


@router.put("/usuarios/{usuario_id}/deactivate", response_model=UsuarioResponse)
def deactivate_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    """
    Desactivar un usuario (soft delete).
    El usuario no se borra físicamente, solo se marca como inactivo.

    Un usuario desactivado:
      - NO puede hacer login
      - Sigue existiendo en la BD (para auditoría)
      - Sus evaluaciones siguen intactas

    SEGURIDAD:
      - No puedes desactivar tu propia cuenta
      - No puedes desactivar al ÚLTIMO admin activo

    Retorna 200 con el usuario desactivado.
    Retorna 404 si el usuario no existe, 409 si viola una regla de seguridad.
    """
    service = AdminService(db)
    try:
        usuario = service.deactivate_usuario(
            usuario_id, current_admin_id=admin["id"]
        )
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


# ============================================================
# CATÁLOGOS: DISTRITOS
# ============================================================

@router.get("/distritos", response_model=list[DistritoResponse])
def list_distritos_admin(
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """
    Listar TODOS los distritos (activos e inactivos).
    Solo accesible por administradores.

    El doctor ve solo los ACTIVOS via GET /api/v1/catalogos/distritos.
    """
    service = AdminService(db)
    return service.list_distritos()


@router.post("/distritos", response_model=DistritoResponse, status_code=status.HTTP_201_CREATED)
def create_distrito(
    data: DistritoCreate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """
    Crear un distrito nuevo (catálogo).

    Body JSON:
      {"nombre": "Alto Selva Alegre"}

    Retorna 201 con el distrito creado.
    Retorna 409 si ya existe un distrito con ese nombre.
    """
    service = AdminService(db)
    try:
        return service.create_distrito(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.put("/distritos/{distrito_id}", response_model=DistritoResponse)
def update_distrito(
    distrito_id: int,
    data: DistritoUpdate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """
    Actualizar un distrito (parcial). El admin puede cambiar el nombre
    o activarlo/desactivarlo.

    Body JSON (ejemplo):
      {"nombre": "Alto Selva Alegre Norte", "activo": true}

    Retorna 404 si no existe, 409 si el nombre ya esta en uso.
    """
    service = AdminService(db)
    try:
        distrito = service.update_distrito(distrito_id, data)
        if not distrito:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Distrito no encontrado"
            )
        return distrito
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.put("/distritos/{distrito_id}/deactivate", response_model=DistritoResponse)
def deactivate_distrito(
    distrito_id: int,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """
    Desactivar un distrito (soft delete).
    Ya no aparece en el dropdown del doctor, pero sus datos siguen en la BD.

    Retorna 404 si no existe.
    """
    service = AdminService(db)
    distrito = service.deactivate_distrito(distrito_id)
    if not distrito:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Distrito no encontrado"
        )
    return distrito


# ============================================================
# CATÁLOGOS: LOCALIDADES
# ============================================================

@router.get("/localidades", response_model=list[LocalidadResponse])
def list_localidades_admin(
    distrito_id: int | None = None,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """
    Listar localidades (activas e inactivas).
    Filtro opcional: ?distrito_id=1 → solo las de ese distrito.
    """
    service = AdminService(db)
    return service.list_localidades(distrito_id=distrito_id)


@router.post("/localidades", response_model=LocalidadResponse, status_code=status.HTTP_201_CREATED)
def create_localidad(
    data: LocalidadCreate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """
    Crear una localidad dentro de un distrito.

    Body JSON:
      {"nombre": "Chilpinilla", "distrito_id": 1}

    Retorna 201 con la localidad creada.
    Retorna 409 si el distrito no existe o la localidad ya esta en ese distrito.
    """
    service = AdminService(db)
    try:
        return service.create_localidad(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.put("/localidades/{localidad_id}", response_model=LocalidadResponse)
def update_localidad(
    localidad_id: int,
    data: LocalidadUpdate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """
    Actualizar una localidad (parcial): nombre, distrito y/o activo.

    Retorna 404 si no existe, 409 si hay conflicto (distrito inexistente
    o nombre duplicado en el distrito).
    """
    service = AdminService(db)
    try:
        localidad = service.update_localidad(localidad_id, data)
        if not localidad:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Localidad no encontrada"
            )
        return localidad
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.put("/localidades/{localidad_id}/deactivate", response_model=LocalidadResponse)
def deactivate_localidad(
    localidad_id: int,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """
    Desactivar una localidad (soft delete).
    Ya no aparece en el dropdown del doctor.

    Retorna 404 si no existe.
    """
    service = AdminService(db)
    localidad = service.deactivate_localidad(localidad_id)
    if not localidad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Localidad no encontrada"
        )
    return localidad
