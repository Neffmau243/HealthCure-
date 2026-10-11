"""
main.py — PUNTO DE ENTRADA DE LA APLICACIÓN

Este es el archivo que ejecuta FastAPI con:
    python -m uvicorn main:app --reload --port 8000

¿Qué hace?
  1. Crea la instancia de FastAPI
  2. Configura CORS (permisos de conexión desde el frontend)
  3. Registra TODOS los endpoints (routers)
  4. Expone un endpoint de health check
  5. Sirve el frontend React compilado (frontend/dist) en el MISMO puerto

¿Por qué se usa `python -m uvicorn` y no el comando `uvicorn`?
En Windows el ejecutable `uvicorn.exe` que instala pip puede quedar bloqueado
por el Control inteligente de aplicaciones (Smart App Control), con el error
"Una directiva de Control de aplicaciones bloqueó este archivo". Invocarlo como
módulo usa el intérprete de Python (permitido) y evita el bloqueo.

Jerarquía de rutas:
    /api/v1/auth/*          → Autenticación (login, registro)
    /api/v1/pacientes/*     → CRUD de pacientes
    /api/v1/evaluaciones/*  → Evaluaciones cardíacas (ML)
    /api/v1/atenciones/*    → Atenciones del consultorio (diagnóstico/tratamiento)
    /api/v1/admin/*         → Administración (solo admins)
    /health                 → Health check (sin auth)
    /docs                   → Swagger UI (documentación interactiva)
    /redoc                  → ReDoc (documentación alternativa)
    /*                      → Interfaz React (build de frontend/dist)
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import get_settings
from app.api.v1 import auth, pacientes, evaluaciones, atenciones, admin, catalogos

settings = get_settings()


# --- LIFESPAN: ejecuta código al iniciar y apagar el servidor ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja el ciclo de vida de la aplicación:
      - Al INICIAR: ejecuta el seed de datos de prueba
      - Al CERRAR: (nada por ahora)

    Flask tiene @app.before_first_request. FastAPI usa lifespan.
    """
    # --- STARTUP ---
    from app.seeds.seed import seed_database
    seed_database()

    yield  # El servidor está corriendo aquí

    # --- SHUTDOWN ---
    # Nada que limpiar por ahora


# --- INSTANCIA DE FASTAPI ---
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema de triaje cardíaco con predicción ML — CardioPredict",
    docs_url="/docs",     # Swagger UI interactivo (para probar la API)
    redoc_url="/redoc",   # Documentación alternativa
    lifespan=lifespan,    # Seed automático al iniciar
)

# --- CORS (Cross-Origin Resource Sharing) ---
# Permite que el frontend (React) se conecte al backend (FastAPI)
# desde un navegador web. Sin esto, el navegador bloquearía las peticiones.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,  # Desde .env (CORS_ORIGINS)
    # allow_credentials solo se habilita con orígenes CONCRETOS (no "*"):
    # la spec CORS rechaza wildcard + credentials en navegadores. Como
    # autenticamos con JWT en el header Authorization (no con cookies),
    # en desarrollo con "*" las credenciales quedan apagadas.
    allow_credentials=settings.cors_origins_list != ["*"],
    allow_methods=["*"],  # Permite GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Permite cualquier header (Authorization, Content-Type, etc.)
)

# --- REGISTRO DE ENDPOINTS (Routers) ---
# Cada router maneja un grupo de rutas relacionadas.
# El prefix="/api/v1" agrega la versión de la API a todas las rutas.
app.include_router(auth.router, prefix="/api/v1")
app.include_router(pacientes.router, prefix="/api/v1")
app.include_router(evaluaciones.router, prefix="/api/v1")
app.include_router(atenciones.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(catalogos.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health_check():
    """
    Health check endpoint — verifica que el servidor esté funcionando.
    No requiere autenticación. Útil para:
      - Monitoreo de uptime
      - Load balancers
      - Docker health checks

    Retorna: {"status": "ok", "app": "HealthCure - CardioPredict", "version": "1.0.0"}
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# ---------------------------------------------------------------------------
# FRONTEND (SPA) — la interfaz se sirve desde el MISMO puerto que la API
# ---------------------------------------------------------------------------
# Un solo servidor y un solo puerto:
#     http://localhost:8000        → interfaz React
#     http://localhost:8000/api/v1 → API
#     http://localhost:8000/docs   → Swagger
#
# Se sirve el build de producción de Vite (frontend/dist). Cada vez que
# cambies algo del frontend hay que reconstruirlo:
#     cd frontend && npm run build
#
# El mount va AL FINAL a propósito: FastAPI evalúa las rutas en orden de
# registro, así que /api/v1/*, /docs y /health (definidas arriba) tienen
# prioridad y no quedan tapadas por la interfaz.
FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"


class SPAStaticFiles(StaticFiles):
    """
    StaticFiles con fallback a index.html (SPA fallback).

    React Router maneja rutas del navegador (/login, /dashboard/pacientes...).
    Si el usuario recarga la página en una de esas URLs, ese archivo no existe
    en el disco; devolvemos index.html para que React resuelva la ruta en lugar
    de mostrar un 404.
    """

    # Rutas que NO son del frontend: si no existen, deben seguir devolviendo
    # 404 JSON en vez de la interfaz (comportamiento normal de la API).
    _RUTAS_SERVIDOR = ("/api/", "/health", "/docs", "/redoc", "/openapi.json")

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            # Se compara contra scope["path"] (la URL original, siempre con "/")
            # y no contra `path`: en Windows StaticFiles normaliza la ruta con
            # separadores "\", así que ahí los prefijos no coincidirían.
            ruta = scope.get("path", "")
            if exc.status_code == 404 and not ruta.startswith(self._RUTAS_SERVIDOR):
                return await super().get_response("index.html", scope)
            raise


if FRONTEND_DIST.is_dir():
    app.mount("/", SPAStaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:
    @app.get("/", tags=["Frontend"])
    def frontend_sin_compilar():
        """
        Aviso cuando todavía no existe el build del frontend (frontend/dist).

        La API funciona igual; solo falta compilar la interfaz con:
            cd frontend && npm run build
        """
        return {
            "detail": "El frontend aún no está compilado. Ejecuta: cd frontend && npm run build",
            "api_docs": "/docs",
        }
