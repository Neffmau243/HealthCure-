"""
seed.py — SEMILLAS DE DATOS DE PRUEBA

Ejecuta automáticamente al iniciar el servidor (llamado desde main.py).
Crea datos de prueba SOLO si la base de datos está vacía.

Qué crea:
  1. Admin → admin@healthcure.com / admin123
  2. Médico → dr.garcia@healthcure.com / doctor123
  3. 5 pacientes de prueba con diferentes demographics
  4. 3 evaluaciones de ejemplo (si existe el modelo ML)

IMPORTANTE: Si la BD ya tiene datos, NO crea nada (idempotente).
"""
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.usuario import Usuario
from app.models.paciente import Paciente
from app.models.evaluacion import Evaluacion
from passlib.context import CryptContext
from datetime import date

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- USUARIOS DE PRUEBA ---
SEED_USERS = [
    {
        "nombre": "Administrador",
        "email": "admin@healthcure.com",
        "password": "admin123",
        "rol": "admin",
    },
    {
        "nombre": "Dr. Carlos García",
        "email": "dr.garcia@healthcure.com",
        "password": "doctor123",
        "rol": "usuario",
    },
    {
        "nombre": "Enfermera Ana Martínez",
        "email": "ana.martinez@healthcure.com",
        "password": "enfermera123",
        "rol": "usuario",
    },
]

# --- PACIENTES DE PRUEBA ---
SEED_PACIENTES = [
    {
        "nombre": "Juan Pérez Rodríguez",
        "documento_identidad": "1032456789",
        "fecha_nacimiento": date(1965, 5, 20),
        "sexo": "M",
        "talla_cm": 172.5,
        "peso_kg": 85.3,
    },
    {
        "nombre": "María Fernanda López",
        "documento_identidad": "1098765432",
        "fecha_nacimiento": date(1978, 11, 8),
        "sexo": "F",
        "talla_cm": 160.0,
        "peso_kg": 68.7,
    },
    {
        "nombre": "Roberto Carlos Gómez",
        "documento_identidad": "1122334455",
        "fecha_nacimiento": date(1955, 2, 14),
        "sexo": "M",
        "talla_cm": 168.0,
        "peso_kg": 92.1,
    },
    {
        "nombre": "Laura Daniela Martínez",
        "documento_identidad": "1055667788",
        "fecha_nacimiento": date(1990, 7, 30),
        "sexo": "F",
        "talla_cm": 165.0,
        "peso_kg": 58.4,
    },
    {
        "nombre": "Pedro Antonio Sánchez",
        "documento_identidad": "1066778899",
        "fecha_nacimiento": date(1948, 9, 3),
        "sexo": "M",
        "talla_cm": 170.0,
        "peso_kg": 78.5,
    },
]


def seed_database():
    """
    Crea datos de prueba si la base de datos está vacía.
    Llamado desde main.py al iniciar el servidor.
    """
    db = SessionLocal()
    try:
        # --- Verificar si ya hay datos ---
        user_count = db.query(Usuario).count()
        if user_count > 0:
            print(f"[OK] Base de datos ya tiene datos ({user_count} usuarios). Seed saltado.")
            return

        print("[SEED] Iniciando seed de la base de datos...")

        # --- Crear usuarios ---
        for user_data in SEED_USERS:
            usuario = Usuario(
                nombre=user_data["nombre"],
                email=user_data["email"],
                password_hash=pwd_context.hash(user_data["password"]),
                rol=user_data["rol"],
                activo=True,
            )
            db.add(usuario)
        db.flush()  # Flush para obtener los IDs (sin commit aún)
        print(f"  [OK] {len(SEED_USERS)} usuarios creados")

        # --- Crear pacientes (asociados al médico dr.garcia, id=2) ---
        doctor_id = 2  # ID del médico (dr.garcia@healthcure.com)
        for paciente_data in SEED_PACIENTES:
            paciente = Paciente(
                usuario_creador_id=doctor_id,  # Dr. García registró estos pacientes
                nombre=paciente_data["nombre"],
                documento_identidad=paciente_data["documento_identidad"],
                fecha_nacimiento=paciente_data["fecha_nacimiento"],
                sexo=paciente_data["sexo"],
                talla_cm=paciente_data["talla_cm"],
                peso_kg=paciente_data["peso_kg"],
            )
            db.add(paciente)
        db.flush()
        print(f"  [OK] {len(SEED_PACIENTES)} pacientes creados")

        # --- Crear evaluaciones de ejemplo ---
        evaluaciones_data = [
            # Juan Pérez (61 años) — alto riesgo
            {
                "paciente_id": 1,
                "usuario_id": doctor_id,
                "edad": 61,
                "presion_alta": True,
                "colesterol_alto": True,
                "tabaquismo": True,
                "actividad_fisica": False,
                "antecedente_acv": False,
                "diabetes": True,
                "salud_general": 4,
                "dificultad_para_caminar": False,
                "probabilidad": 0.784521,
                "clasificacion": "alto",
                "modelo_version": "1.0.0",
            },
            # María López (48 años) — riesgo moderado
            {
                "paciente_id": 2,
                "usuario_id": doctor_id,
                "edad": 48,
                "presion_alta": True,
                "colesterol_alto": False,
                "tabaquismo": False,
                "actividad_fisica": True,
                "antecedente_acv": False,
                "diabetes": False,
                "salud_general": 2,
                "dificultad_para_caminar": False,
                "probabilidad": 0.352100,
                "clasificacion": "moderado",
                "modelo_version": "1.0.0",
            },
            # Roberto Gómez (71 años) — alto riesgo
            {
                "paciente_id": 3,
                "usuario_id": doctor_id,
                "edad": 71,
                "presion_alta": True,
                "colesterol_alto": True,
                "tabaquismo": False,
                "actividad_fisica": False,
                "antecedente_acv": True,
                "diabetes": True,
                "salud_general": 5,
                "dificultad_para_caminar": True,
                "probabilidad": 0.921000,
                "clasificacion": "alto",
                "modelo_version": "1.0.0",
            },
        ]

        for eval_data in evaluaciones_data:
            evaluacion = Evaluacion(**eval_data)
            db.add(evaluacion)
        db.flush()
        print(f"  [OK] {len(evaluaciones_data)} evaluaciones creadas")

        # --- Commit final ---
        db.commit()
        print("[SEED] Completado exitosamente!")
        print()
        print("  Credenciales de prueba:")
        print("  -----------------------------------")
        print("  Admin:     admin@healthcure.com / admin123")
        print("  Medico:    dr.garcia@healthcure.com / doctor123")
        print("  Enfermera: ana.martinez@healthcure.com / enfermera123")
        print()

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error en seed: {e}")
        raise
    finally:
        db.close()
