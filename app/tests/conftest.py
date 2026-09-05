"""
conftest.py — FIXTURES COMPARTIDAS DE PYTEST

Permite correr los tests SIN depender de MySQL: cada test levanta una
base SQLite EN MEMORIA, registra los mismos modelos ORM (tablas idénticas
al esquema de MySQL) y sobreescribe la dependencia get_db de FastAPI para
apuntar a SQLite.

Así los tests de permisos, mapper y preprocessor corren en cualquier
máquina sin servidor MySQL levantado.

Uso:
    python -m pytest app/tests -v
"""
import pytest
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, BigInteger, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from passlib.context import CryptContext

# Alias para no chocar con el paquete `app` al hacer `import app.models`
from main import app as fastapi_app
from app.core.database import get_db, Base
import app.models  # noqa: F401  (importa TODOS los modelos al registro)
from app.models.usuario import Usuario
from app.models.paciente import Paciente
from app.services.auth_service import AuthService

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TestEnv:
    """Contenedor con lo que cada test necesita: client HTTP + sesiones."""

    def __init__(self, client: TestClient, session_factory):
        self.client = client
        self.session_factory = session_factory

    # --- Helpers ---

    def new_session(self):
        """Abre una sesión nueva contra la BD SQLite en memoria."""
        return self.session_factory()

    def create_usuario(self, nombre: str, email: str, password: str, rol: str) -> Usuario:
        """Crea un usuario directo en BD (sin pasar por la API)."""
        db = self.new_session()
        try:
            u = Usuario(
                nombre=nombre,
                email=email,
                password_hash=pwd_context.hash(password),
                rol=rol,
                activo=True,
            )
            db.add(u)
            db.commit()
            db.refresh(u)
            return u
        finally:
            db.close()

    def create_paciente(
        self,
        documento: str,
        usuario_creador_id: int | None = None,
        nombre: str = "Paciente",
    ) -> Paciente:
        """Crea un paciente directo en BD (sin pasar por la API)."""
        db = self.new_session()
        try:
            p = Paciente(
                tipo_documento="DNI",
                documento_identidad=documento,
                apellido_paterno="Apellido",
                apellido_materno="Materno",
                nombres=nombre,
                fecha_nacimiento=date(1980, 1, 1),
                sexo="M",
                tipo_seguro="SIS",
                activo=True,
                usuario_creador_id=usuario_creador_id,
            )
            db.add(p)
            db.commit()
            db.refresh(p)
            return p
        finally:
            db.close()

    def token(self, usuario_id: int, rol: str) -> str:
        """Genera un JWT válido SIN pasar por login (rápido para tests)."""
        # create_token no toca la BD: solo codifica el payload
        auth = AuthService(db=None)
        return auth.create_token(usuario_id, rol)

    def auth_header(self, usuario_id: int, rol: str) -> dict:
        return {"Authorization": f"Bearer {self.token(usuario_id, rol)}"}


@pytest.fixture()
def env():
    """
    Crea por cada test:
      - Un engine SQLite en memoria (StaticPool = una sola conexión)
      - Las tablas del esquema real (Base.metadata.create_all)
      - Un TestClient de FastAPI con get_db apuntando a SQLite
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Comparte UNA conexión → la BD "vive" durante el test
    )

    # SQLite solo autoincrementa columnas INTEGER PRIMARY KEY (alias de rowid),
    # no BIGINT (que es lo que usan los modelos para MySQL). Para los tests
    # mapeamos los BigInteger a Integer sobre el metadata antes de crear tablas.
    for table in Base.metadata.sorted_tables:
        for column in table.columns:
            if isinstance(column.type, BigInteger):
                column.type = Integer()

    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(engine)

    # get_db original hace commit al final y rollback si hay excepción.
    # La réplica exacta evita que los endpoints queden sin commitear.
    def override_get_db():
        db = TestingSession()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    # sin context manager → NO corre lifespan (evita el seed/MySQL)
    client = TestClient(fastapi_app)
    test_env = TestEnv(client, TestingSession)

    yield test_env

    fastapi_app.dependency_overrides.pop(get_db, None)
    client.close()
    engine.dispose()


@pytest.fixture()
def usuarios_base(env: TestEnv):
    """
    Crea los 3 usuarios tipo del seed + 3 pacientes con distintos creadores:
      - admin (id devuelto)          → administrador
      - doctor                       → registró al paciente_doctor
      - enfermera                    → registró a la paciente_enfermera
      - paciente_legacy              → sin creador (datos viejos)
    Retorna dict con las instancias para usar en asserts.
    """
    admin = env.create_usuario("Admin Test", "admin@test.com", "admin123", "admin")
    doctor = env.create_usuario("Dr. Test", "doctor@test.com", "doctor123", "usuario")
    enfermera = env.create_usuario("Enf. Test", "enfermera@test.com", "enfermera123", "usuario")

    paciente_doctor = env.create_paciente("11111111", usuario_creador_id=doctor.id, nombre="Juan")
    paciente_enfermera = env.create_paciente("22222222", usuario_creador_id=enfermera.id, nombre="Maria")
    paciente_legacy = env.create_paciente("33333333", usuario_creador_id=None, nombre="Legacy")

    return {
        "admin": admin,
        "doctor": doctor,
        "enfermera": enfermera,
        "paciente_doctor": paciente_doctor,
        "paciente_enfermera": paciente_enfermera,
        "paciente_legacy": paciente_legacy,
    }
