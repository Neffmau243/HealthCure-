"""
paciente_repository.py — REPOSITORY: OPERACIONES DE BD PARA PACIENTES

Maneja toda la persistencia de datos administrativos del paciente.
El repository es la ÚNICA capa que hace queries a MySQL.
"""
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from app.models.paciente import Paciente


class PacienteRepository:
    """
    Repository de pacientes. Maneja CRUD (Create, Read, Update, Delete).
    """

    def __init__(self, db: Session):
        self.db = db

    def _query_con_catalogos(self):
        """
        Query base con joinedload de distrito y localidad.
        Así las respuestas traen el NOMBRE del distrito/localidad
        (ej: "Alto Selva Alegre") sin queries extra (evita N+1).
        """
        return self.db.query(Paciente).options(
            joinedload(Paciente.distrito),
            joinedload(Paciente.localidad),
        )

    def get_by_id(self, paciente_id: int) -> Optional[Paciente]:
        """Busca paciente por ID primario (incluye catálogos)."""
        return (
            self._query_con_catalogos()
            .filter(Paciente.id == paciente_id)
            .first()
        )

    def get_by_documento(self, documento: str) -> Optional[Paciente]:
        """
        Busca paciente EXACTO por documento de identidad.
        Retorna None si no existe — usado para validar duplicados.
        """
        return (
            self._query_con_catalogos()
            .filter(Paciente.documento_identidad == documento)
            .first()
        )

    def get_by_historia_clinica(self, numero: str) -> Optional[Paciente]:
        """
        Busca paciente EXACTO por número de historia clínica.
        Retorna None si no existe — usado para validar duplicados.
        """
        return (
            self._query_con_catalogos()
            .filter(Paciente.numero_historia_clinica == numero)
            .first()
        )

    def search_by_documento(self, documento: str) -> list[Paciente]:
        """
        Búsqueda parcial de pacientes por documento (LIKE %...%).
        Retorna hasta 10 resultados — usado para el autocomplete del frontend.

        Ejemplo: search_by_documento("1234") busca documentos que contengan "1234"
        """
        return (
            self._query_con_catalogos()
            .filter(Paciente.documento_identidad.like(f"%{documento}%"))
            .limit(10)  # Máximo 10 resultados para no sobrecargar
            .all()
        )

    def list_all(self) -> list[Paciente]:
        """
        Retorna TODOS los pacientes registrados, ordenados por ID.
        Usado por el endpoint GET /api/v1/pacientes/.
        """
        return (
            self._query_con_catalogos()
            .order_by(Paciente.id)
            .all()
        )

    def create(self, usuario_creador_id: int = None, **kwargs) -> Paciente:
        """
        Crea un paciente nuevo.
        **kwargs permite pasar todos los campos como parámetros nombrados.
        usuario_creador_id: ID del usuario que registra al paciente.

        Ejemplo:
            repo.create(
                usuario_creador_id=1,
                tipo_documento="DNI",
                documento_identidad="1032456789",
                apellido_paterno="Pérez",
                apellido_materno="Rodríguez",
                nombres="Juan",
                fecha_nacimiento=date(1965, 5, 20),
                sexo="M",
                distrito_id=1
            )
        """
        paciente = Paciente(usuario_creador_id=usuario_creador_id, **kwargs)
        # Crea el objeto ORM con los campos + quién lo registró
        self.db.add(paciente)          # Agrega a la sesión
        self.db.flush()                # Genera el ID sin commitear
        return paciente

    def update(self, paciente: Paciente, **kwargs) -> Paciente:
        """
        Actualiza campos específicos de un paciente existente.
        Aplica TODOS los kwargs, incluidos None (para LIMPIAR un campo
        opcional como telefono, direccion o numero_historia_clinica).

        El Service ya filtra con exclude_unset=True qué campos se enviaron,
        así que aquí no hace falta ignorar Nones — un None explícito
        significa "el usuario quiere borrar este valor".

        Ejemplo:
            repo.update(paciente_existente, talla_cm=170.0, telefono=None)
        """
        for key, value in kwargs.items():
            if hasattr(paciente, key):
                setattr(paciente, key, value)
        self.db.flush()  # Marca el cambio en la sesión
        return paciente