# HealthCure — CardioPredict: Mapeo Completo y Estado del Proyecto

> Documento técnico de referencia: arquitectura, rutas, flujos, CRUD, datos de entrada/salida, estado actual del modelo ML, y tareas pendientes.
> Generado a partir del código fuente actual del proyecto (revisión completa).

---

## Tabla de Contenidos

1. [Resumen del Proyecto](#1-resumen-del-proyecto)
2. [Estructura de Directorios](#2-estructura-de-directorios)
3. [Arquitectura de Capas](#3-arquitectura-de-capas)
4. [Base de Datos (MySQL)](#4-base-de-datos-mysql)
5. [Autenticación (JWT)](#5-autenticacion-jwt)
6. [Endpoints — Rutas Completas](#6-endpoints--rutas-completas)
7. [Flujo por Endpoint](#7-flujo-por-endpoint)
8. [Mapa de CRUD](#8-mapa-de-crud)
9. [Machine Learning (ML)](#9-machine-learning-ml)
10. [Seguridad](#10-seguridad)
11. [Seed de Datos de Prueba](#11-seed-de-datos-de-prueba)
12. [Matriz de Permisos](#12-matriz-de-permisos)
13. [Stack Tecnológico](#13-stack-tecnologico)
14. [Estado Actual del Proyecto](#14-estado-actual-del-proyecto)
15. [Tareas Pendientes](#15-tareas-pendientes)

---

## 1. Resumen del Proyecto

| Campo | Valor |
|-------|-------|
| **Nombre** | HealthCure — CardioPredict |
| **Propósito** | Sistema web de triaje cardíaco con predicción automática usando ML |
| **Stack** | Python + FastAPI + MySQL + Random Forest/XGBoost |
| **Roles** | `admin` (gestiona usuarios y catálogos) · `usuario` (médico/enfermera — registra pacientes y evalúa) |
| **Estado** | MVP funcional — **modelo ML entrenado y operativo** |

**Descripción:** Un médico/técnico de salud ingresa los datos de un paciente y el sistema automáticamente predice el **riesgo cardíaco** usando un modelo de Random Forest entrenado con el dataset CDC/BRFSS 2015.

```
Paciente → Datos clínicos → Modelo ML → Probabilidad + Clasificación de riesgo
```

---

## 2. Estructura de Directorios

```
ProyInno/
│
├── app/                                  # Paquete principal de la aplicación
│   ├── __init__.py                       # Vacío
│   ├── api/
│   │   ├── __init__.py                   # Vacío
│   │   ├── deps.py                       # Dependencias compartidas (JWT, role checks)
│   │   └── v1/
│   │       ├── __init__.py               # Vacío
│   │       ├── auth.py                   # Endpoints de autenticación
│   │       ├── pacientes.py              # Endpoints CRUD de pacientes
│   │       ├── evaluaciones.py           # Endpoints de evaluaciones (ML)
│   │       ├── admin.py                  # Endpoints de administración
│   │       └── catalogos.py              # Endpoints de catálogos (read-only para doctores)
│   ├── clients/
│   │   └── __init__.py                   # Vacío — SIN implementar
│   ├── core/
│   │   ├── __init__.py                   # Vacío
│   │   ├── config.py                     # Configuración central (Pydantic Settings)
│   │   └── database.py                   # Motor SQLAlchemy, session, get_db()
│   ├── exceptions/
│   │   ├── __init__.py                   # Vacío
│   │   └── ml_exceptions.py              # Excepciones personalizadas del ML
│   ├── mappers/
│   │   ├── __init__.py                   # Vacío
│   │   └── evaluacion_mapper.py          # Traductor entre DTO → ML → ORM → Response
│   ├── ml/
│   │   ├── __init__.py                   # Vacío
│   │   ├── model_loader.py               # Singleton que carga modelo .joblib en RAM
│   │   ├── predictor.py                  # Ejecuta pipeline de predicción
│   │   └── preprocessor.py               # Limpia, valida y ordena datos para el modelo
│   ├── models/
│   │   ├── __init__.py                   # Importa todos los modelos ORM
│   │   ├── usuario.py                    # Entidad Usuario
│   │   ├── paciente.py                   # Entidad Paciente
│   │   ├── evaluacion.py                 # Entidad Evaluación
│   │   ├── distrito.py                   # Entidad Distrito
│   │   └── localidad.py                  # Entidad Localidad
│   ├── repositories/
│   │   ├── __init__.py                   # Vacío
│   │   ├── usuario_repository.py         # CRUD de usuarios
│   │   ├── paciente_repository.py        # CRUD de pacientes
│   │   ├── evaluacion_repository.py      # CRUD de evaluaciones
│   │   ├── distrito_repository.py        # CRUD de distritos
│   │   └── localidad_repository.py       # CRUD de localidades
│   ├── resources/
│   │   ├── __init__.py                   # Vacío
│   │   ├── schema.sql                    # DDL completo de MySQL (5 tablas)
│   │   └── modelo_cardiaco.joblib        # ⭐ Modelo ML entrenado (15.7 MB)
│   ├── schemas/
│   │   ├── __init__.py                   # Vacío
│   │   ├── usuario.py                    # DTOs: UsuarioCreate, Login, Response, Token
│   │   ├── paciente.py                   # DTOs: PacienteCreate, Update, Response
│   │   ├── evaluacion.py                 # DTOs: EvaluacionCreate, Response, ClasificacionEnum
│   │   └── catalogo.py                   # DTOs: DistritoCreate/Update/Response, LocalidadCreate/Update/Response
│   ├── seeds/
│   │   ├── __init__.py                   # "Seeds — Paquete de datos de prueba"
│   │   └── seed.py                       # Datos de prueba automáticos (3 users, 5 distritos, etc.)
│   ├── services/
│   │   ├── __init__.py                   # Vacío
│   │   ├── auth_service.py               # Registro, login, JWT, bcrypt
│   │   ├── paciente_service.py           # CRUD pacientes + permisos
│   │   ├── evaluacion_service.py         # Orquesta: validar paciente → ML → guardar
│   │   ├── admin_service.py              # Gestión de usuarios y catálogos (admin)
│   │   └── catalogo_service.py           # Servicio de catálogos (solo lectura)
│   └── tests/
│       ├── __init__.py                   # Vacío
│       ├── conftest.py                   # Fixtures: SQLite en memoria, TestClient, helpers
│       ├── test_evaluacion_mapper.py     # Tests del mapper de evaluaciones
│       ├── test_preprocessor.py          # Tests del preprocessor (column order, edad CDC)
│       └── test_permisos_pacientes.py    # Tests de permisos y anti-lockout
│
├── docs/
│   ├── MAPPEO_BACKEND.md                 # Documentación técnica detallada (1342 líneas)
│   └── MAPPEO_Y_ESTADO_DEL_PROYECTO.md   # ⭐ Este archivo
│
├── postman/
│   └── HealthCure_API.postman_collection.json
│
├── entrenar_modelo.py                    # Script para entrenar el modelo ML
├── main.py                               # Punto de entrada de FastAPI
├── requirements.txt                      # Dependencias de producción
├── requirements-dev.txt                  # Dependencias de desarrollo (pytest, httpx)
├── .env                                  # Variables de entorno (con credenciales)
├── .env.example                          # Plantilla de variables de entorno
├── .gitignore                            # Archivos ignorados por git
├── _sintetico_brfss.csv                  # Dataset sintético de prueba
├── heart_disease_health_indicators_BRFSS2015.csv  # ⭐ Dataset original de entrenamiento (22.7 MB)
└── README.md                             # Documentación principal del proyecto
```

---

## 3. Arquitectura de Capas

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                          │
│                    (Fase 2 — por crear)                       │
└──────────────────────────┬──────────────────────────────────┘
                            │ HTTP (JSON)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  6. API (Controllers)     app/api/v1/                        │
│     Recibe request → llama al service → retorna response     │
│     NO tiene lógica de negocio                               │
└──────────────────────────┬──────────────────────────────────┘
                            │ Depends(get_db) + Depends(get_current_user)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Service              app/services/                       │
│     Lógica de negocio + orquestación                         │
│     El ÚNICO que puede hablar con Repository + ML            │
└──────────┬─────────────────────────────┬────────────────────┘
           │                             │
           ▼                             ▼
┌─────────────────────┐    ┌──────────────────────────────────┐
│  2. Repository       │    │  4. Mapper + ML                   │
│  app/repositories/   │    │  app/mappers/ + app/ml/           │
│  Solo habla con BD   │    │  Traduce entre capas + predice    │
└──────────┬──────────┘    └──────────┬───────────────────────┘
           │                          │
           ▼                          ▼
┌─────────────────────┐    ┌──────────────────────────────────┐
│  1. Models (ORM)     │    │  3. ML Model (.joblib)            │
│  app/models/         │    │  app/resources/modelo_cardiaco    │
│  SQLAlchemy → MySQL  │    │  Random Forest/XGBoost entrenado  │
└─────────────────────┘    └──────────────────────────────────┘
```

**Regla de oro:** Cada capa solo sabe de la capa de abajo. Nunca se salta.

---

## 4. Base de Datos (MySQL)

### 4.1 Diagrama ER

```
┌──────────────────────┐        ┌──────────────────────────────┐
│      usuarios          │        │        pacientes               │
├──────────────────────┤        ├──────────────────────────────┤
│ id          BIGINT PK │        │ id              BIGINT PK     │
│ nombre      VARCHAR   │        │ nombre          VARCHAR       │
│ email       VARCHAR U │        │ documento_ident VARCHAR U     │
│ password_ha VARCHAR   │        │ fecha_nacimiento DATE         │
│ rol         ENUM      │        │ sexo            ENUM(M/F)     │
│ activo      BOOLEAN   │        │ usuario_creador_id BIGINT FK │
│ created_at  DATETIME  │        │ talla_cm        DECIMAL       │
│ updated_at  DATETIME  │        │ peso_kg         DECIMAL       │
└──────┬───────────────┘        │ created_at      DATETIME      │
        │                        │ updated_at      DATETIME      │
        │  1:N                   └──────────┬──────────────────┘
        │                                   │
        │                                   │  1:N
        │                                   │
        ▼                                   ▼
┌──────────────────────────────────────────────────────────────┐
│                       evaluaciones                             │
├──────────────────────────────────────────────────────────────┤
│ id                  BIGINT PK                                 │
│ paciente_id         BIGINT FK → pacientes.id                  │
│ usuario_id          BIGINT FK → usuarios.id                   │
│ edad                SMALLINT                                   │
│ presion_alta        BOOLEAN                                    │
│ colesterol_alto     BOOLEAN                                    │
│ tabaquismo          BOOLEAN                                    │
│ actividad_fisica    BOOLEAN                                    │
│ antecedente_acv     BOOLEAN                                    │
│ diabetes            BOOLEAN                                    │
│ salud_general       SMALLINT (1-5)                             │
│ dificultad_para_caminar BOOLEAN                                │
│ probabilidad        DECIMAL(7,6)  ← resultado del ML       │
│ clasificacion       ENUM(bajo/moderado/alto) ← resultado ML │
│ modelo_version      VARCHAR(50)                                │
│ created_at          DATETIME                                   │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Tipos de Columna MySQL

| Tabla | Columna | Tipo MySQL | Equivalente Python | Notas |
|-------|---------|------------|-------------------|-------|
| usuarios | id | `BIGINT` | `BigInteger` | Auto-increment |
| usuarios | email | `VARCHAR(255)` | `String(255)` | UNIQUE + INDEX |
| usuarios | password_hash | `VARCHAR(255)` | `String(255)` | bcrypt hash |
| usuarios | rol | `ENUM('admin','usuario')` | `Enum(...)` | Default 'usuario' |
| pacientes | documento_identidad | `VARCHAR(30)` | `String(30)` | UNIQUE + INDEX |
| pacientes | fecha_nacimiento | `DATE` | `Date` | Formato ISO |
| pacientes | sexo | `ENUM('M','F')` | `Enum(...)` | M/F |
| pacientes | usuario_creador_id | `BIGINT` | `BigInteger` | FK implícito a usuarios.id |
| pacientes | talla_cm | `DECIMAL(5,1)` | `Numeric(5,1)` | Nullable (opcional) |
| pacientes | peso_kg | `DECIMAL(5,1)` | `Numeric(5,1)` | Nullable (opcional) |
| evaluaciones | edad | `SMALLINT` | `SmallInteger` | 1-120 |
| evaluaciones | salud_general | `SMALLINT` | `SmallInteger` | 1-5 (escala CDC) |
| evaluaciones | probabilidad | `DECIMAL(7,6)` | `Numeric(7,6)` | 0.000000 - 1.000000 |
| evaluaciones | clasificacion | `ENUM('bajo','moderado','alto')` | `Enum(...)` | Calculado del ML |

### 4.3 Índices

| Tabla | Índice | Columna | Propósito |
|-------|--------|---------|-----------|
| usuarios | `ix_usuarios_email` | email | Login rápido por email |
| pacientes | `ix_pacientes_documento` | documento_identidad | Búsqueda por documento |
| pacientes | `ix_pacientes_usuario_creador` | usuario_creador_id | Búsqueda por quien creó |
| evaluaciones | `ix_evaluaciones_paciente_id` | paciente_id | Historial por paciente |
| evaluaciones | `ix_evaluaciones_created_at` | created_at | ORDER BY para listados |

### 4.4 Foreign Keys

| Tabla | Columna | Referencia | ON DELETE |
|-------|---------|------------|-----------|
| evaluaciones | paciente_id | pacientes.id | RESTRICT (no borrar paciente con evaluaciones) |
| evaluaciones | usuario_id | usuarios.id | RESTRICT (no borrar usuario con evaluaciones) |
| pacientes | usuario_creador_id | usuarios.id | NO ACTION (nullable, compatibilidad) |

---

## 5. Autenticación (JWT)

### 5.1 Flujo de Login

```
Frontend                     Backend                         MySQL
    │                            │                               │
    │  POST /auth/login          │                               │
    │  {email, password}         │                               │
    │ ──────────────────────────→│                               │
    │                            │  SELECT * WHERE email=?       │
    │                            │ ─────────────────────────────→│
    │                            │ ←─────────────────────────────│
    │                            │                               │
    │                            │  bcrypt.verify(password, hash)│
    │                            │  → True si coincide           │
    │                            │                               │
    │                            │  jwt.encode({sub:id, rol})   │
    │                            │                               │
    │  ← {access_token, user}   │                               │
    │                            │                               │
```

### 5.2 Flujo de Request Autenticado

```
Frontend                     Backend (deps.py)                MySQL
    │                            │                               │
    │  GET /api/v1/pacientes/  │                               │
    │  Authorization: Bearer xxx │                               │
    │ ──────────────────────────→│                               │
    │                            │                               │
    │                            │  jwt.decode(token)            │
    │                            │  → payload = {sub: 1, rol:..}│
    │                            │                               │
    │                            │  SELECT * WHERE id=sub        │
    │                            │ ─────────────────────────────→│
    │                            │ ←─────────────────────────────│
    │                            │                               │
    │                            │  if not activo → 401          │
    │                            │                               │
    │  ← Response JSON           │                               │
```

### 5.3 Variables de Configuración

| Variable | Valor por defecto | Descripción |
|----------|-------------------|-------------|
| `JWT_SECRET_KEY` | `CHANGE-THIS-IN-PRODUCTION-...` | Clave de firma HMAC-SHA256 |
| `JWT_ALGORITHM` | `HS256` | Algoritmo de firma |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token válido por 1 hora |

### 5.4 Cómo se Envía el Token

```
Header: Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 6. Endpoints — Rutas Completas

### 6.1 Tabla Resumen

| # | Método | Ruta | Auth | Rol | Descripción | Status Codes |
|---|--------|------|------|-----|-------------|--------------|
| 1 | `GET` | `/health` | No | — | Health check del servidor | 200 |
| 2 | `POST` | `/api/v1/auth/register` | No | — | Registrar usuario nuevo (SIEMPRE rol `usuario`) | 201, 409, 422 |
| 3 | `POST` | `/api/v1/auth/login` | No | — | Login → JWT | 200, 401, 422 |
| 4 | `GET` | `/api/v1/auth/me` | Si | Cualquiera | Datos del usuario autenticado | 200, 401 |
| 5 | `GET` | `/api/v1/pacientes/` | Si | Cualquiera | Listar todos los pacientes | 200, 401 |
| 6 | `GET` | `/api/v1/pacientes/search` | Si | Cualquiera | Búsqueda parcial por documento | 200, 401 |
| 7 | `GET` | `/api/v1/pacientes/by-documento/{doc}` | Si | Cualquiera | Buscar por documento exacto | 200, 401, 404 |
| 8 | `GET` | `/api/v1/pacientes/{id}` | Si | Cualquiera | Obtener por ID | 200, 401, 404 |
| 9 | `POST` | `/api/v1/pacientes/` | Si | Cualquiera | Registrar paciente nuevo | 201, 401, 409, 422 |
| 10 | `PUT` | `/api/v1/pacientes/{id}` | Si | Creador o admin | Actualizar datos (parcial) | 200, 401, 403, 404, 422 |
| 11 | `POST` | `/api/v1/evaluaciones/` | Si | Cualquiera | **Crear evaluación (predicción ML)** | 201, 400, 401, 500 |
| 12 | `GET` | `/api/v1/evaluaciones/` | Si | Cualquiera | Listar evaluaciones (paginado) | 200, 401 |
| 13 | `GET` | `/api/v1/evaluaciones/by-paciente/{id}` | Si | Cualquiera | Historial de un paciente | 200, 401 |
| 14 | `GET` | `/api/v1/evaluaciones/{id}` | Si | Cualquiera | Ver una evaluación | 200, 401, 404 |
| 15 | `GET` | `/api/v1/admin/usuarios` | Si | **admin** | Listar todos los usuarios | 200, 401, 403 |
| 16 | `GET` | `/api/v1/admin/usuarios/{id}` | Si | **admin** | Obtener usuario por ID | 200, 401, 403, 404 |
| 17 | `POST` | `/api/v1/admin/usuarios` | Si | **admin** | Crear usuario (admin elige rol) | 201, 401, 403, 409, 422 |
| 18 | `PUT` | `/api/v1/admin/usuarios/{id}` | Si | **admin** | Actualizar usuario (parcial, con guards anti-lockout) | 200, 401, 403, 404, 409, 422 |
| 19 | `PUT` | `/api/v1/admin/usuarios/{id}/activate` | Si | **admin** | Reactivar usuario | 200, 401, 403, 404 |
| 20 | `PUT` | `/api/v1/admin/usuarios/{id}/deactivate` | Si | **admin** | Desactivar usuario (soft delete) | 200, 401, 403, 404, 409 |
| 21 | `GET` | `/api/v1/catalogos/distritos` | Si | Cualquiera | Distritos ACTIVOS (dropdown) | 200, 401 |
| 22 | `GET` | `/api/v1/catalogos/localidades` | Si | Cualquiera | Localidades ACTIVAS (dropdown, filtro ?distrito_id=) | 200, 401 |
| 23 | `GET` | `/api/v1/admin/distritos` | Si | **admin** | Listar distritos (todos) | 200, 401, 403 |
| 24 | `POST` | `/api/v1/admin/distritos` | Si | **admin** | Crear distrito (catálogo) | 201, 401, 403, 409 |
| 25 | `PUT` | `/api/v1/admin/distritos/{id}` | Si | **admin** | Actualizar distrito (nombre/activo) | 200, 401, 403, 404, 409 |
| 26 | `PUT` | `/api/v1/admin/distritos/{id}/deactivate` | Si | **admin** | Desactivar distrito (soft delete) | 200, 401, 403, 404 |
| 27 | `GET` | `/api/v1/admin/localidades` | Si | **admin** | Listar localidades (filtro ?distrito_id=) | 200, 401, 403 |
| 28 | `POST` | `/api/v1/admin/localidades` | Si | **admin** | Crear localidad (catálogo) | 201, 401, 403, 409 |
| 29 | `PUT` | `/api/v1/admin/localidades/{id}` | Si | **admin** | Actualizar localidad | 200, 401, 403, 404, 409 |
| 30 | `PUT` | `/api/v1/admin/localidades/{id}/deactivate` | Si | **admin** | Desactivar localidad (soft delete) | 200, 401, 403, 404 |

### 6.2 Orden de Rutas (IMPORTANTE)

FastAPI procesa rutas en orden. Las rutas estáticas DEBEN ir antes de las dinámicas:

```
CORRECTO:
  GET /search        ← estática, se evalúa primero
  GET /by-documento  ← estática, se evalúa primero
  GET /{id}          ← dinámica, se evalúa después

INCORRECTO:
  GET /{id}          ← FastAPI interpreta "search" como un ID
  GET /search        ← NUNCA se alcanza
```

---

## 7. Flujo por Endpoint

### 7.1 `POST /api/v1/auth/register` — Registrar Usuario

```
DATOS DE ENTRADA (Body JSON):
{
    "nombre": "Dr. Garcia",          // str, 2-150 chars, obligatorio
    "email": "garcia@hospital.com",  // EmailStr, único, obligatorio
    "password": "mi_password"         // str, 6-128 chars, obligatorio
    // NO existe campo "rol" a propósito (seguridad)
}

FLUJO INTERNO:
  Controller → AuthService.register()
    → Valida que el email NO exista (UsuarioRepository.get_by_email)
    → Hashea la contraseña con bcrypt
    → Crea el usuario con rol="usuario" (SIEMPRE)
    → UsuarioRepository.create()

RESPUESTA (201):
{
    "id": 1, "nombre": "Dr. Garcia", "email": "garcia@hospital.com",
    "rol": "usuario", "activo": true, "created_at": "..."
}

ERRORES:
  409 → "Ya existe un usuario con ese email"
  422 → Validación de Pydantic
```

### 7.2 `POST /api/v1/auth/login` — Iniciar Sesión

```
DATOS DE ENTRADA (Body JSON):
{
    "email": "garcia@hospital.com",
    "password": "mi_password"
}

FLUJO INTERNO:
  Controller → AuthService.login()
    → UsuarioRepository.get_by_email(email)
    → Verifica que el usuario exista y esté activo
    → bcrypt.verify(password, password_hash) → True/False
    → Crea token JWT con {sub: id, rol: rol, exp: +60min}

RESPUESTA (200):
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "usuario": { "id": 1, "nombre": "...", "email": "...", "rol": "...", "activo": true }
}

ERRORES:
  401 → "Credenciales inválidas"
```

### 7.3 `POST /api/v1/evaluaciones/` — Crear Evaluación (ML) ⭐

Este es el endpoint MÁS IMPORTANTE del sistema.

```
DATOS DE ENTRADA (Body JSON):
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

FLUJO COMPLETO (6 pasos):

  PASO 1: Validar paciente
    PacienteRepository.get_by_id(1) → verificar que exista

  PASO 2: Mapper → ML Input Vector
    EvaluacionMapper.request_to_model_input(data)
    Transforma booleans → int (0/1) para el modelo
    Elimina paciente_id (el modelo no sabe de pacientes)

  PASO 3: Predictor → Probabilidad
    app.ml.predictor.predict(model_input)
    → Preprocessor: limpia + ordena columnas
    → model.predict_proba(df) → [[0.26, 0.74]]
    → Clasifica: 0.74 > 0.60 → "alto"

  PASO 4: Mapper → ORM Dict
    EvaluacionMapper.create_to_model(data, prediction, user)
    Combina: datos request + resultado ML + usuario_id

  PASO 5: Repository → Persistir en MySQL
    EvaluacionRepository.create(**dict)
    INSERT INTO evaluaciones (...)

  PASO 6: Mapper → Response DTO
    EvaluacionMapper.to_response(evaluacion_orm)
    Convierte Numeric→float, Enum→ClasificacionEnum

RESPUESTA (201):
{
    "id": 1, "paciente_id": 1, "usuario_id": 2,
    "edad": 55, "presion_alta": true, "colesterol_alto": true,
    "tabaquismo": false, "actividad_fisica": true,
    "antecedente_acv": false, "diabetes": true, "salud_general": 3,
    "dificultad_para_caminar": false,
    "probabilidad": 0.734521,
    "clasificacion": "alto",
    "modelo_version": "1.0.0",
    "created_at": "..."
}

ERRORES:
  400 → "Paciente no encontrado"
  500 → "Error ML: Modelo ML no disponible: [detalle]"
```

---

## 8. Mapa de CRUD

| Entidad | Create | Read (uno) | Read (listar) | Read (buscar) | Update | Delete |
|---------|--------|------------|---------------|---------------|--------|--------|
| **Usuarios** | `POST /auth/register` (público) + `POST /admin/usuarios` (admin) | `GET /auth/me` + `GET /admin/usuarios/{id}` (admin) | `GET /admin/usuarios` *(admin)* | — | `PUT /admin/usuarios/{id}` *(admin)* | `PUT /admin/{id}/deactivate` *(admin, soft)* + `PUT /admin/{id}/activate` *(admin)* |
| **Pacientes** | `POST /pacientes/` | `GET /pacientes/{id}` + `GET /by-documento/{doc}` | `GET /pacientes/` | `GET /search?documento=` | `PUT /pacientes/{id}` *(creador o admin)* | — |
| **Evaluaciones** | `POST /evaluaciones/` | `GET /evaluaciones/{id}` | `GET /evaluaciones/` *(paginado)* | `GET /by-paciente/{id}` | — | — |
| **Distritos** *(catálogo)* | `POST /admin/distritos` *(admin)* | — | `GET /admin/distritos` *(admin)* + `GET /catalogos/distritos` *(doctor)* | — | `PUT /admin/distritos/{id}` *(admin)* | `PUT /admin/distritos/{id}/deactivate` *(admin, soft)* |
| **Localidades** *(catálogo)* | `POST /admin/localidades` *(admin)* | — | `GET /admin/localidades` *(admin)* + `GET /catalogos/localidades` *(doctor)* | `GET /catalogos/localidades?distrito_id=` | `PUT /admin/localidades/{id}` *(admin)* | `PUT /admin/localidades/{id}/deactivate` *(admin, soft)* |

**Notas:**
- No hay DELETE duro en ninguna entidad (soft delete en usuarios/distritos/localidades)
- No hay UPDATE de evaluaciones (son inmutables — cada una es una instantánea)
- Los pacientes tienen permisos: solo el creador o un admin puede editarlos
- **Catálogos (distritos/localidades): el admin los gestiona (CRUD), el doctor solo los LEE**

---

## 9. Machine Learning (ML)

### 9.1 Pipeline del ML

```
┌─────────────────────────────────────────────────────────────┐
│                      CAPA ML                                  │
│                                                               │
│  ┌───────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │ preprocessor   │───→│ model_loader │───→│ predictor    │ │
│  │                │    │  (singleton) │    │              │ │
│  │ • Valida       │    │ • Carga      │    │ • predict()  │ │
│  │ • Ordena cols  │    │   .joblib    │    │ • Clasifica  │ │
│  │ • bool → int   │    │ • Cachea     │    │              │ │
│  └───────────────┘    └──────────────┘    └──────────────┘ │
│                                                               │
│  Input:  dict {"edad": 55, "presion_alta": 1, ...}      │
│  Output: PredictionResult(probabilidad=0.73, "alto")      │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Variables Predictoras (CDC/BRFSS Dataset)

| # | Variable | Tipo | Rango | Descripción |
|---|----------|------|-------|-------------|
| 1 | `edad` | int | 1-120 | Edad del paciente (convertida a código CDC 1-13) |
| 2 | `presion_alta` | bool→int | 0/1 | Diagnóstico de presión alta |
| 3 | `colesterol_alto` | bool→int | 0/1 | Colesterol alto diagnosticado |
| 4 | `tabaquismo` | bool→int | 0/1 | Fuma o fumó >=100 cigarrillos |
| 5 | `actividad_fisica` | bool→int | 0/1 | Hace actividad física en últimos 30 días |
| 6 | `antecedente_acv` | bool→int | 0/1 | Antecedente de accidente cerebrovascular |
| 7 | `diabetes` | bool→int | 0/1 | Diagnóstico de diabetes |
| 8 | `salud_general` | int | 1-5 | Escala CDC: 1=excelente, 5=mala |
| 9 | `dificultad_para_caminar` | bool→int | 0/1 | Dificultad para caminar subir escaleras |

**Orden de columnas que el modelo espera** (PREDEFINE en `preprocessor.py`):
```
edad → presion_alta → colesterol_alto → tabaquismo → actividad_fisica
→ antecedente_acv → diabetes → salud_general → dificultad_para_caminar
```

### 9.3 Clasificación de Riesgo

```
Probabilidad de enfermedad cardiaca:

0%                    30%                   60%                  100%
├─────────────────────┼─────────────────────┼────────────────────┤
│     BAJO RIESGO     │   RIESGO MODERADO   │    ALTO RIESGO     │
│     "bajo"          │     "moderado"      │      "alto"        │
│   < 0.30            │   0.30 - 0.60       │     > 0.60         │
└─────────────────────┴─────────────────────┴────────────────────┘
```

### 9.4 Modelo Actual (ENTRENADO ✅)

| Campo | Valor |
|-------|-------|
| **Algoritmo** | Random Forest (100 estimadores, max_depth=10, class_weight="balanced") |
| **Dataset** | Heart Disease Health Indicators (CDC/BRFSS 2015) |
| **Archivo** | `app/resources/modelo_cardiaco.joblib` (15.7 MB) |
| **Version** | `1.0.0` |
| **Estado** | ✅ **ENTRENADO Y OPERATIVO** |
| **Métricas** | Accuracy: 72.44% \| ROC AUC: 83.65% \| F1: 35.71% |
| **Filas entrenamiento** | 253,680 (20% test = 50,736) |
| **Clase positiva** | 23,893 (9.4% — dataset desbalanceado) |

### 9.5 Comportamiento con Modelo

Si el archivo `.joblib` existe (✅ ahora sí):
- `POST /evaluaciones/` → retorna **201** con predicción (probabilidad + clasificación)
- Todos los endpoints funcionan con ML activo

Si el archivo `.joblib` NO existe:
- Login, registro, pacientes → funcionan normal
- `POST /evaluaciones/` → retorna **500** con "Modelo ML no disponible"

### 9.6 Cómo Reentrenar el Modelo

```bash
# 1. Obtener el CSV (ya descargado en la raíz del proyecto)
# Archivo: heart_disease_health_indicators_BRFSS2015.csv

# 2. Ejecutar el entrenamiento
python entrenar_modelo.py heart_disease_health_indicators_BRFSS2015.csv

# 3. Reiniciar el servidor
uvicorn main:app --reload --port 8000

# 4. Probar
# POST /api/v1/evaluaciones/ → ahora responde 201 con predicción
```

---

## 10. Seguridad

### 10.1 Autenticación
- **JWT** (HS256) con token de 60 min de expiración
- **bcrypt** para hash de contraseñas (versión 4.0.1 por compatibilidad con passlib 1.7.4)

### 10.2 Roles y Permisos

| Rol | Permisos |
|-----|----------|
| `admin` | Acceso total: gestión de usuarios, catálogos, y todo |
| `usuario` | CRUD de pacientes (solo los que creó), evaluaciones, catálogos (solo lectura) |

### 10.3 Guards Anti-Lockout
- Un admin **no puede** desactivar su propia cuenta
- Un admin **no puede** quitarse su propio rol
- **Nadie** puede desactivar/degradar al último administrador activo (responde `409`)
- El registro público (`/auth/register`) **nunca** crea usuarios con rol `admin`

### 10.4 Permisos de Paciente
- **Admin**: puede editar cualquier paciente
- **Usuario (médico/enfermera)**: solo puede editar pacientes que él registró (`usuario_creador_id == su ID`)
- Pacientes legacy (sin creador): editables por cualquiera

---

## 11. Seed de Datos de Prueba

Ejecuta automáticamente al iniciar el servidor (`main.py` lifespan). Solo crea datos si la BD está vacía.

### 11.1 Usuarios Creados

| Nombre | Email | Password | Rol |
|--------|-------|----------|-----|
| Administrador | `admin@healthcure.com` | `admin123` | **admin** |
| Dr. Carlos Garcia | `dr.garcia@healthcure.com` | `doctor123` | usuario |
| Enfermera Ana Martinez | `ana.martinez@healthcure.com` | `enfermera123` | usuario |

### 11.2 Catálogos Creados (distritos y localidades)

| Distrito | Localidades |
|----------|-------------|
| Alto Selva Alegre | Chilpinilla, El Mirador, La Tomilla, Mariano Melgar |
| Cayma | Huachipa, La Pampilla, Trujamanes |
| Miraflores | Campina, El Golf, Lara |
| Yanahuara | La Perla, Mirador de Yanahuara |
| Cerro Colorado | El Progreso, La Mansión, Tahuaycani |

### 11.3 Pacientes Creados (5 de ejemplo)

Todos creados por Dr. Garcia (`usuario_creador_id = 2`):

| Apellidos, Nombres | Documento | H. Clinica | Distrito | Localidad | Seguro | Sexo |
|--------------------|-----------|------------|----------|-----------|--------|------|
| PEREZ RODRIGUEZ, Juan | 1032456789 | 72769512 | Alto Selva Alegre | Chilpinilla | SIS | M |
| LOPEZ QUISPE, Maria Fernanda | 1098765432 | 88123456 | Cayma | La Pampilla | EsSalud | F |
| GOMEZ CHAVEZ, Roberto Carlos | 1122334455 | 90345678 | Cerro Colorado | Tahuaycani | SIS | M |
| MARTINEZ ROJAS, Laura Daniela | 1055667788 | 76543210 | Yanahuara | Mirador de Yanahuara | Privado | F |
| SANCHEZ HUAMAN, Pedro Antonio | 1066778899 | 69988776 | Miraflores | El Golf | EsSalud | M |

### 11.4 Evaluaciones Creadas (3 de ejemplo — hardcodeadas)

| Paciente | Edad | Riesgo | Probabilidad | Clasificación | Factores clave |
|----------|------|--------|-------------|---------------|----------------|
| Juan Perez | 61 | Alto | 78.5% | **alto** | presión + colesterol + tabaquismo + diabetes |
| Maria Lopez | 48 | Moderado | 35.2% | **moderado** | solo presión alta, activa |
| Roberto Gomez | 71 | Alto | 92.1% | **alto** | presión + colesterol + ACV + diabetes + inmovilidad |

---

## 12. Matriz de Permisos

| Endpoint | Sin token | Token usuario | Token admin |
|----------|-----------|---------------|-------------|
| `GET /health` | Si 200 | Si 200 | Si 200 |
| `POST /auth/register` | Si 201 | Si 201 | Si 201 |
| `POST /auth/login` | Si 200 | Si 200 | Si 200 |
| `GET /auth/me` | No 401 | Si 200 | Si 200 |
| `GET /pacientes/` | No 401 | Si 200 | Si 200 |
| `GET /pacientes/search` | No 401 | Si 200 | Si 200 |
| `GET /pacientes/by-documento/{doc}` | No 401 | Si 200 | Si 200 |
| `GET /pacientes/{id}` | No 401 | Si 200 | Si 200 |
| `POST /pacientes/` | No 401 | Si 201 | Si 201 |
| `PUT /pacientes/{id}` | No 401 | **Solo si es el creador** | Si 200 |
| `POST /evaluaciones/` | No 401 | Si 201 | Si 201 |
| `GET /evaluaciones/` | No 401 | Si 200 | Si 200 |
| `GET /evaluaciones/by-paciente/{id}` | No 401 | Si 200 | Si 200 |
| `GET /evaluaciones/{id}` | No 401 | Si 200 | Si 200 |
| `GET /catalogos/distritos` | No 401 | Si 200 | Si 200 |
| `GET /catalogos/localidades` | No 401 | Si 200 | Si 200 |
| `GET /admin/distritos` | No 401 | No 403 | Si 200 |
| `POST /admin/distritos` | No 401 | No 403 | Si 201 |
| `PUT /admin/distritos/{id}` | No 401 | No 403 | Si 200 |
| `PUT /admin/distritos/{id}/deactivate` | No 401 | No 403 | Si 200 |
| `GET /admin/localidades` | No 401 | No 403 | Si 200 |
| `POST /admin/localidades` | No 401 | No 403 | Si 201 |
| `PUT /admin/localidades/{id}` | No 401 | No 403 | Si 200 |
| `PUT /admin/localidades/{id}/deactivate` | No 401 | No 403 | Si 200 |
| `GET /admin/usuarios` | No 401 | No 403 | Si 200 |
| `GET /admin/usuarios/{id}` | No 401 | No 403 | Si 200 |
| `POST /admin/usuarios` | No 401 | No 403 | Si 201 |
| `PUT /admin/usuarios/{id}` | No 401 | No 403 | Si 200 |
| `PUT /admin/usuarios/{id}/activate` | No 401 | No 403 | Si 200 |
| `PUT /admin/usuarios/{id}/deactivate` | No 401 | No 403 | Si 200 |

---

## 13. Stack Tecnológico

| Componente | Tecnología | Versión |
|------------|-----------|---------|
| Backend | Python + FastAPI | 0.115+ |
| Base de datos | MySQL | 8.0+ |
| ORM | SQLAlchemy | 2.0+ |
| Validación | Pydantic v2 | 2.9+ |
| Autenticación | JWT (python-jose) | 3.3+ |
| Contraseñas | bcrypt (passlib) | 4.0.1 |
| ML | Random Forest (scikit-learn) | 1.5+ |
| ML备选 | XGBoost | 2.1+ |
| Procesamiento | pandas | 2.2+ |
| Serialización | joblib | 1.4+ |
| Servidor | uvicorn | 0.30+ |
| Testing | pytest + httpx | 8.0+ / 0.27+ |
| Documentación | Swagger UI / ReDoc | integrado en FastAPI |
| Cliente API | Postman | colección incluida |

---

## 14. Estado Actual del Proyecto

### ✅ Completado

| Elemento | Estado |
|----------|--------|
| Backend completo (30 endpoints) | ✅ |
| Autenticación JWT + roles | ✅ |
| CRUD de pacientes, evaluaciones, catálogos, administración | ✅ |
| Permisos granulares (anti-lockout, creador-only, soft delete) | ✅ |
| Tests con SQLite en memoria (`pytest app/tests -v`) | ✅ |
| Documentación (README.md + MAPPEO_BACKEND.md) | ✅ |
| Postman collection | ✅ |
| Estructura de ML preparada (preprocessor, predictor, model_loader) | ✅ |
| **Modelo ML entrenado** (`modelo_cardiaco.joblib`) | ✅ |
| Dataset descargado (`heart_disease_health_indicators_BRFSS2015.csv`) | ✅ |
| Script de entrenamiento (`entrenar_modelo.py`) | ✅ |
| Configuración `.env` | ✅ |
| `.gitignore` configurado | ✅ |

### ⚠️ ML — Entrenado y Operativo

| Detalle | Valor |
|---------|-------|
| Modelo | `app/resources/modelo_cardiaco.joblib` (15.7 MB) |
| Algoritmo | Random Forest (n_estimators=100, max_depth=10, class_weight="balanced") |
| Dataset | 253,680 filas BRFSS 2015 |
| Accuracy | 72.44% |
| ROC AUC | 83.65% |
| F1 Score | 35.71% |
| Estado | **Operativo** — `POST /api/v1/evaluaciones/` retorna predicciones |

---

## 15. Tareas Pendientes

### 🔴 Alta Prioridad

| # | Tarea | Descripción | Impacto |
|---|-------|-------------|---------|
| 1 | **Frontend (React)** | No existe. Se menciona como "Fase 2". Sin frontend, el sistema no tiene interfaz de usuario. | Sin UI no hay usuarios |
| 2 | **Cambiar credenciales de producción** | `.env` tiene passwords por defecto (`admin123`, `doctor123`, `enfermera123`). | Seguridad crítica |
| 3 | **Cambiar JWT_SECRET_KEY** | Actualmente es `cambia-esta-clave-super-secreta-para-produccion` | Seguridad crítica |
| 4 | **Cambiar DEBUG=True a False** | En producción debe ser `False` | Seguridad |
| 5 | **Cambiar CORS_ORIGINS=*`** | Debe apuntar a la URL real del frontend en producción | Seguridad |

### 🟡 Media Prioridad

| # | Tarea | Descripción | Impacto |
|---|-------|-------------|---------|
| 6 | **Crear Dockerfile + docker-compose.yml** | No hay contenedores. Necesario para despliegue consistente. | Despliegue |
| 7 | **Configurar CI/CD** | No hay GitHub Actions ni pipeline de automatización. | Automatización |
| 8 | **Crear `app/clients/`** | Directorio vacío. Podría contener clientes para servicios externos. | Funcionalidad extra |
| 9 | **Evaluaciones seed con ML real** | Las 3 evaluaciones de prueba son datos hardcodeados, no predicciones reales. | Datos más creíbles |
| 10 | **Imágenes médicas (Fase 2)** | El análisis de imágenes médicas está planeado pero no implementado. | Feature futuro |

### 🟢 Baja Prioridad

| # | Tarea | Descripción | Impacto |
|---|-------|-------------|---------|
| 11 | **Documentación de API** | El Swagger UI (`/docs`) ya genera documentación automática, pero podría agregarse documentación adicional. | Baja |
| 12 | **Monitoreo y logging** | No hay sistema de logging estructurado ni monitoreo. | Operaciones |
| 13 | **Pipeline de datos** | Podría automatizarse la descarga y preparación del dataset para reentrenamiento. | Mantenimiento ML |

---

## Instrucciones de Instalación y Ejecución

### Requisitos
- Python 3.10+
- MySQL 8.0+

### 1. Configurar Base de Datos
```sql
CREATE DATABASE healthcure_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
```

### 2. Configurar Variables de Entorno
Editar `.env`:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu_password_aqui
DB_NAME=healthcure_db
JWT_SECRET_KEY=tu_clave_super_secreta
DEBUG=False
CORS_ORIGINS=http://localhost:3000
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Ejecutar el Servidor
```bash
uvicorn main:app --reload --port 8000
```

### 5. Verificar
- Swagger UI: **http://localhost:8000/docs**
- Health check: **http://localhost:8000/health**

### 6. Probar el ML
```bash
# El modelo ya está entrenado, solo reiniciar el servidor
# POST /api/v1/evaluaciones/ → retorna 201 con predicción
```

### 7. Correr Tests
```bash
python -m pytest app/tests -v
```

### 8. Credenciales de Prueba (seed automático)
| Rol | Email | Password |
|-----|-------|----------|
| Admin | `admin@healthcure.com` | `admin123` |
| Médico | `dr.garcia@healthcure.com` | `doctor123` |
| Enfermera | `ana.martinez@healthcure.com` | `enfermera123` |

### 9. Flujo de Uso Típico
```
1. POST /api/v1/auth/register   → Crear cuenta de usuario
2. POST /api/v1/auth/login      → Obtener token JWT
3. GET  /api/v1/catalogos/distritos  → Cargar opciones del formulario
4. POST /api/v1/pacientes/      → Registrar paciente
5. POST /api/v1/evaluaciones/   → Evaluar riesgo cardíaco (ML)
6. GET  /api/v1/evaluaciones/   → Ver historial
```

---

## Licencia

Proyecto académico — HealthCure CardioPredict
