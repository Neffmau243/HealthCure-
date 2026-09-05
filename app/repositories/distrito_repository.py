"""
distrito_repository.py — REPOSITORY: OPERACIONES DE BD PARA DISTRITOS

Catálogo gestionado por el admin. La ÚNICA capa que habla con MySQL.
"""
from sqlalchemy.orm import Session
from typing import Optional
from app.models.distrito import Distrito


class DistritoRepository:
    """
    Repository de distritos (catálogo admin).
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, distrito_id: int) -> Optional[Distrito]:
        """Busca un distrito por su ID. Retorna None si no existe."""
        return (
            self.db.query(Distrito)
            .filter(Distrito.id == distrito_id)
            .first()
        )

    def get_by_nombre(self, nombre: str) -> Optional[Distrito]:
        """Busca por nombre EXACTO — usado para validar duplicados."""
        return (
            self.db.query(Distrito)
            .filter(Distrito.nombre == nombre)
            .first()
        )

    def list_all(self) -> list[Distrito]:
        """Retorna TODOS los distritos (para el admin)."""
        return self.db.query(Distrito).order_by(Distrito.nombre).all()

    def list_activos(self) -> list[Distrito]:
        """
        Retorna SOLO los distritos activos, ordenados alfabéticamente.
        Usado por el doctor para llenar el dropdown del formulario.
        """
        return (
            self.db.query(Distrito)
            .filter(Distrito.activo.is_(True))
            .order_by(Distrito.nombre)
            .all()
        )

    def create(self, nombre: str) -> Distrito:
        """Crea un distrito nuevo."""
        distrito = Distrito(nombre=nombre, activo=True)
        self.db.add(distrito)
        self.db.flush()
        return distrito

    def update(self, distrito_id: int, **kwargs) -> Optional[Distrito]:
        """Actualiza campos de un distrito. Retorna None si no existe."""
        distrito = self.get_by_id(distrito_id)
        if not distrito:
            return None
        for key, value in kwargs.items():
            if hasattr(distrito, key):
                setattr(distrito, key, value)
        self.db.flush()
        return distrito