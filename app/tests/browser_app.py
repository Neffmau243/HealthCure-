"""Servidor E2E descartable: python -m app.tests.browser_app

Solo SQLite en memoria y pacientes ficticios. Nunca ejecuta el seed de MySQL.
Acceso local: http://127.0.0.1:8765 · e2e@example.com / e2e-password
"""
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI
from sqlalchemy import BigInteger, Integer, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from main import SPAStaticFiles, FRONTEND_DIST
from app.api.v1 import auth, pacientes, evaluaciones, atenciones, admin, catalogos, clinica
from app.core.database import Base, get_db
from app.models.paciente import Paciente
from app.models.usuario import Usuario
from app.services.auth_service import pwd_context

# Memoria compartida con una conexión por petición: el navegador envía varios
# GET simultáneos y no deben usar el mismo cursor/conexión de StaticPool.
engine = create_engine("sqlite:///file:healthcure_browser_e2e?mode=memory&cache=shared&uri=true",
                       connect_args={"check_same_thread": False}, poolclass=QueuePool)
for table in Base.metadata.sorted_tables:
    for column in table.columns:
        if isinstance(column.type, BigInteger):
            column.type = Integer()
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine, autoflush=False)


def test_db():
    with Session() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise


@asynccontextmanager
async def lifespan(app):
    yield
    engine.dispose()


app = FastAPI(lifespan=lifespan)
app.dependency_overrides[get_db] = test_db
for router in [auth.router, pacientes.router, evaluaciones.router, atenciones.router, admin.router, catalogos.router, clinica.router]:
    app.include_router(router, prefix="/api/v1")
app.mount("/", SPAStaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

with Session() as db:
    user = Usuario(nombre="Profesional de prueba E2E", email="e2e@example.com", password_hash=pwd_context.hash("e2e-password"), rol="admin", activo=True)
    db.add(user)
    db.flush()
    for documento, nombre, edad, sexo in [("E2E-10001", "Lucía Materna", 30, "F"), ("E2E-10002", "Diego Infantil", 10, "M"), ("E2E-10003", "Rosa Mayor", 72, "F")]:
        db.add(Paciente(tipo_documento="DNI", documento_identidad=documento,
                        apellido_paterno="Prueba", nombres=nombre,
                        fecha_nacimiento=date(date.today().year - edad, 1, 1), sexo=sexo,
                        tipo_seguro="SIS", activo=True, usuario_creador_id=user.id))
    db.commit()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
