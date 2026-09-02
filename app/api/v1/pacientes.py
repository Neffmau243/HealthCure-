"""
pacientes.py — ENDPOINTS DE PACIENTES (CRUD)

Rutas:
  GET    /api/v1/pacientes/                    → Listar todos los pacientes
  GET    /api/v1/pacientes/search              → Buscar por documento (autocomplete)
  GET    /api/v1/pacientes/by-documento/{doc}  → Obtener por documento exacto
  GET    /api/v1/pacientes/{id}                → Obtener un paciente por ID
  POST   /api/v1/pacientes/                    → Registrar un paciente nuevo
  PUT    /api/v1/pacientes/{id}                → Actualizar datos de un paciente

⚠️ ORDEN DE RUTAS IMPORTANTE:
  FastAPI procesa rutas en orden. Las rutas ESTÁTICAS (/search, /by-documento)
  deben ir ANTES de las dinámicas (/{id}), sino FastAPI interpreta
  "search" o "by-documento" como un paciente_id y la ruta estática nunca se alcanza.

Autenticación: TODOS requieren token JWT válido.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.paciente_service import PacienteService
from app.schemas.paciente import (
    PacienteCreate, PacienteUpdate, PacienteResponse
)
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/pacientes", tags=["Pacientes"])


@router.get("/", response_model=list[PacienteResponse])
def list_pacientes(db: Session = Depends(get_db), _user: dict = Depends(get_current_user)):
    """
    Listar TODOS los pacientes registrados.
    Usado por el frontend para mostrar la tabla de pacientes.
    """
    service = PacienteService(db)
    return service.list_all()


# ⚠️ RUTAS ESTÁTICAS ANTES DE LAS DINÁMICAS
# /search y /by-documento DEBEN ir ANTES de /{paciente_id}
# Si no, FastAPI interpreta "search" como un ID y nunca llega aquí.

@router.get("/search", response_model=list[PacienteResponse])
def search_pacientes(
    documento: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Búsqueda parcial de pacientes por documento (autocomplete).

    Query param: documento=1234
    Retorna: hasta 10 pacientes cuyo documento contenga "1234"

    Ejemplo: GET /api/v1/pacientes/search?documento=1234
    """
    service = PacienteService(db)
    return service.search(documento)


@router.get("/by-documento/{documento}", response_model=PacienteResponse)
def get_paciente_by_documento(
    documento: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Obtener un paciente por documento EXACTO (no parcial).
    Retorna 404 si no existe.
    """
    service = PacienteService(db)
    paciente = service.get_by_documento(documento)
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    return paciente


@router.get("/{paciente_id}", response_model=PacienteResponse)
def get_paciente(
    paciente_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Obtener un paciente por su ID.
    Retorna 404 si no existe.
    """
    service = PacienteService(db)
    paciente = service.get_by_id(paciente_id)
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    return paciente


@router.post("/", response_model=PacienteResponse, status_code=status.HTTP_201_CREATED)
def create_paciente(
    data: PacienteCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Registrar un paciente nuevo.

    Body JSON:
      {
        "nombre": "María López",
        "documento_identidad": "1234567890",
        "fecha_nacimiento": "1985-03-15",
        "sexo": "F",
        "talla_cm": 165.5,
        "peso_kg": 70.2
      }

    Retorna 201 con los datos del paciente creado.
    Retorna 409 si ya existe un paciente con ese documento.
    """
    service = PacienteService(db)
    try:
        return service.create(data, usuario_creador_id=user["id"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.put("/{paciente_id}", response_model=PacienteResponse)
def update_paciente(
    paciente_id: int,
    data: PacienteUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Actualizar datos de un paciente existente.
    Solo se actualizan los campos que se envíen en el body.

    PERMISOS:
      - Admin: puede editar cualquier paciente
      - Médico/Enfermera: solo puede editar pacientes que EL registró

    Body JSON (ejemplo — solo actualizar talla):
      {"talla_cm": 166.0}

    Retorna 200 con los datos actualizados.
    Retorna 403 si no tiene permiso.
    Retorna 404 si el paciente no existe.
    """
    service = PacienteService(db)

    # Verificar que el paciente exista
    paciente = service.get_by_id_raw(paciente_id)
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    # Verificar permisos: admin puede todo, medico solo lo que creo
    if user["rol"] != "admin":
        if paciente.usuario_creador_id is not None and paciente.usuario_creador_id != user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para editar este paciente. Solo el usuario que lo registro puede modificarlo."
            )

    resultado = service.update(paciente_id, data)
    return resultado
