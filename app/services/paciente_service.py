"""
paciente_service.py — SERVICE: LÓGICA DE NEGOCIO PARA PACIENTES

El Service es la capa que orquesta la lógica de negocio.
Conecta los Repositories (acceso a BD) con los Schemas (validación)
sin que unos sepan de los otros.

RESPONSABILIDADES:
  - Validar que no se dupliquen pacientes (por documento)
  - Convertir entre schemas DTO y ORM usando model_validate
  - Manejar la lógica de actualización parcial
"""
from sqlalchemy.orm import Session
from typing import Optional
from app.repositories.paciente_repository import PacienteRepository
from app.schemas.paciente import (
    PacienteCreate, PacienteUpdate, PacienteResponse
)


class PacienteService:
    """
    Service de pacientes. Orquesta repositories y schemas.
    """

    def __init__(self, db: Session):
        self.repo = PacienteRepository(db)

    # --- READ OPERATIONS ---

    def get_by_id(self, paciente_id: int) -> Optional[PacienteResponse]:
        """Busca paciente por ID y retorna el DTO de respuesta."""
        paciente = self.repo.get_by_id(paciente_id)
        if not paciente:
            return None
        return PacienteResponse.model_validate(paciente)
        # model_validate convierte el ORM → Pydantic DTO automáticamente

    def get_by_documento(self, documento: str) -> Optional[PacienteResponse]:
        """Busca paciente exacto por documento de identidad."""
        paciente = self.repo.get_by_documento(documento)
        if not paciente:
            return None
        return PacienteResponse.model_validate(paciente)

    def search(self, documento: str) -> list[PacienteResponse]:
        """Búsqueda parcial de pacientes por documento (autocomplete)."""
        pacientes = self.repo.search_by_documento(documento)
        return [PacienteResponse.model_validate(p) for p in pacientes]

    # --- CREATE ---

    def create(self, data: PacienteCreate) -> PacienteResponse:
        """
        Registra un paciente nuevo.
        1. Verifica que no exista otro con el mismo documento
        2. Crea el paciente en la BD
        3. Retorna los datos del paciente creado
        """
        if self.repo.get_by_documento(data.documento_identidad):
            raise ValueError("Ya existe un paciente con ese documento")

        paciente = self.repo.create(
            nombre=data.nombre,
            documento_identidad=data.documento_identidad,
            fecha_nacimiento=data.fecha_nacimiento,
            sexo=data.sexo.value,  # Enum → string ("M" o "F")
            talla_cm=data.talla_cm,
            peso_kg=data.peso_kg,
        )
        return PacienteResponse.model_validate(paciente)

    # --- LIST ---

    def list_all(self) -> list[PacienteResponse]:
        """
        Retorna todos los pacientes registrados.
        Usado por el endpoint GET /api/v1/pacientes/.
        """
        pacientes = self.repo.list_all()
        return [PacienteResponse.model_validate(p) for p in pacientes]

    # --- UPDATE ---

    def update(self, paciente_id: int, data: PacienteUpdate) -> Optional[PacienteResponse]:
        """
        Actualiza datos de un paciente existente.
        Solo actualiza los campos que se envíen (excluye_unset=True).
        """
        paciente = self.repo.get_by_id(paciente_id)
        if not paciente:
            return None

        # model_dump(exclude_unset=True) → solo campos que el usuario envió
        # Ejemplo: si solo envía {"talla_cm": 170}, solo se actualiza talla_cm
        update_data = data.model_dump(exclude_unset=True)

        # Convertir enum a string para SQLAlchemy
        if "sexo" in update_data:
            update_data["sexo"] = update_data["sexo"].value

        self.repo.update(paciente, **update_data)
        return PacienteResponse.model_validate(paciente)
