"""
catalogos.py — ENDPOINTS DE CATÁLOGOS (OPCIONES PARA EL MÉDICO)

Rutas:
  GET /api/v1/catalogos/distritos     → Distritos ACTIVOS (dropdown)
  GET /api/v1/catalogos/localidades   → Localidades ACTIVAS (dropdown)

Estos endpoints NO permiten crear/editar catálogos — el doctor solo
LEE las opciones que el admin ya registró. El CRUD de catálogos vive
en /api/v1/admin/* (solo accesible con rol admin).

Autenticación: requiere token JWT (cualquier rol autenticado).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.catalogo_service import CatalogoService
from app.schemas.catalogo import DistritoResponse, LocalidadResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/catalogos", tags=["Catálogos"])


@router.get("/distritos", response_model=list[DistritoResponse])
def list_distritos(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Retorna los DISTRITOS ACTIVOS, ordenados alfabéticamente.

    Uso: el frontend carga aquí el dropdown "Distrito" del formulario
    de registro de paciente. Los distritos desactivados por el admin
    no aparecen.

    Ejemplo: GET /api/v1/catalogos/distritos
    """
    service = CatalogoService(db)
    return service.list_distritos()


@router.get("/localidades", response_model=list[LocalidadResponse])
def list_localidades(
    distrito_id: int | None = None,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Retorna las LOCALIDADES ACTIVAS.

    Query param opcional:
      - distrito_id=1 → solo las localidades de ESE distrito
        (dropdown encadenado: primero eliges distrito, luego localidad)
      - sin parámetro → todas las localidades activas

    Ejemplos:
      GET /api/v1/catalogos/localidades
      GET /api/v1/catalogos/localidades?distrito_id=1
    """
    service = CatalogoService(db)
    return service.list_localidades(distrito_id=distrito_id)