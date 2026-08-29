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

## Endpoints Disponibles

### Auth (públicos)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Registrar usuario nuevo |
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

### Admin (requiere JWT + rol admin)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/admin/usuarios` | Listar todos los usuarios |
| PUT | `/api/v1/admin/usuarios/{id}/deactivate` | Desactivar usuario |

## Flujo de Uso Típico

```
1. POST /api/v1/auth/register   → Crear cuenta de usuario
2. POST /api/v1/auth/login      → Obtener token JWT
3. POST /api/v1/pacientes/      → Registrar paciente
4. POST /api/v1/evaluaciones/   → Evaluar riesgo cardíaco
5. GET  /api/v1/evaluaciones/   → Ver historial
```

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

- **ML deshabilitado temporalmente**: El endpoint de evaluaciones funcionará cuando se entrene el modelo y se guarde como `app/resources/modelo_cardiaco.joblib`
- **Sin imágenes**: El análisis de imágenes médicas está en "Fase 2" (futuro)
- **Dataset**: Heart Disease Health Indicators (CDC/BRFSS, Kaggle)

## Licencia

Proyecto académico — HealthCure CardioPredict
