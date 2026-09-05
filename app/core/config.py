"""
config.py — CONFIGURACIÓN CENTRAL DE LA APLICACIÓN

Carga TODAS las variables de entorno (.env) y las expone como un objeto
tipado con Pydantic Settings. Cualquier archivo del proyecto que necesite
un dato de configuración importa get_settings() desde aquí.

NUNCA se leen variables de entorno directamente con os.getenv() en otros
archivos — siempre se pasa por este módulo para mantener un solo punto
de verdad y validación de tipos.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Clase tipada que mapea variables de entorno (.env) a atributos Python.
    Pydantic valida los tipos automáticamente al cargar.
    """

    # --- App ---
    APP_NAME: str = "HealthCure - CardioPredict"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False  # Si True, SQLAlchemy loguea cada query SQL

    # --- Database - MySQL ---
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "healthcure_db"

    @property
    def DATABASE_URL(self) -> str:
        """
        Cadena de conexión síncrona (PyMySQL) para SQLAlchemy.
        Formato: mysql+pymysql://user:pass@host:port/db
        """
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def DATABASE_URL_ASYNC(self) -> str:
        """
        Cadena de conexión asíncrona (aiomysql) — por si se necesita
        en el futuro con FastAPI async. Por ahora usamos la síncrona.
        """
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # --- CORS (permisos de conexión desde el frontend) ---
    # Orígenes permitidos, separados por coma. Ejemplos:
    #   "*"                          → cualquier origen (SOLO desarrollo)
    #   "http://localhost:3000"      → un solo frontend
    #   "http://localhost:3000,https://app.healthcure.com" → varios
    # NOTA: con "*" los navegadores rechazan allow_credentials=True (spec CORS),
    # así que en main.py las credenciales se habilitan solo si hay orígenes concretos.
    CORS_ORIGINS: str = "*"

    @property
    def cors_origins_list(self) -> list[str]:
        """Convierte CORS_ORIGINS (string separado por comas) en lista de Python."""
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # --- JWT (autenticación por tokens) ---
    JWT_SECRET_KEY: str = "CHANGE-THIS-IN-PRODUCTION-super-secret-key"
    JWT_ALGORITHM: str = "HS256"  # Algoritmo de firma HMAC-SHA256
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # Token válido por 1 hora

    # --- ML Model ---
    MODEL_PATH: str = "app/resources/modelo_cardiaco.joblib"
    # Ruta al archivo .joblib del modelo entrenado de Random Forest/XGBoost

    class Config:
        env_file = ".env"  # Lee de este archivo al iniciar
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """
    Crea UNA sola instancia de Settings y la cachea con lru_cache.
    Así no re-leemos el archivo .env en cada request — solo la primera vez.
    """
    return Settings()
