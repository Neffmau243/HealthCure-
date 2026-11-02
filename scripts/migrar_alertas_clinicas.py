"""Migración aditiva e idempotente: python -m scripts.migrar_alertas_clinicas."""
from sqlalchemy import create_engine, inspect, text
from app.core.config import get_settings


def migrar(engine):
    with engine.begin() as db:
        for tabla in ("evaluaciones", "atenciones"):
            existentes = {c["name"] for c in inspect(db).get_columns(tabla)}
            for campo in ("observaciones_clinicas", "alerta_clinica"):
                if campo not in existentes:
                    db.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {campo} JSON NULL"))
                    print(f"Añadida {tabla}.{campo}")
    print("Migración 004 lista; registros previos sin cambios.")


if __name__ == "__main__":
    engine = create_engine(get_settings().DATABASE_URL, echo=False)
    try:
        migrar(engine)
    finally:
        engine.dispose()
