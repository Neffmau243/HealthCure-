# HealthCure — CardioPredict

Sistema web de triaje cardíaco con **predicción automática usando Machine Learning** y **triaje clínico determinista** que traduce los resultados del modelo en instrucciones accionables para médicos y enfermeros.

> 🩺 **Lo que hace:** Un médico/técnico de salud ingresa los datos de un paciente → el sistema predice el **riesgo cardíaco** con ML (Random Forest/XGBoost) → y genera automáticamente un **triaje clínico** con nivel de alerta, código de color, factores de riesgo/protectores y recomendaciones médicas.

```
Paciente → Datos clínicos → Modelo ML → Probabilidad + Clasificación → TRIAJE CLÍNICO
```

---

## ✨ Qué hay ahora mismo

| Feature | Estado |
|---------|--------|
| Predicción ML (probabilidad + clasificación) | ✅ Funcionando |
| **Triaje Clínico Automático** | ✅ **Implementado** |
| Endpoints REST (FastAPI + Swagger) | ✅ Funcionando |
| Autenticación JWT + roles (admin/médico/enfermera) | ✅ Funcionando |
| Gestión de pacientes | ✅ Funcionando |
| Catálogos (distritos/localidades) | ✅ Funcionando |
| Admin (gestión de usuarios + catálogos) | ✅ Funcionando |
| Tests (pytest, SQLite en memoria) | ✅ Cubiertos |
| Migraciones SQL | ✅ Incluidas |
| Postman collection | ✅ Incluido |
| Entrenamiento de modelo | ✅ Script incluido |

---

## 🏗️ Arquitectura del Backend

```
app/
├── models/          → Entidades SQLAlchemy (tablas MySQL)
├── schemas/         → DTOs de entrada/salida (Pydantic v2)
├── repositories/    → Acceso a la base de datos
├── mappers/         → Traductor entre capas
├── ml/              → Modelo ML (predictor + clasificador)
├── services/        → Lógica de negocio
│   ├── evaluacion_service.py        → Orquesta evaluaciones
│   └── evaluacion_triaje_service.py → ★ Motor de triaje clínico ★
├── api/             → Endpoints HTTP (FastAPI)
├── core/            → Configuración y base de datos
├── exceptions/      → Excepciones personalizadas
├── resources/       → Modelo .joblib, SQL, CSV, migraciones
│   └── migrations/
│       └── 001_triaje_clinico.sql
└── tests/           → Tests con SQLite en memoria
```

### Capas (de afuera hacia adentro)

```
API Controller → Service → Repository → MySQL
                    ↓
                 Mapper ↔ ML Predictor
                    ↓
              Triaje Clínico (determinista)
```

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|------------|-----------|
| Backend | Python 3.10+ + **FastAPI** |
| Base de datos | MySQL 8.0+ |
| ORM | SQLAlchemy |
| Validación | Pydantic v2 |
| Autenticación | JWT (python-jose) |
| Contraseñas | bcrypt (passlib) |
| ML | Random Forest / XGBoost (scikit-learn) |
| Tests | pytest + httpx |
| Documentación API | Swagger UI automático |

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/Neffmau243/HealthCure-.git
cd HealthCure-
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
pip install -r requirements-dev.txt   # pytest + httpx
```

### 4. Configurar base de datos

```sql
CREATE DATABASE healthcure_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
```

Ejecutar el script SQL:

```bash
mysql -u root -p healthcure_db < app/resources/schema.sql
```

> **Si tu BD ya existe** (creada con schema.sql anterior), aplica la migración de triaje:
> ```bash
> mysql -u root -p healthcure_db < app/resources/migrations/001_triaje_clinico.sql
> ```

### 5. Configurar variables de entorno

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

### 7. Verificar

Abre **http://localhost:8000/docs** → Swagger UI con todos los endpoints.

### 8. Correr los tests

```bash
python -m pytest app/tests -v
```

Los tests usan **SQLite en memoria** — no necesitan MySQL levantado.

---

## 📡 Endpoints Disponibles

### Auth (públicos)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Registrar usuario (SIEMPRE rol `usuario`) |
| POST | `/api/v1/auth/login` | Login → token JWT |
| GET | `/api/v1/auth/me` | Datos del usuario autenticado |

### Pacientes (requiere JWT)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/pacientes/` | Listar todos |
| GET | `/api/v1/pacientes/search?documento=1234` | Buscar por documento |
| GET | `/api/v1/pacientes/{id}` | Obtener por ID |
| POST | `/api/v1/pacientes/` | Registrar paciente nuevo |
| PUT | `/api/v1/pacientes/{id}` | Actualizar datos |

### Evaluaciones Cardíacas (requiere JWT)

| Método | Ruta | Descripción |
|--------|------|-------------|
| **POST** | `/api/v1/evaluaciones/` | **Crear evaluación + predicción ML + TRIAJE CLÍNICO** |
| GET | `/api/v1/evaluaciones/` | Listar todas (paginado) |
| GET | `/api/v1/evaluaciones/{id}` | Ver una evaluación |
| GET | `/api/v1/evaluaciones/by-paciente/{id}` | Historial de un paciente |

### Catálogos (requiere JWT)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/catalogos/distritos` | Distritos activos |
| GET | `/api/v1/catalogos/localidades?distrito_id=1` | Localidades activas |

### Admin (requiere JWT + rol admin)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET/POST | `/api/v1/admin/usuarios*` | Gestión de usuarios |
| GET/POST | `/api/v1/admin/distritos*` | Gestión de distritos |
| GET/POST | `/api/v1/admin/localidades*` | Gestión de localidades |

> **Seguridad admin:** el registro público no acepta campo `rol`. Un admin no puede desactivar su propia cuenta ni quitarse el rol. Nadie puede desactivar al último administrador activo.

---

## 🩺 Flujo de Uso Típico

```
1. POST /api/v1/auth/register   → Crear cuenta
2. POST /api/v1/auth/login      → Obtener token JWT
3. GET  /api/v1/catalogos/distritos → Cargar dropdowns
4. POST /api/v1/pacientes/      → Registrar paciente
5. POST /api/v1/evaluaciones/   → Evaluar riesgo + obtener triaje clínico
6. GET  /api/v1/evaluaciones/   → Ver historial
```

---

## 🧪 Credenciales de Prueba (seed automático)

Al levantar el servidor (BD vacía), se crean:

| Rol | Email | Password |
|-----|-------|----------|
| Admin | `admin@healthcure.com` | `admin123` |
| Médico | `dr.garcia@healthcure.com` | `doctor123` |
| Enfermera | `ana.martinez@healthcure.com` | `enfermera123` |

5 distritos, 15 localidades, 5 pacientes de ejemplo y 3 evaluaciones de prueba.

---

## 📋 Ejemplo de Evaluación + Triaje Clínico

### Request

```json
POST /api/v1/evaluaciones/
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

### Response (201 Created)

```json
{
    "id": 8,
    "paciente_id": 1,
    "usuario_id": 2,
    "edad": 55,
    "presion_alta": true,
    "colesterol_alto": true,
    "tabaquismo": false,
    "actividad_fisica": true,
    "antecedente_acv": false,
    "diabetes": true,
    "salud_general": 3,
    "dificultad_para_caminar": false,
    "probabilidad": 0.459186,
    "clasificacion": "moderado",
    "modelo_version": "1.0.0",
    "triaje_clinico": {
        "nivel_alerta": "RIESGO MODERADO - SEGUIMIENTO PREVENTIVO",
        "codigo_color": "amarillo",
        "accion_sugerida": "Programar consulta médica de control en los próximos 15 a 30 días.",
        "factores_riesgo_detectados": [
            "Hipertensión Arterial",
            "Dislipidemia (Colesterol Alto)",
            "Diabetes Mellitus"
        ],
        "factores_protectores": [
            "Realiza Actividad Física Regular",
            "No Fumador"
        ],
        "recomendaciones_medicas": [
            "Solicitar perfil lipídico y examen de glucosa en ayunas.",
            "Monitoreo ambulatorio de presión arterial durante 1 semana.",
            "Reforzar cambios en el estilo de vida (dieta cardioprotectora)."
        ]
    },
    "created_at": "2026-09-05T08:30:13"
}
```

---

## 🎯 Clasificación de Riesgo

| Probabilidad | Clasificación | Nivel de Alerta | Semáforo |
|-------------|---------------|-----------------|----------|
| < 30% | **Bajo** | BAJO RIESGO - CONTROL DE RUTINA | 🟢 Verde |
| 30% - 60% | **Moderado** | RIESGO MODERADO - SEGUIMIENTO PREVENTIVO | 🟡 Amarillo |现状 |
| > 60% | **Alto** | ALTA PRIORIDAD - RIESGO ELEVADO | 🔴 Rojo |

---

## 🧠 ¿Qué es el triaje clínico?

Es el **corazón diferenciador** de HealthCure. Mientras el modelo ML dice _"0.459 → moderado"_, el sistema de triaje clínico traduce eso a información que un médico puede usar **inmediatamente**:

- **¿Qué tan rápido actuar?** → `nivel_alerta`
- **Semáforo visual** → `codigo_color` (verde/amarillo/rojo)
- **¿Por qué dio ese riesgo?** → `factores_riesgo_detectados`
- **¿Qué se está haciendo bien?** → `factores_protectores`
- **Próximos pasos clínicos** → `accion_sugerida` + `recomendaciones_medicas`

> **Diseño:** 100% determinista — mismos inputs → mismo triaje. Sin dependencias externas, sin HTML, sin estilos. El texto clínico vive en un solo archivo: `app/services/evaluacion_triaje_service.py`.

---

## 📂 Estructura de un Request de Evaluación

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

---

## 📝 Notas de Desarrollo

- **Dependencias:** `requirements.txt` (producción) y `requirements-dev.txt` (tests). `bcrypt` está fijado a `4.0.1` por compatibilidad con passlib 1.7.4.
- **Dataset:** Heart Disease Health Indicators (CDC/BRFSS 2015, Kaggle)
- **Entrenamiento:** `entrenar_modelo.py` — entrena y guarda el modelo como `app/resources/modelo_cardiaco.joblib`
- **Postman:** `postman/HealthCure_API.postman_collection.json` con todos los endpoints
- **BD nueva:** `schema.sql` ya incluye las columnas de triaje
- **BD existente:** aplicar `app/resources/migrations/001_triaje_clinico.sql`

---

## 📚 Documentación Adicional

- **Triaje Clínico detallado:** [`docs/TRIAGE_CLINICO.md`](docs/TRIAGE_CLINICO.md) — Arquitectura, reglas clínicas, flujo completo, compatibilidad con evaluaciones antiguas y guía de extensión.

---

## 🎯 Proyecto Academico — HealthCure CardioPredict

Licencia: Proyecto académico
