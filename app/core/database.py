"""
database.py — CONEXIÓN A LA BASE DE DATOS MYSQL

Crea el engine de SQLAlchemy (pool de conexiones), la sesión de BD,
y el mecanismo Base para que los modelos ORM se registren.

La función get_db() es una dependency de FastAPI que:
  1. Abre una conexión a MySQL
  2. La entrega al endpoint que la pidió
  3. Al terminar: commit si todo salió bien, rollback si hubo error
  4. Cierra la conexión

Esto garantiza que NO se quedan conexiones abiertas y que los datos
se persisten correctamente.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import get_settings

settings = get_settings()

# Engine = pool de conexiones a MySQL. Cada petición HTTP toma una conexión del pool.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # Verifica que la conexión no esté muerta antes de usarla
    pool_size=5,           # Máximo 5 conexiones simultáneas en el pool
    max_overflow=10,       # Puede abrir hasta 10 conexiones extra si el pool se llena
    echo=settings.DEBUG,   # Si DEBUG=True, imprime cada query SQL en consola
)

# SessionLocal = fábrica de sesiones. Cada request crea una sesión nueva.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# autocommit=False → los cambios NO se guardan solos, hay que hacer commit explícito
# autoflush=False  → los cambios NO se envían a MySQL automáticamente, hay que flush

# Base = clase padre de TODOS los modelos ORM (Usuario, Paciente, Evaluacion)
Base = declarative_base()


def get_db():
    """
    DEPENDENCY de FastAPI — se inyecta con Depends(get_db) en cada endpoint.

    Flujo:
      1. Abre sesión a MySQL
      2. yield → el endpoint ejecuta su lógica
      3. Si todo OK → commit (guarda cambios)
      4. Si excepción → rollback (deshace cambios)
      5. Siempre → cierra la conexión

    Ejemplo de uso en un endpoint:
        @router.get("/algo")
        def mi_endpoint(db: Session = Depends(get_db)):
            ...  # db ya está abierta aquí
    """
    db = SessionLocal()
    try:
        yield db           # Entrega la sesión al endpoint
        db.commit()        # Si el endpoint terminó sin error → guardar todo
    except Exception:
        db.rollback()      # Si hubo error → deshacer todo lo que se hizo
        raise
    finally:
        db.close()         # Siempre cerrar la conexión, pase lo que pase
