"""Aplica la migración 003 sin duplicar columnas ni modificar registros antiguos.

Ejecutar desde la raíz: python -m scripts.migrar_contexto_atencion
"""
from sqlalchemy import create_engine, inspect, text
from app.core.config import get_settings

COLUMNAS = {
    "tipo_atencion": "VARCHAR(20) NULL",
    "grupo_etario": "VARCHAR(20) NULL",
    "condicion_materna": "VARCHAR(20) NULL",
    "edad_al_atender": "SMALLINT NULL",
}


def migrar(engine):
    with engine.begin() as conexion:
        existentes = {c["name"] for c in inspect(conexion).get_columns("atenciones")}
        for nombre, tipo in COLUMNAS.items():
            if nombre not in existentes:
                conexion.execute(text(f"ALTER TABLE atenciones ADD COLUMN {nombre} {tipo}"))
                print(f"Columna añadida: {nombre}")
    print("Migración 003 lista. Los registros previos conservan NULL en los campos nuevos.")


if __name__ == "__main__":
    motor = create_engine(get_settings().DATABASE_URL, echo=False)
    try:
        migrar(motor)
    finally:
        motor.dispose()
