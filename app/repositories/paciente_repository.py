"""
paciente_repository.py — REPOSITORY: OPERACIONES DE BD PARA PACIENTES

Maneja toda la persistencia de datos administrativos del paciente.
El repository es la ÚNICA capa que hace queries a MySQL.
"""
from sqlalchemy.orm import Session
from typing import Optional
from app.models.paciente import Paciente


class PacienteRepository:
    """
    Repository de pacientes. Maneja CRUD (Create, Read, Update, Delete).
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, paciente_id: int) -> Optional[Paciente]:
        """Busca paciente por ID primario."""
        return self.db.query(Paciente).filter(Paciente.id == paciente_id).first()

    def get_by_documento(self, documento: str) -> Optional[Paciente]:
        """
        Busca paciente EXACTO por documento de identidad.
        Retorna None si no existe — usado para validar duplicados.
        """
        return (
            self.db.query(Paciente)
            .filter(Paciente.documento_identidad == documento)
            .first()
        )

    def search_by_documento(self, documento: str) -> list[Paciente]:
        """
        Búsqueda parcial de pacientes por documento (LIKE %...%).
        Retorna hasta 10 resultados — usado para el autocomplete del frontend.

        Ejemplo: search_by_documento("1234") busca documentos que contengan "1234"
        """
        return (
            self.db.query(Paciente)
            .filter(Paciente.documento_identidad.like(f"%{documento}%"))
            .limit(10)  # Máximo 10 resultados para no sobrecargar
            .all()
        )

    def create(self, **kwargs) -> Paciente:
        """
        Crea un paciente nuevo.
        **kwargs permite pasar todos los campos como parámetros nombrados.

        Ejemplo:
            repo.create(
                nombre="María",
                documento_identidad="12345",
                fecha_nacimiento=date(1985, 3, 15),
                sexo="F"
            )
        """
        paciente = Paciente(**kwargs)  # Crea el objeto ORM con los campos
        self.db.add(paciente)          # Agrega a la sesión
        self.db.flush()                # Genera el ID sin commitear
        return paciente

    def update(self, paciente: Paciente, **kwargs) -> Paciente:
        """
        Actualiza campos específicos de un paciente existente.
        Solo actualiza los campos que se pasen en kwargs (los None se ignoran).

        Ejemplo:
            repo.update(paciente_existente, talla_cm=170.0, peso_kg=75.0)
        """
        for key, value in kwargs.items():
            if value is not None:  # No sobreescribir con None
                setattr(paciente, key, value)
        self.db.flush()  # Marca el cambio en la sesión
        return paciente
