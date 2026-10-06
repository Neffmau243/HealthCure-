"""
atenciones.py — ENDPOINTS DE ATENCIONES DEL CONSULTORIO

Rutas:
  POST /api/v1/atenciones/                    → Registrar atención (diagnóstico/tratamiento)
  GET  /api/v1/atenciones/                    → Listar todas (paginado)
  GET  /api/v1/atenciones/by-paciente/{id}    → Historial de atenciones de un paciente
  GET  /api/v1/atenciones/{id}                → Ver una atención

⚠️ ORDEN DE RUTAS IMPORTANTE:
  La ruta estática /by-paciente debe ir ANTES de la dinámica /{atencion_id},
  sino FastAPI interpreta "by-paciente" como un ID.

Autenticación: TODOS requieren token JWT válido.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.atencion_service import AtencionService
from app.schemas.atencion import AtencionCreate, AtencionResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/atenciones", tags=["Atenciones"])


@router.post("/", response_model=AtencionResponse, status_code=status.HTTP_201_CREATED)
def create_atencion(
    data: AtencionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    REGISTRAR UNA ATENCIÓN (ACTO MÉDICO)

    Guarda el diagnóstico, tratamiento e indicaciones de una consulta,
    dejando trazabilidad de qué profesional la registró.

    Body JSON:
      {
        "paciente_id": 1,
        "evaluacion_id": 8,
        "diagnostico": "HTA no controlada + dislipidemia mixta.",
        "tratamiento": "Losartán 50mg cada 12h por 30 días.",
        "indicaciones": "Dieta hiposódica y control en 15 días."
      }

    Retorna 201 con la atención creada.
    Retorna 400 si el paciente o la evaluación no existen / no coinciden.
    """
    service = AtencionService(db)
    try:
        return service.create(data, current_user["id"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=list[AtencionResponse])
def list_atenciones(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Listar atenciones paginadas (todas, de todos los pacientes).

    Query params:
      - limit: cuántas retornar (default 50)
      - offset: cuántas saltar (paginación)

    Ejemplo: GET /api/v1/atenciones/?limit=10&offset=20
    """
    service = AtencionService(db)
    return service.list_all(limit=limit, offset=offset)


# ⚠️ RUTA ESTÁTICA ANTES DE LA DINÁMICA (/{atencion_id})
@router.get("/by-paciente/{paciente_id}", response_model=list[AtencionResponse])
def get_atenciones_by_paciente(
    paciente_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Historial de atenciones de un paciente (más reciente primero).
    """
    service = AtencionService(db)
    return service.get_by_paciente(paciente_id)


@router.get("/{atencion_id}", response_model=AtencionResponse)
def get_atencion(
    atencion_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Obtener una atención por su ID.
    Retorna 404 si no existe.
    """
    service = AtencionService(db)
    atencion = service.get_by_id(atencion_id)
    if not atencion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atención no encontrada",
        )
    return atencion
