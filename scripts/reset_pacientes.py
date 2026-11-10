"""
reset_pacientes.py — Borra todos los pacientes directamente desde la BD
y registra pacientes nuevos de prueba via API.
"""
import requests
import sys
sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.models.paciente import Paciente
from app.models.evaluacion import Evaluacion
from app.models.atencion import Atencion

BASE_URL = "http://127.0.0.1:8000/api/v1"

# --- Borrar desde la BD ---
db = SessionLocal()
try:
    # Primero borrar evaluaciones y atenciones (FK constraints)
    n_eval = db.query(Evaluacion).delete()
    n_aten = db.query(Atencion).delete()
    n_pac = db.query(Paciente).delete()
    db.commit()
    print(f"Borrados: {n_pac} pacientes, {n_eval} evaluaciones, {n_aten} atenciones")
except Exception as e:
    db.rollback()
    print(f"Error: {e}")
    sys.exit(1)
finally:
    db.close()

# --- Login ---
login_resp = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "dr.garcia@healthcure.com",
    "password": "doctor123"
})
login_resp.raise_for_status()
token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# --- Registrar pacientes nuevos de prueba ---
nuevos_pacientes = [
    {
        "tipo_documento": "DNI",
        "documento_identidad": "72345678",
        "numero_historia_clinica": "HC-2026-001",
        "apellido_paterno": "Salazar",
        "apellido_materno": "Vargas",
        "nombres": "Carlos Alberto",
        "fecha_nacimiento": "1980-03-15",
        "sexo": "M",
        "telefono": "987123456",
        "direccion": "Av. Los Pinos 456",
        "distrito_id": 1,
        "localidad_id": 1,
        "tipo_seguro": "SIS",
        "codigo_afiliacion_seguro": "040-1-72345678",
        "talla_cm": 175.0,
        "peso_kg": 82.5,
        "presion_sistolica": 130,
        "presion_diastolica": 85,
        "frecuencia_cardiaca": 78,
        "temperatura_c": 36.8,
        "saturacion_o2": 97,
        "sintomas": "Dolor toracico leve, disnea de esfuerzo",
        "antecedentes": "Hipertension arterial hace 5 anos",
        "medicamentos": "Losartan 50mg",
        "alergias": "Ninguna",
        "fumador": False,
        "alcohol": False,
        "ejercicio": False,
        "diabetes": False,
        "colesterol_alto": True
    },
    {
        "tipo_documento": "DNI",
        "documento_identidad": "73456789",
        "numero_historia_clinica": "HC-2026-002",
        "apellido_paterno": "Mendoza",
        "apellido_materno": "Flores",
        "nombres": "Maria Elena",
        "fecha_nacimiento": "1975-07-22",
        "sexo": "F",
        "telefono": "987654321",
        "direccion": "Jr. Las Flores 789",
        "distrito_id": 2,
        "localidad_id": 6,
        "tipo_seguro": "EsSalud",
        "codigo_afiliacion_seguro": "ESS-77889911",
        "talla_cm": 162.0,
        "peso_kg": 68.0,
        "presion_sistolica": 120,
        "presion_diastolica": 75,
        "frecuencia_cardiaca": 72,
        "temperatura_c": 36.5,
        "saturacion_o2": 98,
        "sintomas": "Palpitaciones ocasionales",
        "antecedentes": "Ninguno relevante",
        "medicamentos": "Ninguno",
        "alergias": "Penicilina",
        "fumador": False,
        "alcohol": False,
        "ejercicio": True,
        "diabetes": False,
        "colesterol_alto": False
    },
    {
        "tipo_documento": "DNI",
        "documento_identidad": "74567890",
        "numero_historia_clinica": "HC-2026-003",
        "apellido_paterno": "Quispe",
        "apellido_materno": "Condori",
        "nombres": "Jose Luis",
        "fecha_nacimiento": "1968-11-10",
        "sexo": "M",
        "telefono": "987789012",
        "direccion": "Calle Los Olivos 321",
        "distrito_id": 5,
        "localidad_id": 15,
        "tipo_seguro": "Privado",
        "codigo_afiliation_seguro": "EPS-55667788",
        "talla_cm": 170.0,
        "peso_kg": 95.0,
        "presion_sistolica": 145,
        "presion_diastolica": 95,
        "frecuencia_cardiaca": 88,
        "temperatura_c": 37.0,
        "saturacion_o2": 95,
        "sintomas": "Dolor toracico intenso, sudoracion, nauseas",
        "antecedentes": "Infarto agudo de miocardio hace 2 anos, diabetes tipo 2",
        "medicamentos": "Metformina 850mg, Aspirina 100mg, Atorvastatina 40mg",
        "alergias": "Ninguna",
        "fumador": True,
        "alcohol": True,
        "ejercicio": False,
        "diabetes": True,
        "colesterol_alto": True
    }
]

print("\n--- Registrando pacientes nuevos ---")
for p in nuevos_pacientes:
    r = requests.post(f"{BASE_URL}/pacientes/", json=p, headers=headers)
    if r.status_code in (200, 201):
        data = r.json()
        print(f"  Registrado: {data.get('nombre_completo', p['nombres'])} (ID: {data.get('id', '?')})")
    else:
        print(f"  Error registrando {p['nombres']}: {r.status_code} {r.text}")

# --- Verificar estado final ---
resp = requests.get(f"{BASE_URL}/pacientes/", headers=headers)
resp.raise_for_status()
final = resp.json()
print(f"\nPacientes finales: {len(final)}")
for p in final:
    print(f"  - [{p['id']}] {p['nombre_completo']} | {p['tipo_documento']} {p['documento_identidad']}")
