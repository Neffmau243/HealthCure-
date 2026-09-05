"""
catalogo_service.py — SERVICE: CATÁLOGOS PARA EL MÉDICO

Este servicio da al doctor/enfermera las OPCIONES disponibles para
llenar sus formularios (dropdowns del frontend):
  - GET distritos activos
  - GET localidades activas de un distrito

Los catálogos los gestiona el admin (crear/editar/desactivar en
AdminService) — el doctor solo los LEE.

¿Por qué separado de AdminService?
Porque son dos responsabilidades distintas:
  - AdminService  → escribe en los catálogos (solo admin)
  - CatalogoService → lee los catálogos (cualquier usuario autenticado)
"""
from sqlalchemy.orm import Session
from app.repositories.distrito_repository import DistritoRepository
from app.repositories.localidad_repository import LocalidadRepository
from app.schemas.catalogo import DistritoResponse, LocalidadResponse


class CatalogoService:
    """
    Service de catálogos (lectura para el doctor).
    """

    def __init__(self, db: Session):
        self.distrito_repo = DistritoRepository(db)
        self.localidad_repo = LocalidadRepository(db)

    def list_distritos(self) -> list[DistritoResponse]:
        """
        Retorna los distritos ACTIVOS, ordenados alfabéticamente.
        El frontend los muestra en un dropdown al registrar un paciente.

        Los distritos desactivados por el admin NO aparecen aquí.
        """
        distritos = self.distrito_repo.list_activos()
        return [DistritoResponse.model_validate(d) for d in distritos]

    def list_localidades(self, distrito_id: int | None = None) -> list[LocalidadResponse]:
        """
        Retorna las localidades ACTIVAS.

        - Con distrito_id: solo las de ESE distrito (dropdown encadenado:
          el doctor elige distrito → se cargan sus localidades)
        - Sin distrito_id: todas las activas

        Si el distrito no existe, retorna lista vacía (sin error).
        """
        if distrito_id is not None:
            localidades = self.localidad_repo.list_by_distrito(distrito_id, solo_activas=True)
        else:
            localidades = [
                l for l in self.localidad_repo.list_all()
                if l.activo and (l.distrito is not None and l.distrito.activo)
            ]
        return [LocalidadResponse.model_validate(l) for l in localidades]