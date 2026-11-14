"""Añade el contexto administrativo actual sin modificar atenciones anteriores."""
from sqlalchemy import create_engine, inspect, text
from app.core.config import get_settings


def migrar(engine):
    with engine.begin() as conexion:
        columnas = {columna["name"] for columna in inspect(conexion).get_columns("pacientes")}
        if "contexto_atencion" not in columnas:
            conexion.execute(text("ALTER TABLE pacientes ADD COLUMN contexto_atencion JSON NULL"))
    print("Migración 005 lista. Los registros e historiales existentes se conservan.")


if __name__ == "__main__":
    motor = create_engine(get_settings().DATABASE_URL, echo=False)
    try:
        migrar(motor)
    finally:
        motor.dispose()
