"""Añade snapshot JSON de política; repetible, sin reescribir evaluaciones."""
import sys
from pathlib import Path
from sqlalchemy import inspect, text
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.database import engine


def aplicar(bind):
    columns = {c["name"] for c in inspect(bind).get_columns("evaluaciones")}
    if "politica_modelo" not in columns:
        with bind.begin() as connection:
            connection.execute(text("ALTER TABLE evaluaciones ADD COLUMN politica_modelo JSON NULL"))
    print("[OK] Migración 004 lista; evaluaciones históricas intactas.")


if __name__ == "__main__":
    aplicar(engine)
