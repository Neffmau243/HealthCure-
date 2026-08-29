"""
__init__.py de models — IMPORTA TODOS LOS MODELOS

Este archivo es OBLIGATORIO para que:
  1. Alembic (migraciones) pueda detectar los modelos automáticamente
  2. Python reconozca app/models/ como un paquete importable
  3. Se puedan hacer imports como: from app.models import Usuario

Si no existiera este archivo, Alembic no encontraría las tablas
y las migraciones no funcionarían.
"""
from app.models.usuario import Usuario
from app.models.paciente import Paciente
from app.models.evaluacion import Evaluacion

__all__ = ["Usuario", "Paciente", "Evaluacion"]
