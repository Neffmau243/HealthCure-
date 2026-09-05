"""
test_permisos_pacientes.py — TESTS DE PERMISOS Y REGLAS DE NEGOCIO

Corre contra la API completa (FastAPI TestClient) pero con SQLite en
memoria en vez de MySQL (ver conftest.py). Cubre:

  - Regla de edición de pacientes: solo el creador o un admin
  - Pacientes legacy (sin creador): editables por cualquiera
  - Guards anti-lockout del admin:
      * un admin no puede desactivarse a sí mismo
      * un admin no puede quitarse su propio rol
      * sí puede desactivar a otros (médicos/enfermeras)
  - El registro público SIEMPRE crea usuarios con rol "usuario"
"""
import pytest


# ============================================================
# Permisos de edición de pacientes
# ============================================================

def test_medico_puede_editar_su_propio_paciente(env, usuarios_base):
    h = env.auth_header(usuarios_base["doctor"].id, "usuario")
    r = env.client.put(
        f"/api/v1/pacientes/{usuarios_base['paciente_doctor'].id}",
        json={"telefono": "999000111"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["telefono"] == "999000111"


def test_medico_no_puede_editar_paciente_de_otro(env, usuarios_base):
    """La enfermera intenta editar el paciente del doctor → 403."""
    h = env.auth_header(usuarios_base["enfermera"].id, "usuario")
    r = env.client.put(
        f"/api/v1/pacientes/{usuarios_base['paciente_doctor'].id}",
        json={"telefono": "999000222"},
        headers=h,
    )
    assert r.status_code == 403
    assert "permiso" in r.json()["detail"].lower()


def test_admin_puede_editar_cualquier_paciente(env, usuarios_base):
    h = env.auth_header(usuarios_base["admin"].id, "admin")
    r = env.client.put(
        f"/api/v1/pacientes/{usuarios_base['paciente_doctor'].id}",
        json={"telefono": "999000333"},
        headers=h,
    )
    assert r.status_code == 200


def test_paciente_legacy_sin_creador_es_editable_por_cualquiera(env, usuarios_base):
    """Datos viejos (sin creador) mantienen el comportamiento por defecto."""
    h = env.auth_header(usuarios_base["enfermera"].id, "usuario")
    r = env.client.put(
        f"/api/v1/pacientes/{usuarios_base['paciente_legacy'].id}",
        json={"telefono": "999000444"},
        headers=h,
    )
    assert r.status_code == 200


def test_historia_clinica_duplicada_rechazada(env, usuarios_base):
    """Dos pacientes no pueden compartir número de historia clínica."""
    h = env.auth_header(usuarios_base["doctor"].id, "usuario")
    r = env.client.post(
        "/api/v1/pacientes/",
        json={
            "tipo_documento": "DNI",
            "documento_identidad": "99999999",  # documento nuevo
            "numero_historia_clinica": "HC-DUP-001",  # ya en uso abajo
            "apellido_paterno": "Duplicado",
            "nombres": "Test",
            "fecha_nacimiento": "1985-01-01",
            "sexo": "M",
            "tipo_seguro": "SIS",
        },
        headers=h,
    )
    assert r.status_code == 201

    # Intentar registrar OTRO paciente con la misma historia clínica
    r2 = env.client.post(
        "/api/v1/pacientes/",
        json={
            "tipo_documento": "DNI",
            "documento_identidad": "88888888",
            "numero_historia_clinica": "HC-DUP-001",
            "apellido_paterno": "Otro",
            "nombres": "Paciente",
            "fecha_nacimiento": "1990-01-01",
            "sexo": "F",
            "tipo_seguro": "SIS",
        },
        headers=h,
    )
    assert r2.status_code == 409
    assert "historia clínica" in r2.json()["detail"]


# ============================================================
# Guards anti-lockout del admin
# ============================================================

def test_admin_no_puede_desactivarse_a_si_mismo(env, usuarios_base):
    admin = usuarios_base["admin"]
    h = env.auth_header(admin.id, "admin")
    r = env.client.put(f"/api/v1/admin/usuarios/{admin.id}/deactivate", headers=h)
    assert r.status_code == 409
    assert "propia cuenta" in r.json()["detail"]


def test_admin_no_puede_quitarse_su_propio_rol(env, usuarios_base):
    admin = usuarios_base["admin"]
    h = env.auth_header(admin.id, "admin")
    r = env.client.put(
        f"/api/v1/admin/usuarios/{admin.id}",
        json={"rol": "usuario"},
        headers=h,
    )
    assert r.status_code == 409


def test_admin_no_puede_desactivar_ultimo_admin(env, usuarios_base):
    """Solo hay 1 admin activo y es quien ejecuta → la acción cae en el guard."""
    admin = usuarios_base["admin"]
    h = env.auth_header(admin.id, "admin")
    # Intentar desactivarse vía PUT (campo activo) — debe bloquearse igual
    r = env.client.put(
        f"/api/v1/admin/usuarios/{admin.id}",
        json={"activo": False},
        headers=h,
    )
    assert r.status_code == 409


def test_admin_si_puede_desactivar_a_un_medico(env, usuarios_base):
    """Desactivar a un usuario normal (no admin) siempre está permitido."""
    admin = usuarios_base["admin"]
    doctor = usuarios_base["doctor"]
    h = env.auth_header(admin.id, "admin")
    r = env.client.put(f"/api/v1/admin/usuarios/{doctor.id}/deactivate", headers=h)
    assert r.status_code == 200
    assert r.json()["activo"] is False

    # El médico desactivado ya no puede hacer login
    r_login = env.client.post(
        "/api/v1/auth/login",
        json={"email": doctor.email, "password": "doctor123"},
    )
    assert r_login.status_code == 401


def test_admin_con_dos_admins_puede_desactivar_al_otro(env, usuarios_base):
    """Con 2 admins activos, uno SÍ puede desactivar al otro (no queda lockout)."""
    admin = usuarios_base["admin"]
    admin2 = env.create_usuario("Admin 2", "admin2@test.com", "admin456", "admin")

    h = env.auth_header(admin.id, "admin")
    r = env.client.put(f"/api/v1/admin/usuarios/{admin2.id}/deactivate", headers=h)
    assert r.status_code == 200
    assert r.json()["activo"] is False


# ============================================================
# Registro público
# ============================================================

def test_register_siempre_crea_rol_usuario(env):
    """El registro público NO puede crear admins (rol fijo 'usuario')."""
    r = env.client.post(
        "/api/v1/auth/register",
        json={
            "nombre": "Nuevo Usuario",
            "email": "nuevo@test.com",
            "password": "password123",
            # sin campo rol: el registro público no lo acepta
        },
    )
    assert r.status_code == 201
    assert r.json()["rol"] == "usuario"
