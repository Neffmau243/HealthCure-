"""
seed.py — SEMILLAS DE DATOS DE PRUEBA

Ejecuta automáticamente al iniciar el servidor (llamado desde main.py).
Crea datos de prueba SOLO si la base de datos está vacía.

Qué crea:
  1. Admin → admin@healthcure.com / admin123
  2. Médico → dr.garcia@healthcure.com / doctor123
  3. Catálogos: distritos + localidades (los gestiona el admin)
  4. Pacientes de prueba con datos detallados (formato peruano)
  5. Evaluaciones de ejemplo (si existe el modelo ML)

IMPORTANTE: Si la BD ya tiene datos, NO crea nada (idempotente),
pero SÍ hace backfill de usuario_creador_id en pacientes legacy.
"""
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.usuario import Usuario
from app.models.paciente import Paciente
from app.models.evaluacion import Evaluacion
from app.models.distrito import Distrito
from app.models.localidad import Localidad
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

# --- CATÁLOGOS: DISTRITOS (gestionados por el admin) ---
SEED_DISTRITOS = [
    "Alto Selva Alegre",
    "Cayma",
    "Miraflores",
    "Yanahuara",
    "Cerro Colorado",
]

# --- CATÁLOGOS: LOCALIDADES (cada una pertenece a un distrito) ---
# La clave es el NOMBRE del distrito (se resuelve al insertar)
SEED_LOCALIDADES = {
    "Alto Selva Alegre": ["Chilpinilla", "El Mirador", "La Tomilla", "Mariano Melgar"],
    "Cayma": ["Huachipa", "La Pampilla", "Trujamanes"],
    "Miraflores": ["Campina", "El Golf", "Lara"],
    "Yanahuara": ["La Perla", "Mirador de Yanahuara"],
    "Cerro Colorado": ["El Progreso", "La Mansión", "Tahuaycani"],
}

# --- PACIENTES DE PRUEBA (datos detallados, formato peruano) ---
SEED_PACIENTES = [
    {
        "tipo_documento": "DNI",
        "documento_identidad": "1032456789",
        "numero_historia_clinica": "72769512",
        "apellido_paterno": "Pérez",
        "apellido_materno": "Rodríguez",
        "nombres": "Juan",
        "fecha_nacimiento": date(1965, 5, 20),
        "sexo": "M",
        "telefono": "987654321",
        "direccion": "Av. Principal 123",
        "distrito_nombre": "Alto Selva Alegre",
        "localidad_nombre": "Chilpinilla",
        "tipo_seguro": "SIS",
        "codigo_afiliacion_seguro": "040-2-1032456789",
        "talla_cm": 172.5,
        "peso_kg": 85.3,
    },
    {
        "tipo_documento": "DNI",
        "documento_identidad": "1098765432",
        "numero_historia_clinica": "88123456",
        "apellido_paterno": "López",
        "apellido_materno": "Quispe",
        "nombres": "María Fernanda",
        "fecha_nacimiento": date(1978, 11, 8),
        "sexo": "F",
        "telefono": "987123456",
        "direccion": "Calle Los Rosales 45",
        "distrito_nombre": "Cayma",
        "localidad_nombre": "La Pampilla",
        "tipo_seguro": "EsSalud",
        "codigo_afiliacion_seguro": "ESS-77889900",
        "talla_cm": 160.0,
        "peso_kg": 68.7,
    },
    {
        "tipo_documento": "DNI",
        "documento_identidad": "1122334455",
        "numero_historia_clinica": "90345678",
        "apellido_paterno": "Gómez",
        "apellido_materno": "Chávez",
        "nombres": "Roberto Carlos",
        "fecha_nacimiento": date(1955, 2, 14),
        "sexo": "M",
        "telefono": "987777888",
        "direccion": "Jr. La Merced 88",
        "distrito_nombre": "Cerro Colorado",
        "localidad_nombre": "Tahuaycani",
        "tipo_seguro": "SIS",
        "codigo_afiliacion_seguro": "040-1-1122334455",
        "talla_cm": 168.0,
        "peso_kg": 92.1,
    },
    {
        "tipo_documento": "DNI",
        "documento_identidad": "1055667788",
        "numero_historia_clinica": "76543210",
        "apellido_paterno": "Martínez",
        "apellido_materno": "Rojas",
        "nombres": "Laura Daniela",
        "fecha_nacimiento": date(1990, 7, 30),
        "sexo": "F",
        "telefono": "982345678",
        "direccion": "Av. Ejercito 210",
        "distrito_nombre": "Yanahuara",
        "localidad_nombre": "Mirador de Yanahuara",
        "tipo_seguro": "Privado",
        "codigo_afiliacion_seguro": "EPS-55667788",
        "talla_cm": 165.0,
        "peso_kg": 58.4,
    },
    {
        "tipo_documento": "DNI",
        "documento_identidad": "1066778899",
        "numero_historia_clinica": "69988776",
        "apellido_paterno": "Sánchez",
        "apellido_materno": "Huamán",
        "nombres": "Pedro Antonio",
        "fecha_nacimiento": date(1948, 9, 3),
        "sexo": "M",
        "telefono": "981234567",
        "direccion": "Mz. G Lote 14",
        "distrito_nombre": "Miraflores",
        "localidad_nombre": "El Golf",
        "tipo_seguro": "EsSalud",
        "codigo_afiliacion_seguro": "ESS-11223344",
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
            _backfill_creadores(db)  # Pero SÍ asigna creador a pacientes legacy
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

        # --- Buscar al médico por email (NO hardcodear el ID) ---
        doctor = db.query(Usuario).filter(Usuario.email == "dr.garcia@healthcure.com").first()
        doctor_id = doctor.id if doctor else None

        # --- Crear distritos ---
        distrito_ids = {}
        for nombre in SEED_DISTRITOS:
            distrito = Distrito(nombre=nombre, activo=True)
            db.add(distrito)
            db.flush()
            distrito_ids[nombre] = distrito.id
        print(f"  [OK] {len(SEED_DISTRITOS)} distritos creados")

        # --- Crear localidades (dependen de su distrito) ---
        localidad_ids = {}
        for distrito_nombre, localidades in SEED_LOCALIDADES.items():
            for loc_nombre in localidades:
                localidad = Localidad(
                    nombre=loc_nombre,
                    distrito_id=distrito_ids[distrito_nombre],
                    activo=True,
                )
                db.add(localidad)
                db.flush()
                localidad_ids[(distrito_nombre, loc_nombre)] = localidad.id
        print(f"  [OK] {sum(len(v) for v in SEED_LOCALIDADES.values())} localidades creadas")

        # --- Crear pacientes (asociados al médico dr.garcia) ---
        for paciente_data in SEED_PACIENTES:
            paciente = Paciente(
                usuario_creador_id=doctor_id,
                tipo_documento=paciente_data["tipo_documento"],
                documento_identidad=paciente_data["documento_identidad"],
                numero_historia_clinica=paciente_data["numero_historia_clinica"],
                apellido_paterno=paciente_data["apellido_paterno"],
                apellido_materno=paciente_data["apellido_materno"],
                nombres=paciente_data["nombres"],
                fecha_nacimiento=paciente_data["fecha_nacimiento"],
                sexo=paciente_data["sexo"],
                telefono=paciente_data["telefono"],
                direccion=paciente_data["direccion"],
                distrito_id=distrito_ids[paciente_data["distrito_nombre"]],
                localidad_id=localidad_ids[
                    (paciente_data["distrito_nombre"], paciente_data["localidad_nombre"])
                ],
                tipo_seguro=paciente_data["tipo_seguro"],
                codigo_afiliacion_seguro=paciente_data["codigo_afiliacion_seguro"],
                talla_cm=paciente_data["talla_cm"],
                peso_kg=paciente_data["peso_kg"],
                activo=True,
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


def _backfill_creadores(db: Session):
    """
    BACKFILL idempotente: asigna usuario_creador_id a pacientes legacy
    que quedaron sin creador (sembrados antes de que existiera la columna).

    Así el sistema de permisos funciona con datos existentes:
    un médico NO puede editar pacientes que no registró él.

    Solo toca pacientes con usuario_creador_id = NULL.
    """
    doctor = db.query(Usuario).filter(Usuario.email == "dr.garcia@healthcure.com").first()
    if not doctor:
        return  # No hay médico → no hay a quién asignar

    sin_creador = (
        db.query(Paciente)
        .filter(Paciente.usuario_creador_id.is_(None))
        .all()
    )
    for paciente in sin_creador:
        paciente.usuario_creador_id = doctor.id
    if sin_creador:
        db.commit()
        print(f"  [OK] Backfill: {len(sin_creador)} pacientes asignados a {doctor.nombre}")