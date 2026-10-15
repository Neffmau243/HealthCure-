"""Añade solo las columnas nuevas; no cambia ni recalcula evaluaciones históricas.

Uso desde la raíz: python scripts/aplicar_migracion_003.py
Puede repetirse: las columnas existentes se conservan.
"""
from pathlib import Path
import sys

from sqlalchemy import inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import engine  # noqa: E402


def aplicar(bind):
    columnas = {c["name"] for c in inspect(bind).get_columns("evaluaciones")}
    nuevas = {
        "estado_diabetes": "VARCHAR(20) NULL",
        "presion_sistolica": "SMALLINT NULL",
        "presion_diastolica": "SMALLINT NULL",
    }
    with bind.begin() as conexion:
        for nombre, tipo in nuevas.items():
            if nombre not in columnas:
                conexion.execute(text(f"ALTER TABLE evaluaciones ADD COLUMN {nombre} {tipo}"))
                print(f"[OK] Columna agregada: {nombre}")
    print("[OK] Migración 003 lista. Historial conservado.")


if __name__ == "__main__":
    aplicar(engine)
