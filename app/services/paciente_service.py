"""
paciente_service.py — SERVICE: LÓGICA DE NEGOCIO PARA PACIENTES

El Service es la capa que orquesta la lógica de negocio.
Conecta los Repositories (acceso a BD) con los Schemas (validación)
sin que unos sepan de los otros.

RESPONSABILIDADES:
  - Validar duplicados (documento, historia clínica)
  - Validar que distrito/localidad existan y sean coherentes
  - Convertir entre schemas DTO y ORM
  - Manejar la lógica de actualización parcial
  - Verificar permisos de edición (solo creador o admin)
"""
from sqlalchemy.orm import Session
from typing import Optional
from app.repositories.paciente_repository import PacienteRepository
from app.repositories.distrito_repository import DistritoRepository
from app.repositories.localidad_repository import LocalidadRepository
from app.schemas.paciente import (
    PacienteCreate, PacienteUpdate, PacienteResponse
)


class PacienteService:
    """
    Service de pacientes. Orquesta repositories y schemas.
    """

    def __init__(self, db: Session):
        self.repo = PacienteRepository(db)
        self.distrito_repo = DistritoRepository(db)
        self.localidad_repo = LocalidadRepository(db)

    # --- HELPERS ---

    def _validar_ubicacion(self, distrito_id: int, localidad_id: int):
        """
        Valida que distrito/localidad existan y sean coherentes:
          1. Si hay distrito_id → debe existir un distrito con ese ID
          2. Si hay localidad_id → debe existir y pertenecer al distrito
        Lanza ValueError si algo no cuadra (el controller lo hace 400/409).
        """
        if distrito_id is not None:
            distrito = self.distrito_repo.get_by_id(distrito_id)
            if not distrito:
                raise ValueError("El distrito seleccionado no existe")

        if localidad_id is not None:
            localidad = self.localidad_repo.get_by_id(localidad_id)
            if not localidad:
                raise ValueError("La localidad seleccionada no existe")
            # La localidad debe pertenecer al distrito elegido
            if distrito_id is not None and localidad.distrito_id != distrito_id:
                raise ValueError(
                    "La localidad no pertenece al distrito seleccionado"
                )

    # --- READ OPERATIONS ---

    def get_by_id(self, paciente_id: int) -> Optional[PacienteResponse]:
        """Busca paciente por ID y retorna el DTO de respuesta."""
        paciente = self.repo.get_by_id(paciente_id)
        if not paciente:
            return None
        return PacienteResponse.model_validate(paciente)

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

    def create(self, data: PacienteCreate, usuario_creador_id: int = None) -> PacienteResponse:
        """
        Registra un paciente nuevo.
        1. Verifica que no exista otro con el mismo documento
        2. Verifica que la historia clínica no esté en uso (si se envía)
        3. Valida distrito/localidad
        4. Crea el paciente en la BD (guarda quién lo registró)
        5. Retorna los datos del paciente creado
        """
        if self.repo.get_by_documento(data.documento_identidad):
            raise ValueError("Ya existe un paciente con ese documento")

        if data.numero_historia_clinica and self.repo.get_by_historia_clinica(
            data.numero_historia_clinica
        ):
            raise ValueError("Ya existe un paciente con ese número de historia clínica")

        self._validar_ubicacion(data.distrito_id, data.localidad_id)

        paciente = self.repo.create(
            usuario_creador_id=usuario_creador_id,
            tipo_documento=data.tipo_documento.value,
            documento_identidad=data.documento_identidad,
            numero_historia_clinica=data.numero_historia_clinica,
            apellido_paterno=data.apellido_paterno,
            apellido_materno=data.apellido_materno,
            nombres=data.nombres,
            fecha_nacimiento=data.fecha_nacimiento,
            sexo=data.sexo.value,
            telefono=data.telefono,
            direccion=data.direccion,
            distrito_id=data.distrito_id,
            localidad_id=data.localidad_id,
            tipo_seguro=data.tipo_seguro.value,
            codigo_afiliacion_seguro=data.codigo_afiliacion_seguro,
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

    def update(
        self,
        paciente_id: int,
        data: PacienteUpdate,
        current_user_id: int = None,
        current_user_rol: str = None,
    ) -> Optional[PacienteResponse]:
        """
        Actualiza datos de un paciente existente.
        Solo actualiza los campos que se envíen (excluye_unset=True).

        PERMISOS (regla de negocio, vive en el Service no en el controller):
          - Admin: puede editar CUALQUIER paciente
          - Usuario: solo pacientes que él registró (usuario_creador_id == él)
            Si el paciente no tiene creador (datos del seed/legacy), cualquiera
            puede editarlo — comportamiento por defecto para datos existentes.

        Excepciones:
          - PermissionError si el usuario no tiene permiso (→ el controller
            lo convierte en HTTP 403 Forbidden)
        """
        paciente = self.repo.get_by_id(paciente_id)
        if not paciente:
            return None

        # --- Verificación de permisos ---
        if current_user_rol != "admin":
            if (
                paciente.usuario_creador_id is not None
                and paciente.usuario_creador_id != current_user_id
            ):
                raise PermissionError(
                    "No tienes permiso para editar este paciente. "
                    "Solo el usuario que lo registro puede modificarlo."
                )

        # model_dump(exclude_unset=True) → solo campos que el usuario envió
        update_data = data.model_dump(exclude_unset=True)

        # --- Validaciones de duplicados (solo si cambian) ---
        if "numero_historia_clinica" in update_data and update_data["numero_historia_clinica"]:
            # Excluir al mismo paciente: si conserva SU número, no es duplicado
            existing = self.repo.get_by_historia_clinica(update_data["numero_historia_clinica"])
            if existing and existing.id != paciente_id:
                raise ValueError("Ya existe otro paciente con esa historia clínica")

        # --- Validación de ubicación ---
        distrito_id = update_data.get("distrito_id", paciente.distrito_id)
        localidad_id = update_data.get("localidad_id", paciente.localidad_id)
        self._validar_ubicacion(distrito_id, localidad_id)

        # --- Convertir enums a strings para SQLAlchemy ---
        for campo in ("sexo", "tipo_documento", "tipo_seguro"):
            if campo in update_data and update_data[campo] is not None:
                update_data[campo] = update_data[campo].value

        self.repo.update(paciente, **update_data)
        # Recargar para traer los catálogos actualizados en la respuesta
        paciente = self.repo.get_by_id(paciente_id)
        return PacienteResponse.model_validate(paciente)