"""
triaje_pacientes.py — Ejecuta evaluaciones cardíacas (triajes) para los pacientes nuevos.
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

# --- Login ---
login_resp = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "dr.garcia@healthcure.com",
    "password": "doctor123"
})
login_resp.raise_for_status()
token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# --- Triajes para cada paciente (datos basados en sus perfiles) ---
triajes = [
    {
        "paciente_id": 18,
        "nombre": "Salazar Vargas, Carlos Alberto",
        "data": {
            "paciente_id": 18,
            "edad": 46,
            "presion_alta": True,
            "colesterol_alto": True,
            "tabaquismo": False,
            "actividad_fisica": False,
            "antecedente_acv": False,
            "diabetes": False,
            "salud_general": 3,
            "dificultad_para_caminar": False
        }
    },
    {
        "paciente_id": 19,
        "nombre": "Mendoza Flores, Maria Elena",
        "data": {
            "paciente_id": 19,
            "edad": 51,
            "presion_alta": False,
            "colesterol_alto": False,
            "tabaquismo": False,
            "actividad_fisica": True,
            "antecedente_acv": False,
            "diabetes": False,
            "salud_general": 2,
            "dificultad_para_caminar": False
        }
    },
    {
        "paciente_id": 20,
        "nombre": "Quispe Condori, Jose Luis",
        "data": {
            "paciente_id": 20,
            "edad": 58,
            "presion_alta": True,
            "colesterol_alto": True,
            "tabaquismo": True,
            "actividad_fisica": False,
            "antecedente_acv": False,
            "diabetes": True,
            "salud_general": 4,
            "dificultad_para_caminar": True
        }
    }
]

print("=" * 70)
print("TRIAJES CARDIACOS - MODELO ML")
print("=" * 70)

for t in triajes:
    print(f"\n--- {t['nombre']} (ID: {t['paciente_id']}) ---")
    r = requests.post(f"{BASE_URL}/evaluaciones/", json=t["data"], headers=headers)
    if r.status_code in (200, 201):
        ev = r.json()
        print(f"  Probabilidad: {ev.get('probabilidad_riesgo', '?')}")
        print(f"  Clasificacion: {ev.get('clasificacion', '?')}")
        print(f"  Codigo color: {ev.get('codigo_color', '?')}")
        triaje = ev.get('triaje_clinico', {})
        if triaje:
            print(f"  Recomendacion: {triaje.get('recomendacion', '?')}")
            print(f"  Nivel atencion: {triaje.get('nivel_atencion', '?')}")
            hallazgos = triaje.get('hallazgos', [])
            if hallazgos:
                print(f"  Hallazgos:")
                for h in hallazgos:
                    print(f"    - {h}")
    else:
        print(f"  Error: {r.status_code} {r.text}")

# --- Resumen final ---
print("\n" + "=" * 70)
print("RESUMEN DE EVALUACIONES")
print("=" * 70)
resp = requests.get(f"{BASE_URL}/evaluaciones/resumen", headers=headers)
if resp.status_code == 200:
    resumen = resp.json()
    print(f"Total evaluaciones: {resumen.get('total_evaluaciones', '?')}")
    print(f"Clasificacion: {json.dumps(resumen.get('por_clasificacion', {}), indent=2)}")
