# HealthCure — CardioPredict: Mapeo Completo del Backend

> Documento técnico de referencia: rutas, flujos, CRUD, datos de entrada/salida, y arquitectura ML.
> Generado a partir del código fuente actual del proyecto.

---

## Tabla de Contenidos

1. [Resumen del Proyecto](#1-resumen-del-proyecto)
2. [Arquitectura de Capas](#2-arquitectura-de-capas)
3. [Base de Datos (MySQL)](#3-base-de-datos-mysql)
4. [Autenticación (JWT)](#4-autenticación-jwt)
5. [Endpoints — Rutas Completas](#5-endpoints--rutas-completas)
6. [Flujo por Endpoint](#6-flujo-por-endpoint)
7. [Mapa de CRUD](#7-mapa-de-crud)
8. [Machine Learning (ML)](#8-machine-learning-ml)
9. [Seed de Datos de Prueba](#9-seed-de-datos-de-prueba)
10. [Matriz de Permisos](#10-matriz-de-permisos)

---

## 1. Resumen del Proyecto

| Campo | Valor |
|-------|-------|
| **Nombre** | HealthCure — CardioPredict |
| **Propósito** | Sistema web de triaje cardíaco con predicción ML |
| **Stack** | Python + FastAPI + MySQL + Random Forest/XGBoost |
| **Roles** | `admin` (gestiona usuarios) · `usuario` (médico/enfermera — registra pacientes y evalúa) |
| **Estado** | MVP funcional (sin modelo ML entrenado aún) |

---

## 2. Arquitectura de Capas

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                          │
│                    (fase 2 — por crear)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (JSON)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  6. API (Controllers)     app/api/v1/                        │
│     Recibe request → llama al service → retorna response     │
│     ❌ NO tiene lógica de negocio                           │
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
│  app/models/         │    │  app/resources/modelo_cardiaco.*  │
│  SQLAlchemy → MySQL  │    │  Random Forest/XGBoost entrenado  │
└─────────────────────┘    └──────────────────────────────────┘
```

**Regla de oro:** Cada capa solo sabe de la capa de abajo. Nunca se salta.

---

## 3. Base de Datos (MySQL)

### 3.1 Diagrama ER

```
┌──────────────────────┐        ┌──────────────────────────┐
│      usuarios         │        │        pacientes           │
├──────────────────────┤        ├──────────────────────────┤
│ id          BIGINT PK │        │ id              BIGINT PK │
│ nombre      VARCHAR   │        │ nombre          VARCHAR   │
│ email       VARCHAR U │        │ documento_ident VARCHAR U │
│ password_ha VARCHAR   │        │ fecha_nacimiento DATE     │
│ rol         ENUM      │        │ sexo            ENUM(M/F) │
│ activo      BOOLEAN   │        │ talla_cm        DECIMAL   │
│ created_at  DATETIME  │        │ peso_kg         DECIMAL   │
│ updated_at  DATETIME  │        │ created_at      DATETIME  │
└──────┬───────────────┘        │ updated_at      DATETIME  │
       │                        └──────────┬───────────────┘
       │                                   │
       │  1:N                               │  1:N
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
│ probabilidad        DECIMAL(7,6)  ← resultado del ML          │
│ clasificacion       ENUM(bajo/moderado/alto) ← resultado ML   │
│ modelo_version      VARCHAR(50)                                │
│ created_at          DATETIME                                   │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Tipos de Columna MySQL

| Tabla | Columna | Tipo MySQL | Equivalente Python | Notas |
|-------|---------|------------|-------------------|-------|
| usuarios | id | `BIGINT` | `BigInteger` | Auto-increment |
| usuarios | email | `VARCHAR(255)` | `String(255)` | UNIQUE + INDEX |
| usuarios | password_hash | `VARCHAR(255)` | `String(255)` | bcrypt hash |
| usuarios | rol | `ENUM('admin','usuario')` | `Enum(...)` | Default 'usuario' |
| pacientes | documento_identidad | `VARCHAR(30)` | `String(30)` | UNIQUE + INDEX |
| pacientes | fecha_nacimiento | `DATE` | `Date` | Formato ISO |
| pacientes | sexo | `ENUM('M','F')` | `Enum(...)` | M/F |
| pacientes | talla_cm | `DECIMAL(5,1)` | `Numeric(5,1)` | Nullable (opcional) |
| pacientes | peso_kg | `DECIMAL(5,1)` | `Numeric(5,1)` | Nullable (opcional) |
| evaluaciones | edad | `SMALLINT` | `SmallInteger` | 1-120 |
| evaluaciones | salud_general | `SMALLINT` | `SmallInteger` | 1-5 (escala CDC) |
| evaluaciones | probabilidad | `DECIMAL(7,6)` | `Numeric(7,6)` | 0.000000 - 1.000000 |
| evaluaciones | clasificacion | `ENUM('bajo','moderado','alto')` | `Enum(...)` | Calculado del ML |

### 3.3 Índices

| Tabla | Índice | Columna | Propósito |
|-------|--------|---------|-----------|
| usuarios | `ix_usuarios_email` | email | Login rápido por email |
| pacientes | `ix_pacientes_documento` | documento_identidad | Búsqueda por documento |
| evaluaciones | `ix_evaluaciones_paciente_id` | paciente_id | Historial por paciente |
| evaluaciones | `ix_evaluaciones_created_at` | created_at | ORDER BY para listados |

### 3.4 Foreign Keys

| Tabla | Columna | Referencia | ON DELETE |
|-------|---------|------------|-----------|
| evaluaciones | paciente_id | pacientes.id | RESTRICT (no borrar paciente con evaluaciones) |
| evaluaciones | usuario_id | usuarios.id | RESTRICT (no borrar usuario con evaluaciones) |

---

## 4. Autenticación (JWT)

### 4.1 Flujo de Login

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
   │                            │  jwt.encode({sub:id, rol})    │
   │                            │                               │
   │  ← {access_token, user}   │                               │
   │                            │                               │
```

### 4.2 Flujo de Request Autenticado

```
Frontend                     Backend (deps.py)                MySQL
   │                            │                               │
   │  GET /api/v1/pacientes/    │                               │
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
   │                            │  return {id, nombre, email}   │
   │                            │                               │
   │                            │  ...endpoint ejecuta lógica...│
   │                            │                               │
   │  ← Response JSON           │                               │
```

### 4.3 Variables de Configuración

| Variable | Valor por defecto | Descripción |
|----------|-------------------|-------------|
| `JWT_SECRET_KEY` | `CHANGE-THIS-IN-PRODUCTION-...` | Clave de firma HMAC-SHA256 |
| `JWT_ALGORITHM` | `HS256` | Algoritmo de firma |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token válido por 1 hora |

### 4.4 Cómo se Envía el Token

```
Header: Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 5. Endpoints — Rutas Completas

### 5.1 Tabla Resumen

| # | Método | Ruta | Auth | Rol | Descripción | Status Codes |
|---|--------|------|------|-----|-------------|--------------|
| 1 | `GET` | `/health` | ❌ | — | Health check del servidor | 200 |
| 2 | `POST` | `/api/v1/auth/register` | ❌ | — | Registrar usuario nuevo | 201, 409, 422 |
| 3 | `POST` | `/api/v1/auth/login` | ❌ | — | Login → JWT | 200, 401, 422 |
| 4 | `GET` | `/api/v1/auth/me` | ✅ | Cualquiera | Datos del usuario autenticado | 200, 401 |
| 5 | `GET` | `/api/v1/pacientes/` | ✅ | Cualquiera | Listar todos los pacientes | 200, 401 |
| 6 | `GET` | `/api/v1/pacientes/search` | ✅ | Cualquiera | Búsqueda parcial por documento | 200, 401 |
| 7 | `GET` | `/api/v1/pacientes/by-documento/{doc}` | ✅ | Cualquiera | Buscar por documento exacto | 200, 401, 404 |
| 8 | `GET` | `/api/v1/pacientes/{id}` | ✅ | Cualquiera | Obtener paciente por ID | 200, 401, 404 |
| 9 | `POST` | `/api/v1/pacientes/` | ✅ | Cualquiera | Registrar paciente nuevo | 201, 401, 409, 422 |
| 10 | `PUT` | `/api/v1/pacientes/{id}` | ✅ | Cualquiera | Actualizar paciente (parcial) | 200, 401, 404, 422 |
| 11 | `POST` | `/api/v1/evaluaciones/` | ✅ | Cualquiera | **Crear evaluación (ML)** | 201, 400, 401, 500 |
| 12 | `GET` | `/api/v1/evaluaciones/` | ✅ | Cualquiera | Listar evaluaciones (paginado) | 200, 401 |
| 13 | `GET` | `/api/v1/evaluaciones/by-paciente/{id}` | ✅ | Cualquiera | Historial de un paciente | 200, 401 |
| 14 | `GET` | `/api/v1/evaluaciones/{id}` | ✅ | Cualquiera | Ver una evaluación | 200, 401, 404 |
| 15 | `GET` | `/api/v1/admin/usuarios` | ✅ | **admin** | Listar todos los usuarios | 200, 401, 403 |
| 16 | `PUT` | `/api/v1/admin/usuarios/{id}/deactivate` | ✅ | **admin** | Desactivar usuario (soft delete) | 200, 401, 403, 404 |

### 5.2 Orden de Rutas (IMPORTANTE)

FastAPI procesa rutas en orden. Las rutas estáticas DEBEN ir antes de las dinámicas:

```
✅ CORRECTO:
  GET /search        ← estática, se evalúa primero
  GET /by-documento  ← estática, se evalúa primero
  GET /{id}          ← dinámica, se evalúa después

❌ INCORRECTO:
  GET /{id}          ← FastAPI interpreta "search" como un ID
  GET /search        ← NUNCA se alcanza
```

---

## 6. Flujo por Endpoint

### 6.1 `POST /api/v1/auth/register` — Registrar Usuario

```
DATOS DE ENTRADA (Body JSON):
{
    "nombre": "Dr. García",          // str, 2-150 chars, obligatorio
    "email": "garcia@hospital.com",  // EmailStr, único, obligatorio
    "password": "mi_password",       // str, 6-128 chars, obligatorio
    "rol": "usuario"                 // Enum("admin","usuario"), default "usuario"
}

FLUJO INTERNO:
  Controller → AuthService.register()
    → Valida que el email NO exista (UsuarioRepository.get_by_email)
    → Hashea la contraseña con bcrypt
    → Crea el usuario con rol="usuario" (IGNORA el rol del request por seguridad)
    → UsuarioRepository.create()

DATOS QUE SE GUARDAN EN MySQL (tabla usuarios):
  id              → AUTO_INCREMENT
  nombre          → "Dr. García"
  email           → "garcia@hospital.com"
  password_hash   → "$2b$12$LJ3m4ys3G..." (bcrypt, NUNCA el texto plano)
  rol             → "usuario" (siempre, sin importar lo que envíe el request)
  activo          → TRUE
  created_at      → CURRENT_TIMESTAMP
  updated_at      → CURRENT_TIMESTAMP

RESPUESTA (201):
{
    "id": 1,
    "nombre": "Dr. García",
    "email": "garcia@hospital.com",
    "rol": "usuario",
    "activo": true,
    "created_at": "2025-01-15T10:30:00"
}

ERRORES:
  409 → "Ya existe un usuario con ese email"
  422 → Validación de Pydantic (email inválido, password muy corta, etc.)
```

---

### 6.2 `POST /api/v1/auth/login` — Iniciar Sesión

```
DATOS DE ENTRADA (Body JSON):
{
    "email": "garcia@hospital.com",  // EmailStr, obligatorio
    "password": "mi_password"        // str, obligatorio
}

FLUJO INTERNO:
  Controller → AuthService.login()
    → UsuarioRepository.get_by_email(email)
    → Verifica que el usuario exista y esté activo
    → bcrypt.verify(password, password_hash) → True/False
    → Crea token JWT con {sub: id, rol: rol, exp: +60min}

DATOS QUE SE GUARDAN EN MySQL:
  Ninguno — es solo lectura + creación de token

RESPUESTA (200):
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "usuario": {
        "id": 1,
        "nombre": "Dr. García",
        "email": "garcia@hospital.com",
        "rol": "usuario",
        "activo": true,
        "created_at": "2025-01-15T10:30:00"
    }
}

ERRORES:
  401 → "Credenciales inválidas" (email no existe, password incorrecto, o usuario inactivo)
```

---

### 6.3 `GET /api/v1/auth/me` — Mi Perfil

```
DATOS DE ENTRADA:
  Header: Authorization: Bearer <token>

FLUJO INTERNO:
  Controller → Depends(get_current_user) → deps.py
    → jwt.decode(token) → payload = {sub: 1, rol: "usuario"}
    → AuthService.get_user_by_id(1) → Usuario ORM
    → Verifica que esté activo
    → Retorna {id, nombre, email, rol}

DATOS QUE SE LEEN DE MySQL:
  SELECT * FROM usuarios WHERE id = 1

RESPUESTA (200):
{
    "id": 1,
    "nombre": "Dr. García",
    "email": "garcia@hospital.com",
    "rol": "usuario",
    "activo": true,
    "created_at": "2025-01-15T10:30:00"
}

ERRORES:
  401 → Token inválido/expirado o usuario inactivo
```

---

### 6.4 `GET /api/v1/pacientes/` — Listar Pacientes

```
DATOS DE ENTRADA:
  Header: Authorization: Bearer <token>
  Query: (ninguno)

FLUJO INTERNO:
  Controller → PacienteService.list_all()
    → PacienteRepository.list_all()
    → SELECT * FROM pacientes ORDER BY id
    → model_validate() para cada registro

DATOS QUE SE LEEN DE MySQL:
  SELECT id, nombre, documento_identidad, fecha_nacimiento, sexo,
         talla_cm, peso_kg, created_at, updated_at
  FROM pacientes ORDER BY id

RESPUESTA (200):
[
    {
        "id": 1,
        "nombre": "Juan Pérez Rodríguez",
        "documento_identidad": "1032456789",
        "fecha_nacimiento": "1965-05-20",
        "sexo": "M",
        "talla_cm": 172.5,
        "peso_kg": 85.3,
        "created_at": "2025-01-15T10:30:00",
        "updated_at": "2025-01-15T10:30:00"
    },
    ...
]
```

---

### 6.5 `GET /api/v1/pacientes/search` — Búsqueda Parcial

```
DATOS DE ENTRADA:
  Header: Authorization: Bearer <token>
  Query param: documento=1234  (str, obligatorio)

FLUJO INTERNO:
  Controller → PacienteService.search("1234")
    → PacienteRepository.search_by_documento("1234")
    → SELECT * FROM pacientes WHERE documento_identidad LIKE '%1234%' LIMIT 10

RESPUESTA (200):
[
    {"id": 1, "nombre": "Juan Pérez", "documento_identidad": "1032456789", ...}
]

NOTA: Para autocomplete en el frontend — mientras el usuario escribe,
se envía la query y se muestran las sugerencias.
```

---

### 6.6 `GET /api/v1/pacientes/by-documento/{documento}` — Documento Exacto

```
DATOS DE ENTRADA:
  Header: Authorization: Bearer <token>
  Path param: documento=1032456789 (str)

FLUJO INTERNO:
  Controller → PacienteService.get_by_documento("1032456789")
    → PacienteRepository.get_by_documento("1032456789")
    → SELECT * FROM pacientes WHERE documento_identidad = '1032456789'

RESPUESTA (200):
{
    "id": 1,
    "nombre": "Juan Pérez Rodríguez",
    "documento_identidad": "1032456789",
    "fecha_nacimiento": "1965-05-20",
    "sexo": "M",
    "talla_cm": 172.5,
    "peso_kg": 85.3,
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:30:00"
}

ERRORES:
  404 → "Paciente no encontrado"
```

---

### 6.7 `POST /api/v1/pacientes/` — Crear Paciente

```
DATOS DE ENTRADA (Body JSON):
{
    "nombre": "María López",            // str, 2-150 chars, obligatorio
    "documento_identidad": "1234567890", // str, 5-30 chars, único, obligatorio
    "fecha_nacimiento": "1985-03-15",    // date (YYYY-MM-DD), obligatorio
    "sexo": "F",                         // Enum("M","F"), obligatorio
    "talla_cm": 165.5,                   // float, >0, ≤300, opcional
    "peso_kg": 70.2                      // float, >0, ≤500, opcional
}

FLUJO INTERNO:
  Controller → PacienteService.create()
    → Valida que NO exista otro paciente con ese documento
    → PacienteRepository.create(nombre, documento, fecha, sexo, talla, peso)
    → INSERT INTO pacientes (...)

DATOS QUE SE GUARDAN EN MySQL (tabla pacientes):
  id                  → AUTO_INCREMENT
  nombre              → "María López"
  documento_identidad → "1234567890"
  fecha_nacimiento    → 1985-03-15
  sexo                → "F"
  talla_cm            → 165.5
  peso_kg             → 70.2
  created_at          → CURRENT_TIMESTAMP
  updated_at          → CURRENT_TIMESTAMP

RESPUESTA (201):
{
    "id": 6,
    "nombre": "María López",
    "documento_identidad": "1234567890",
    "fecha_nacimiento": "1985-03-15",
    "sexo": "F",
    "talla_cm": 165.5,
    "peso_kg": 70.2,
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:30:00"
}

ERRORES:
  409 → "Ya existe un paciente con ese documento"
  422 → Validación de Pydantic
```

---

### 6.8 `PUT /api/v1/pacientes/{id}` — Actualizar Paciente (Parcial)

```
DATOS DE ENTRADA (Body JSON — solo campos a actualizar):
{
    "talla_cm": 166.0,    // solo se actualiza este campo
    "peso_kg": 71.5       // y este
}
// nombre, fecha_nacimiento, sexo NO se tocan (son null/omitidos)

FLUJO INTERNO:
  Controller → PacienteService.update()
    → PacienteRepository.get_by_id(1) → verificar que exista
    → data.model_dump(exclude_unset=True) → {"talla_cm": 166.0, "peso_kg": 71.5}
    → PacienteRepository.update(paciente, talla_cm=166.0, peso_kg=71.5)
    → UPDATE pacientes SET talla_cm=166.0, peso_kg=71.5, updated_at=NOW() WHERE id=1

DATOS QUE SE ACTUALIZAN EN MySQL:
  Solo los campos enviados + updated_at se actualizan automáticamente

RESPUESTA (200):
{
    "id": 1,
    "nombre": "Juan Pérez Rodríguez",  // NO cambió
    "documento_identidad": "1032456789", // NO cambió
    "fecha_nacimiento": "1965-05-20",  // NO cambió
    "sexo": "M",                        // NO cambió
    "talla_cm": 166.0,                 // ✅ SÍ cambió
    "peso_kg": 71.5,                   // ✅ SÍ cambió
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T11:45:00" // ✅ SÍ cambió
}

ERRORES:
  404 → "Paciente no encontrado"
```

---

### 6.9 ⭐ `POST /api/v1/evaluaciones/` — Crear Evaluación (ML)

Este es el endpoint MÁS IMPORTANTE del sistema.

```
DATOS DE ENTRADA (Body JSON):
{
    "paciente_id": 1,                    // int, obligatorio (debe existir)
    "edad": 55,                          // int, 1-120, obligatorio
    "presion_alta": true,                // bool, default false
    "colesterol_alto": true,             // bool, default false
    "tabaquismo": false,                 // bool, default false
    "actividad_fisica": true,            // bool, default false
    "antecedente_acv": false,            // bool, default false
    "diabetes": true,                    // bool, default false
    "salud_general": 3,                  // int, 1-5 (CDC), default 3
    "dificultad_para_caminar": false     // bool, default false
}

FLUJO COMPLETO (6 pasos):

  ┌─────────────────────────────────────────────────────────────┐
  │ PASO 1: Validar paciente                                    │
  │   PacienteRepository.get_by_id(1) → verificar que exista   │
  └──────────────────────────┬──────────────────────────────────┘
                             ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ PASO 2: Mapper → ML Input Vector                            │
  │   EvaluacionMapper.request_to_model_input(data)             │
  │   Transforma booleans → int (0/1) para el modelo            │
  │   Elimina paciente_id (el modelo no sabe de pacientes)      │
  └──────────────────────────┬──────────────────────────────────┘
                             ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ PASO 3: Predictor → Probabilidad                            │
  │   app.ml.predictor.predict(model_input)                     │
  │   → Preprocessor: limpia + ordena columnas                  │
  │   → model.predict_proba(df) → [[0.26, 0.74]]               │
  │   → Clasifica: 0.74 > 0.60 → "alto"                        │
  └──────────────────────────┬──────────────────────────────────┘
                             ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ PASO 4: Mapper → ORM Dict                                  │
  │   EvaluacionMapper.create_to_model(data, prediction, user)  │
  │   Combina: datos request + resultado ML + usuario_id        │
  └──────────────────────────┬──────────────────────────────────┘
                             ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ PASO 5: Repository → Persistir en MySQL                     │
  │   EvaluacionRepository.create(**dict)                       │
  │   INSERT INTO evaluaciones (...)                             │
  └──────────────────────────┬──────────────────────────────────┘
                             ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ PASO 6: Mapper → Response DTO                               │
  │   EvaluacionMapper.to_response(evaluacion_orm)              │
  │   Convierte Numeric→float, Enum→ClasificacionEnum          │
  └──────────────────────────┬──────────────────────────────────┘
                             ▼
                        Response 201

DATOS QUE SE GUARDAN EN MySQL (tabla evaluaciones):
  id                      → AUTO_INCREMENT
  paciente_id             → 1
  usuario_id              → (del JWT)
  edad                    → 55
  presion_alta            → TRUE
  colesterol_alto         → TRUE
  tabaquismo              → FALSE
  actividad_fisica        → TRUE
  antecedente_acv         → FALSE
  diabetes                → TRUE
  salud_general           → 3
  dificultad_para_caminar → FALSE
  probabilidad            → 0.734521  ← calculado por el ML
  clasificacion           → "alto"     ← calculado por el ML
  modelo_version          → "1.0.0"
  created_at              → CURRENT_TIMESTAMP

RESPUESTA (201):
{
    "id": 1,
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
    "probabilidad": 0.734521,
    "clasificacion": "alto",
    "modelo_version": "1.0.0",
    "created_at": "2025-01-15T10:30:00"
}

ERRORES:
  400 → "Paciente no encontrado"
  500 → "Error ML: Modelo ML no disponible: [detalle]"
```

---

### 6.10 `GET /api/v1/evaluaciones/` — Listar Evaluaciones (Paginado)

```
DATOS DE ENTRADA:
  Header: Authorization: Bearer <token>
  Query params:
    limit  → int, default 50 (máximo de resultados)
    offset → int, default 0  (cuántos saltar)

FLUJO INTERNO:
  Controller → EvaluacionService.list_all(limit, offset)
    → EvaluacionRepository.list_all(limit, offset)
    → SELECT * FROM evaluaciones ORDER BY created_at DESC LIMIT 50 OFFSET 0

EJEMPLO:
  GET /api/v1/evaluaciones/?limit=10&offset=0   → evaluaciones 1-10
  GET /api/v1/evaluaciones/?limit=10&offset=10  → evaluaciones 11-20
  GET /api/v1/evaluaciones/?limit=10&offset=20  → evaluaciones 21-30

RESPUESTA (200): Array de EvaluacionResponse (igual que el POST)
```

---

### 6.11 `GET /api/v1/evaluaciones/by-paciente/{id}` — Historial

```
DATOS DE ENTRADA:
  Header: Authorization: Bearer <token>
  Path param: paciente_id=1 (int)

FLUJO INTERNO:
  Controller → EvaluacionService.get_by_paciente(1)
    → EvaluacionRepository.get_by_paciente(1)
    → SELECT * FROM evaluaciones WHERE paciente_id=1 ORDER BY created_at DESC

RESPUESTA (200):
[
    {
        "id": 3,
        "paciente_id": 1,
        "edad": 55,
        "probabilidad": 0.784521,
        "clasificacion": "alto",
        "created_at": "2025-01-20T14:00:00"   // más reciente primero
    },
    {
        "id": 1,
        "paciente_id": 1,
        "edad": 53,
        "probabilidad": 0.650000,
        "clasificacion": "alto",
        "created_at": "2025-01-15T10:30:00"   // más antigua
    }
]

NOTA: Permite ver cómo ha cambiado el riesgo cardíaco del paciente
a lo largo del tiempo.
```

---

### 6.12 `GET /api/v1/evaluaciones/{id}` — Ver Evaluación

```
DATOS DE ENTRADA:
  Header: Authorization: Bearer <token>
  Path param: evaluacion_id=1 (int)

RESPUESTA (200): EvaluacionResponse completa (igual que el POST)

ERRORES:
  404 → "Evaluación no encontrada"
```

---

### 6.13 `GET /api/v1/admin/usuarios` — Listar Usuarios (Admin)

```
DATOS DE ENTRADA:
  Header: Authorization: Bearer <token> (debe ser rol "admin")

FLUJO INTERNO:
  Controller → Depends(require_admin) → verifica rol
    → AdminService.list_usuarios()
    → UsuarioRepository.list_all()
    → SELECT * FROM usuarios ORDER BY id

RESPUESTA (200):
[
    {
        "id": 1,
        "nombre": "Administrador",
        "email": "admin@healthcure.com",
        "rol": "admin",
        "activo": true,
        "created_at": "2025-01-15T10:30:00"
    },
    ...
]
// NOTA: NUNCA retorna password_hash

ERRORES:
  403 → "Se requiere rol de administrador"
  401 → Token inválido
```

---

### 6.14 `PUT /api/v1/admin/usuarios/{id}/deactivate` — Desactivar Usuario

```
DATOS DE ENTRADA:
  Header: Authorization: Bearer <token> (debe ser rol "admin")
  Path param: usuario_id=3 (int)

FLUJO INTERNO:
  Controller → Depends(require_admin)
    → AdminService.deactivate_usuario(3)
    → UPDATE usuarios SET activo=FALSE WHERE id=3

DATOS QUE SE ACTUALIZAN EN MySQL:
  activo → FALSE (soft delete, NO borra el registro)
  updated_at → CURRENT_TIMESTAMP

RESPUESTA (200):
{
    "message": "Usuario desactivado correctamente"
}

EFECTOS DEL SOFT DELETE:
  ✗ El usuario NO puede hacer login (AuthService valida activo=True)
  ✓ El usuario SIGUE existiendo en la BD (para auditoría)
  ✓ Sus evaluaciones siguen intactas (FK no se rompen)

ERRORES:
  404 → "Usuario no encontrado"
  403 → "Se requiere rol de administrador"
```

---

## 7. Mapa de CRUD

| Entidad | Create | Read (uno) | Read (listar) | Read (buscar) | Update | Delete |
|---------|--------|------------|---------------|---------------|--------|--------|
| **Usuarios** | `POST /auth/register` | `GET /auth/me` | `GET /admin/usuarios` *(admin)* | — | — | `PUT /admin/{id}/deactivate` *(admin, soft)* |
| **Pacientes** | `POST /pacientes/` | `GET /pacientes/{id}` · `GET /by-documento/{doc}` | `GET /pacientes/` | `GET /search?documento=` | `PUT /pacientes/{id}` | — |
| **Evaluaciones** | `POST /evaluaciones/` | `GET /evaluaciones/{id}` | `GET /evaluaciones/` *(paginado)* | `GET /by-paciente/{id}` | — | — |

**Notas:**
- No hay DELETE duro en ninguna entidad (soft delete en usuarios, no existe en pacientes/evaluaciones)
- No hay UPDATE de evaluaciones (son inmutables — cada una es una instantánea)
- No hay CREATE de usuarios por admin (solo por registro público)

---

## 8. Machine Learning (ML)

### 8.1 Pipeline del ML

```
┌─────────────────────────────────────────────────────────────┐
│                      CAPA ML                                  │
│                                                               │
│  ┌───────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ preprocessor   │───→│ model_loader │───→│ predictor    │  │
│  │                │    │  (singleton) │    │              │  │
│  │ • Valida       │    │ • Carga      │    │ • predict()  │  │
│  │ • Ordena cols  │    │   .joblib    │    │ • Clasifica  │  │
│  │ • bool → int   │    │ • Cachea     │    │              │  │
│  └───────────────┘    └──────────────┘    └──────────────┘  │
│                                                               │
│  Input:  dict {"edad": 55, "presion_alta": 1, ...}          │
│  Output: PredictionResult(probabilidad=0.73, "alto")         │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Variables Predictoras (CDC/BRFSS Dataset)

| # | Variable | Tipo | Rango | Descripción |
|---|----------|------|-------|-------------|
| 1 | `edad` | int | 1-120 | Edad del paciente |
| 2 | `presion_alta` | bool→int | 0/1 | Diagnóstico de presión alta |
| 3 | `colesterol_alto` | bool→int | 0/1 | Colesterol alto diagnosticado |
| 4 | `tabaquismo` | bool→int | 0/1 | Fuma o fumó ≥100 cigarrillos |
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

### 8.3 Clasificación de Riesgo

```
Probabilidad de enfermedad cardíaca:

0%                    30%                   60%                  100%
├─────────────────────┼─────────────────────┼────────────────────┤
│     BAJO RIESGO     │   RIESGO MODERADO   │    ALTO RIESGO     │
│     "bajo"          │     "moderado"      │      "alto"        │
│   < 0.30            │   0.30 - 0.60       │     > 0.60         │
└─────────────────────┴─────────────────────┴────────────────────┘
```

### 8.4 Modelo Actual

| Campo | Valor |
|-------|-------|
| **Algoritmo** | Pendiente de entrenar (Random Forest / XGBoost) |
| **Dataset** | Heart Disease Health Indicators (CDC/BRFSS, Kaggle) |
| **Archivo** | `app/resources/modelo_cardiaco.joblib` (no existe aún) |
| **Versión** | `1.0.0` |
| **Estado** | ⚠️ El server funciona sin el modelo — solo falla al predecir |

### 8.5 Comportamiento sin Modelo

Si el archivo `.joblib` no existe:
- ✅ Login, registro, pacientes → funcionan normal
- ❌ `POST /evaluaciones/` → retorna **500** con "Modelo ML no disponible"
- ✅ Seed de datos de prueba → crea usuarios, pacientes y evaluaciones de ejemplo (con datos hardcodeados, no del ML)

---

## 9. Seed de Datos de Prueba

Ejecuta automáticamente al iniciar el servidor (`main.py` lifespan). Solo crea datos si la BD está vacía.

### 9.1 Usuarios Creados

| Nombre | Email | Password | Rol |
|--------|-------|----------|-----|
| Administrador | `admin@healthcure.com` | `admin123` | **admin** |
| Dr. Carlos García | `dr.garcia@healthcure.com` | `doctor123` | usuario |
| Enfermera Ana Martínez | `ana.martinez@healthcure.com` | `enfermera123` | usuario |

### 9.2 Pacientes Creados

| Nombre | Documento | Sexo | Edad aprox | Talla | Peso |
|--------|-----------|------|------------|-------|------|
| Juan Pérez Rodríguez | 1032456789 | M | 61 | 172.5 | 85.3 |
| María Fernanda López | 1098765432 | F | 48 | 160.0 | 68.7 |
| Roberto Carlos Gómez | 1122334455 | M | 71 | 168.0 | 92.1 |
| Laura Daniela Martínez | 1055667788 | F | 36 | 165.0 | 58.4 |
| Pedro Antonio Sánchez | 1066778899 | M | 78 | 170.0 | 78.5 |

### 9.3 Evaluaciones Creadas (ejemplos hardcodeados)

| Paciente | Edad | Riesgo | Probabilidad | Clasificación | Factores clave |
|----------|------|--------|-------------|---------------|----------------|
| Juan Pérez | 61 | Alto | 78.5% | **alto** | presión + colesterol + tabaquismo + diabetes |
| María López | 48 | Moderado | 35.2% | **moderado** | solo presión alta, activa |
| Roberto Gómez | 71 | Alto | 92.1% | **alto** | presión + colesterol + ACV + diabetes + inmovilidad |

---

## 10. Matriz de Permisos

| Endpoint | Sin token | Token usuario | Token admin |
|----------|-----------|---------------|-------------|
| `GET /health` | ✅ 200 | ✅ 200 | ✅ 200 |
| `POST /auth/register` | ✅ 201 | ✅ 201 | ✅ 201 |
| `POST /auth/login` | ✅ 200 | ✅ 200 | ✅ 200 |
| `GET /auth/me` | ❌ 401 | ✅ 200 | ✅ 200 |
| `GET /pacientes/` | ❌ 401 | ✅ 200 | ✅ 200 |
| `GET /pacientes/search` | ❌ 401 | ✅ 200 | ✅ 200 |
| `GET /pacientes/by-documento/{doc}` | ❌ 401 | ✅ 200 | ✅ 200 |
| `GET /pacientes/{id}` | ❌ 401 | ✅ 200 | ✅ 200 |
| `POST /pacientes/` | ❌ 401 | ✅ 201 | ✅ 201 |
| `PUT /pacientes/{id}` | ❌ 401 | ✅ 200 | ✅ 200 |
| `POST /evaluaciones/` | ❌ 401 | ✅ 201 | ✅ 201 |
| `GET /evaluaciones/` | ❌ 401 | ✅ 200 | ✅ 200 |
| `GET /evaluaciones/by-paciente/{id}` | ❌ 401 | ✅ 200 | ✅ 200 |
| `GET /evaluaciones/{id}` | ❌ 401 | ✅ 200 | ✅ 200 |
| `GET /admin/usuarios` | ❌ 401 | ❌ 403 | ✅ 200 |
| `PUT /admin/usuarios/{id}/deactivate` | ❌ 401 | ❌ 403 | ✅ 200 |

---

## Apéndice: Estructura de Archivos

```
app/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── config.py              # Settings desde .env (Pydantic)
│   └── database.py            # Engine + SessionLocal + get_db
├── models/
│   ├── __init__.py            # Importa todos los modelos (para Alembic)
│   ├── usuario.py             # Tabla usuarios (auth)
│   ├── paciente.py            # Tabla pacientes (datos admin)
│   └── evaluacion.py          # Tabla evaluaciones (predicciones ML)
├── schemas/
│   ├── __init__.py
│   ├── usuario.py             # UsuarioCreate, Login, Response, Token
│   ├── paciente.py            # PacienteCreate, Update, Response
│   └── evaluacion.py          # EvaluacionCreate, Response, PredictionResult
├── mappers/
│   ├── __init__.py
│   └── evaluacion_mapper.py   # Request→ML→ORM→Response
├── repositories/
│   ├── __init__.py
│   ├── usuario_repository.py  # CRUD usuarios
│   ├── paciente_repository.py # CRUD pacientes
│   └── evaluacion_repository.py # CRUD evaluaciones
├── ml/
│   ├── __init__.py
│   ├── model_loader.py        # Singleton: carga .joblib una vez
│   ├── predictor.py           # predict() → probabilidad + clasificación
│   └── preprocessor.py        # Limpieza/validación/orden de columnas
├── services/
│   ├── __init__.py
│   ├── auth_service.py        # JWT + bcrypt + registro/login
│   ├── paciente_service.py    # CRUD pacientes
│   ├── evaluacion_service.py  # Orquesta ML + BD
│   └── admin_service.py       # Gestionar usuarios (solo admin)
├── api/
│   ├── __init__.py
│   ├── deps.py                # get_current_user + require_admin
│   └── v1/
│       ├── __init__.py
│       ├── auth.py            # /auth/*
│       ├── pacientes.py       # /pacientes/*
│       ├── evaluaciones.py    # /evaluaciones/*
│       └── admin.py           # /admin/*
├── exceptions/
│   ├── __init__.py
│   └── ml_exceptions.py       # ModelNotFoundError, PredictionError, etc.
├── seeds/
│   ├── __init__.py
│   └── seed.py                # Datos de prueba (admin, pacientes, evals)
├── tests/
│   └── __init__.py
├── clients/
│   └── __init__.py
└── resources/
    ├── __init__.py
    ├── schema.sql             # DDL MySQL completo
    ├── modelo_cardiaco.joblib # (pendiente — modelo entrenado)
    └── plantilla_pacientes.csv # (pendiente — plantilla de carga)

main.py                         # FastAPI entry point + lifespan (seed)
requirements.txt                # Dependencias Python
.env                            # Variables de entorno (MySQL, JWT)
.env.example                    # Template de .env
README.md                       # Documentación del proyecto
postman/
└── HealthCure_API.postman_collection.json  # Colección Postman completa
```
