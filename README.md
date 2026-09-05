# HealthCure — CardioPredict

Sistema web de triaje cardíaco con predicción automática usando Machine Learning.

## ¿Qué hace este proyecto?

Un médico/técnico de salud ingresa los datos de un paciente y el sistema automáticamente predice el **riesgo cardíaco** usando un modelo de Random Forest/XGBoost.

```
Paciente → Datos clínicos → Modelo ML → Probabilidad + Clasificación de riesgo
```

## Arquitectura del Backend

```
app/
├── models/          → Entidades SQLAlchemy (tablas MySQL)
├── schemas/         → DTOs de entrada/salida (Pydantic)
├── repositories/    → Acceso a la base de datos
├── mappers/         → Traductor entre capas
├── ml/              → Modelo de Machine Learning
├── services/        → Lógica de negocio
├── api/             → Endpoints HTTP (FastAPI)
├── core/            → Configuración y base de datos
├── exceptions/      → Excepciones personalizadas
└── resources/       → Modelo .joblib, SQL, CSV
```

### Capas (de afuera hacia adentro)

```
API Controller → Service → Repository → MySQL
                   ↓
                Mapper ↔ ML Predictor
```

## Stack Tecnológico

| Componente | Tecnología |
|------------|-----------|
| Backend | Python + FastAPI |
| Base de datos | MySQL |
| ORM | SQLAlchemy |
| Validación | Pydantic v2 |
| Autenticación | JWT (python-jose) |
| Contraseñas | bcrypt (passlib) |
| ML | Random Forest / XGBoost (scikit-learn) |

## Requisitos

- Python 3.10+
- MySQL 8.0+
- pip (gestor de paquetes)

## Instalación

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd healthcure-backend
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar base de datos

1. Abrir MySQL Workbench o tu cliente favorito
2. Crear la base de datos:

```sql
CREATE DATABASE healthcure_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
```

3. Ejecutar el script SQL:

```bash
# Opción A: desde la consola de MySQL
mysql -u root -p healthcure_db < app/resources/schema.sql

# Opción B: desde MySQL Workbench
# Abrir app/resources/schema.sql y ejecutar
```

### 5. Configurar variables de entorno

Editar el archivo `.env` con tus credenciales de MySQL:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu_password_aqui
DB_NAME=healthcure_db
JWT_SECRET_KEY=cambia-esta-clave-super-secreta
DEBUG=True
```

### 6. Levantar el servidor

```bash
uvicorn main:app --reload --port 8000
```

El servidor arranca en: **http://localhost:8000**

### 7. Verificar que funciona

Abrir en el navegador: **http://localhost:8000/docs**

Ahí aparece el Swagger UI con todos los endpoints disponibles.

### 8. Correr los tests (opcional)

Los tests corren con una base **SQLite en memoria** — NO necesitan MySQL levantado:

```bash
pip install -r requirements-dev.txt   # pytest + httpx (solo desarrollo)
python -m pytest app/tests -v
```

Cubren el mapper de evaluaciones, el preprocesador del modelo ML y las reglas
de permisos (quién puede editar pacientes y los guards anti-lockout del admin).

## Endpoints Disponibles

### Auth (públicos)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Registrar usuario nuevo (SIEMPRE crea rol `usuario`) |
| POST | `/api/v1/auth/login` | Login → token JWT |
| GET | `/api/v1/auth/me` | Datos del usuario autenticado |

### Pacientes (requiere JWT)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/pacientes/` | Listar todos |
| GET | `/api/v1/pacientes/search?documento=1234` | Buscar por documento |
| GET | `/api/v1/pacientes/{id}` | Obtener por ID |
| GET | `/api/v1/pacientes/by-documento/{doc}` | Obtener por documento exacto |
| POST | `/api/v1/pacientes/` | Registrar paciente nuevo |
| PUT | `/api/v1/pacientes/{id}` | Actualizar datos |

### Evaluaciones Cardíacas (requiere JWT)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/evaluaciones/` | **Crear evaluación (predicción ML)** |
| GET | `/api/v1/evaluaciones/` | Listar todas (paginado) |
| GET | `/api/v1/evaluaciones/{id}` | Ver una evaluación |
| GET | `/api/v1/evaluaciones/by-paciente/{id}` | Historial de un paciente |

### Catálogos (requiere JWT — opciones para el doctor)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/catalogos/distritos` | Distritos activos (dropdown) |
| GET | `/api/v1/catalogos/localidades?distrito_id=1` | Localidades activas de un distrito (dropdown) |

### Admin (requiere JWT + rol admin)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/admin/usuarios` | Listar todos los usuarios |
| GET | `/api/v1/admin/usuarios/{id}` | Obtener usuario por ID |
| POST | `/api/v1/admin/usuarios` | Crear usuario (admin elige rol) |
| PUT | `/api/v1/admin/usuarios/{id}` | Actualizar usuario (parcial) |
| PUT | `/api/v1/admin/usuarios/{id}/activate` | Reactivar usuario |
| PUT | `/api/v1/admin/usuarios/{id}/deactivate` | Desactivar usuario |
| GET | `/api/v1/admin/distritos` | Listar distritos (catálogo) |

> **Seguridad admin:** el registro público (`/auth/register`) **no acepta** campo `rol` — siempre crea usuarios con rol `usuario`. Para crear/editar admins solo existe `/api/v1/admin/usuarios*`. Además, un admin **no puede desactivar su propia cuenta ni quitarse el rol admin**, y **nadie puede desactivar/degradar al último administrador activo** (evita dejar la app sin administradores → responde `409`).
| POST | `/api/v1/admin/distritos` | Crear distrito |
| PUT | `/api/v1/admin/distritos/{id}` | Actualizar distrito |
| PUT | `/api/v1/admin/distritos/{id}/deactivate` | Desactivar distrito |
| GET | `/api/v1/admin/localidades` | Listar localidades (catálogo) |
| POST | `/api/v1/admin/localidades` | Crear localidad |
| PUT | `/api/v1/admin/localidades/{id}` | Actualizar localidad |
| PUT | `/api/v1/admin/localidades/{id}/deactivate` | Desactivar localidad |

## Flujo de Uso Típico

```
1. POST /api/v1/auth/register   → Crear cuenta de usuario
2. POST /api/v1/auth/login      → Obtener token JWT
3. GET  /api/v1/catalogos/distritos  → Cargar opciones del formulario (dropdowns)
4. POST /api/v1/pacientes/      → Registrar paciente (formato detallado)
5. POST /api/v1/evaluaciones/   → Evaluar riesgo cardíaco
6. GET  /api/v1/evaluaciones/   → Ver historial
```

## Credenciales de Prueba (seed automático)

Al levantar el servidor, el seed crea estos usuarios (solo si la BD está vacía):

| Rol | Email | Password |
|-----|-------|----------|
| Admin | `admin@healthcure.com` | `admin123` |
| Médico | `dr.garcia@healthcure.com` | `doctor123` |
| Enfermera | `ana.martinez@healthcure.com` | `enfermera123` |

Además crea 5 distritos, 15 localidades, 5 pacientes de ejemplo y 3 evaluaciones.

## Registro de Paciente (formato detallado)

```json
{
    "tipo_documento": "DNI",
    "documento_identidad": "1032456789",
    "numero_historia_clinica": "72769512",
    "apellido_paterno": "Pérez",
    "apellido_materno": "Rodríguez",
    "nombres": "Juan",
    "fecha_nacimiento": "1965-05-20",
    "sexo": "M",
    "telefono": "987654321",
    "direccion": "Av. Principal 123",
    "distrito_id": 1,
    "localidad_id": 1,
    "tipo_seguro": "SIS",
    "codigo_afiliacion_seguro": "040-2-1032456789",
    "talla_cm": 172.5,
    "peso_kg": 85.3
}
```

> Los `distrito_id` y `localidad_id` se eligen de los dropdowns cargados desde `/api/v1/catalogos/*`. El admin gestiona esos catálogos (crear/editar/desactivar) desde `/api/v1/admin/distritos` y `/api/v1/admin/localidades`.

## Estructura de un Request de Evaluación

```json
{
    "paciente_id": 1,
    "edad": 55,
    "presion_alta": true,
    "colesterol_alto": true,
    "tabaquismo": false,
    "actividad_fisica": true,
    "antecedente_acv": false,
    "diabetes": true,
    "salud_general": 3,
    "dificultad_para_caminar": false
}
```

## Respuesta con Predicción

```json
{
    "id": 1,
    "paciente_id": 1,
    "usuario_id": 1,
    "edad": 55,
    "presion_alta": true,
    "colesterol_alto": true,
    "tabaquismo": false,
    "actividad_fisica": true,
    "antecedente_acv": false,
    "diabetes": true,
    "salud_general": 3,
    "dificultad_para_caminar": false,
    "probabilidad": 0.734521,
    "clasificacion": "alto",
    "modelo_version": "1.0.0",
    "triaje_clinico": {
        "nivel_alerta": "ALTA PRIORIDAD - RIESGO ELEVADO",
        "codigo_color": "rojo",
        "accion_sugerida": "Priorizar atención médica. Evaluación por Cardiología requerida.",
        "factores_riesgo_detectados": ["Hipertensión Arterial", "Dislipidemia (Colesterol Alto)"],
        "factores_protectores": ["No Fumador"],
        "recomendaciones_medicas": ["Realizar Electrocardiograma (ECG) de base de inmediato."]
    },
    "created_at": "2025-01-15T10:30:00"
}
```

## Clasificación de Riesgo

| Probabilidad | Clasificación | Acción sugerida |
|-------------|---------------|-----------------|
| < 30% | **Bajo** | Seguimiento rutinario |
| 30% - 60% | **Moderado** | Evaluación adicional |
| > 60% | **Alto** | Atención inmediata |

## Notas para el Desarrollo

- **Dependencias**: `requirements.txt` (producción) y `requirements-dev.txt` (tests, solo desarrollo). `bcrypt` está fijado a `4.0.1` porque passlib 1.7.4 no lee versiones de bcrypt ≥ 4.1 (ruido en el log).
- **ML deshabilitado temporalmente**: El endpoint de evaluaciones funcionará cuando se entrene el modelo y se guarde como `app/resources/modelo_cardiaco.joblib`
- **Sin imágenes**: El análisis de imágenes médicas está en "Fase 2" (futuro)
- **Dataset**: Heart Disease Health Indicators (CDC/BRFSS, Kaggle)

## Licencia

Proyecto académico — HealthCure CardioPredict
