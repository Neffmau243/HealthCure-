"""
main.py — PUNTO DE ENTRADA DE LA APLICACIÓN

Este es el archivo que ejecuta FastAPI con:
    uvicorn main:app --reload --port 8000

¿Qué hace?
  1. Crea la instancia de FastAPI
  2. Configura CORS (permisos de conexión desde el frontend)
  3. Registra TODOS los endpoints (routers)
  4. Expone un endpoint de health check

Jerarquía de rutas:
    /api/v1/auth/*          → Autenticación (login, registro)
    /api/v1/pacientes/*     → CRUD de pacientes
    /api/v1/evaluaciones/*  → Evaluaciones cardíacas (ML)
    /api/v1/admin/*         → Administración (solo admins)
    /health                 → Health check (sin auth)
    /docs                   → Swagger UI (documentación interactiva)
    /redoc                  → ReDoc (documentación alternativa)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.v1 import auth, pacientes, evaluaciones, admin

settings = get_settings()

# --- INSTANCIA DE FASTAPI ---
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema de triaje cardíaco con predicción ML — CardioPredict",
    docs_url="/docs",     # Swagger UI interactivo (para probar la API)
    redoc_url="/redoc",   # Documentación alternativa
)

# --- CORS (Cross-Origin Resource Sharing) ---
# Permite que el frontend (React) se conecte al backend (FastAPI)
# desde un navegador web. Sin esto, el navegador bloquearía las peticiones.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # En producción, cambiar a ["http://localhost:3000"]
    allow_credentials=True,   # Permite cookies y headers de autenticación
    allow_methods=["*"],      # Permite GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],      # Permite cualquier header (Authorization, Content-Type, etc.)
)

# --- REGISTRO DE ENDPOINTS (Routers) ---
# Cada router maneja un grupo de rutas relacionadas.
# El prefix="/api/v1" agrega la versión de la API a todas las rutas.
app.include_router(auth.router, prefix="/api/v1")
app.include_router(pacientes.router, prefix="/api/v1")
app.include_router(evaluaciones.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


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
