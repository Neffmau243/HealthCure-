"""
localidad_repository.py — REPOSITORY: OPERACIONES DE BD PARA LOCALIDADES

Catálogo gestionado por el admin. Cada localidad pertenece a un distrito.
"""
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from app.models.localidad import Localidad


class LocalidadRepository:
    """
    Repository de localidades (catálogo admin).
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, localidad_id: int) -> Optional[Localidad]:
        """Busca una localidad por su ID (incluye su distrito)."""
        return (
            self.db.query(Localidad)
            .options(joinedload(Localidad.distrito))
            .filter(Localidad.id == localidad_id)
            .first()
        )

    def get_by_nombre(self, nombre: str, distrito_id: int) -> Optional[Localidad]:
        """
        Busca por nombre DENTRO de un distrito.
        "Chilpinilla" puede existir en varios distritos, pero no dos veces
        en el mismo → validación de duplicados por (nombre, distrito_id).
        """
        return (
            self.db.query(Localidad)
            .filter(
                Localidad.nombre == nombre,
                Localidad.distrito_id == distrito_id,
            )
            .first()
        )

    def list_all(self) -> list[Localidad]:
        """Retorna TODAS las localidades con su distrito (para el admin)."""
        return (
            self.db.query(Localidad)
            .options(joinedload(Localidad.distrito))
            .order_by(Localidad.distrito_id, Localidad.nombre)
            .all()
        )

    def list_by_distrito(self, distrito_id: int, solo_activas: bool = True) -> list[Localidad]:
        """
        Retorna las localidades de un distrito.
        - solo_activas=True → solo las activas (dropdown del doctor)
        - solo_activas=False → todas (lista del admin)
        """
        query = self.db.query(Localidad).filter(Localidad.distrito_id == distrito_id)
        if solo_activas:
            query = query.filter(Localidad.activo.is_(True))
        return query.order_by(Localidad.nombre).all()

    def create(self, nombre: str, distrito_id: int) -> Localidad:
        """Crea una localidad dentro de un distrito."""
        localidad = Localidad(nombre=nombre, distrito_id=distrito_id, activo=True)
        self.db.add(localidad)
        self.db.flush()
        return localidad

    def update(self, localidad_id: int, **kwargs) -> Optional[Localidad]:
        """Actualiza campos de una localidad. Retorna None si no existe."""
        localidad = self.get_by_id(localidad_id)
        if not localidad:
            return None
        for key, value in kwargs.items():
            if hasattr(localidad, key):
                setattr(localidad, key, value)
        self.db.flush()
        return localidad