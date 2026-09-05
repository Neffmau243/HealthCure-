# HealthCure — CardioPredict: Mapeo Completo del Backend

> Documento tecnico de referencia: rutas, flujos, CRUD, datos de entrada/salida, y arquitectura ML.
> Generado a partir del codigo fuente actual del proyecto.

---

## Tabla de Contenidos

1. [Resumen del Proyecto](#1-resumen-del-proyecto)
2. [Arquitectura de Capas](#2-arquitectura-de-capas)
3. [Base de Datos (MySQL)](#3-base-de-datos-mysql)
4. [Autenticacion (JWT)](#4-autenticacion-jwt)
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
| **Proposito** | Sistema web de triaje cardiaco con prediccion ML |
| **Stack** | Python + FastAPI + MySQL + Random Forest/XGBoost |
| **Roles** | `admin` (gestiona usuarios) · `usuario` (medico/enfermera — registra pacientes y evalua) |
| **Estado** | MVP funcional (sin modelo ML entrenado aun) |

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
│     NO tiene logica de negocio                              │
└──────────────────────────┬──────────────────────────────────┘
                           │ Depends(get_db) + Depends(get_current_user)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Service              app/services/                       │
│     Logica de negocio + orquestacion                         │
│     El UNICO que puede hablar con Repository + ML            │
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
┌──────────────────────┐        ┌──────────────────────────────┐
│      usuarios         │        │        pacientes               │
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
       │  1:N                    └──────────┬──────────────────┘
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
| pacientes | usuario_creador_id | `BIGINT` | `BigInteger` | FK implicito a usuarios.id |
| pacientes | talla_cm | `DECIMAL(5,1)` | `Numeric(5,1)` | Nullable (opcional) |
| pacientes | peso_kg | `DECIMAL(5,1)` | `Numeric(5,1)` | Nullable (opcional) |
| evaluaciones | edad | `SMALLINT` | `SmallInteger` | 1-120 |
| evaluaciones | salud_general | `SMALLINT` | `SmallInteger` | 1-5 (escala CDC) |
| evaluaciones | probabilidad | `DECIMAL(7,6)` | `Numeric(7,6)` | 0.000000 - 1.000000 |
| evaluaciones | clasificacion | `ENUM('bajo','moderado','alto')` | `Enum(...)` | Calculado del ML |

### 3.3 Indices

| Tabla | Indice | Columna | Proposito |
|-------|--------|---------|-----------|
| usuarios | `ix_usuarios_email` | email | Login rapido por email |
| pacientes | `ix_pacientes_documento` | documento_identidad | Busqueda por documento |
| pacientes | `ix_pacientes_usuario_creador` | usuario_creador_id | Busqueda por quien creo |
| evaluaciones | `ix_evaluaciones_paciente_id` | paciente_id | Historial por paciente |
| evaluaciones | `ix_evaluaciones_created_at` | created_at | ORDER BY para listados |

### 3.4 Foreign Keys

| Tabla | Columna | Referencia | ON DELETE |
|-------|---------|------------|-----------|
| evaluaciones | paciente_id | pacientes.id | RESTRICT (no borrar paciente con evaluaciones) |
| evaluaciones | usuario_id | usuarios.id | RESTRICT (no borrar usuario con evaluaciones) |
| pacientes | usuario_creador_id | usuarios.id | NO ACTION (nullable, compatibilidad) |

---

## 4. Autenticacion (JWT)

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
   │                            │  ...endpoint ejecuta logica...│
   │                            │                               │
   │  ← Response JSON           │                               │
```

### 4.3 Variables de Configuracion

| Variable | Valor por defecto | Descripcion |
|----------|-------------------|-------------|
| `JWT_SECRET_KEY` | `CHANGE-THIS-IN-PRODUCTION-...` | Clave de firma HMAC-SHA256 |
| `JWT_ALGORITHM` | `HS256` | Algoritmo de firma |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token valido por 1 hora |

### 4.4 Como se Envia el Token

```
Header: Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 5. Endpoints — Rutas Completas

### 5.1 Tabla Resumen

| # | Metodo | Ruta | Auth | Rol | Descripcion | Status Codes |
|---|--------|------|------|-----|-------------|--------------|
| 1 | `GET` | `/health` | No | — | Health check del servidor | 200 |
| 2 | `POST` | `/api/v1/auth/register` | No | — | Registrar usuario nuevo (SIEMPRE rol `usuario`, sin campo rol) | 201, 409, 422 |
| 3 | `POST` | `/api/v1/auth/login` | No | — | Login → JWT | 200, 401, 422 |
| 4 | `GET` | `/api/v1/auth/me` | Si | Cualquiera | Datos del usuario autenticado | 200, 401 |
| 5 | `GET` | `/api/v1/pacientes/` | Si | Cualquiera | Listar todos los pacientes | 200, 401 |
| 6 | `GET` | `/api/v1/pacientes/search` | Si | Cualquiera | Busqueda parcial por documento | 200, 401 |
| 7 | `GET` | `/api/v1/pacientes/by-documento/{doc}` | Si | Cualquiera | Buscar por documento exacto | 200, 401, 404 |
| 8 | `GET` | `/api/v1/pacientes/{id}` | Si | Cualquiera | Obtener paciente por ID | 200, 401, 404 |
| 9 | `POST` | `/api/v1/pacientes/` | Si | Cualquiera | Registrar paciente nuevo | 201, 401, 409, 422 |
| 10 | `PUT` | `/api/v1/pacientes/{id}` | Si | Creador o admin | Actualizar paciente (parcial) | 200, 401, 403, 404, 422 |
| 11 | `POST` | `/api/v1/evaluaciones/` | Si | Cualquiera | **Crear evaluacion (ML)** | 201, 400, 401, 500 |
| 12 | `GET` | `/api/v1/evaluaciones/` | Si | Cualquiera | Listar evaluaciones (paginado) | 200, 401 |
| 13 | `GET` | `/api/v1/evaluaciones/by-paciente/{id}` | Si | Cualquiera | Historial de un paciente | 200, 401 |
| 14 | `GET` | `/api/v1/evaluaciones/{id}` | Si | Cualquiera | Ver una evaluacion | 200, 401, 404 |
| 15 | `GET` | `/api/v1/admin/usuarios` | Si | **admin** | Listar todos los usuarios | 200, 401, 403 |
| 16 | `GET` | `/api/v1/admin/usuarios/{id}` | Si | **admin** | Obtener usuario por ID | 200, 401, 403, 404 |
| 17 | `POST` | `/api/v1/admin/usuarios` | Si | **admin** | Crear usuario (admin elige rol) | 201, 401, 403, 409, 422 |
| 18 | `PUT` | `/api/v1/admin/usuarios/{id}` | Si | **admin** | Actualizar usuario (parcial, con guards anti-lockout) | 200, 401, 403, 404, 409, 422 |
| 19 | `PUT` | `/api/v1/admin/usuarios/{id}/activate` | Si | **admin** | Reactivar usuario | 200, 401, 403, 404 |
| 20 | `PUT` | `/api/v1/admin/usuarios/{id}/deactivate` | Si | **admin** | Desactivar usuario (soft delete) | 200, 401, 403, 404, 409 |
| 21 | `GET` | `/api/v1/catalogos/distritos` | Si | Cualquiera | Distritos ACTIVOS (dropdown del doctor) | 200, 401 |
| 22 | `GET` | `/api/v1/catalogos/localidades` | Si | Cualquiera | Localidades ACTIVAS (dropdown, filtro ?distrito_id=) | 200, 401 |
| 23 | `GET` | `/api/v1/admin/distritos` | Si | **admin** | Listar distritos (todos) | 200, 401, 403 |
| 24 | `POST` | `/api/v1/admin/distritos` | Si | **admin** | Crear distrito (catálogo) | 201, 401, 403, 409 |
| 25 | `PUT` | `/api/v1/admin/distritos/{id}` | Si | **admin** | Actualizar distrito (nombre/activo) | 200, 401, 403, 404, 409 |
| 26 | `PUT` | `/api/v1/admin/distritos/{id}/deactivate` | Si | **admin** | Desactivar distrito (soft delete) | 200, 401, 403, 404 |
| 27 | `GET` | `/api/v1/admin/localidades` | Si | **admin** | Listar localidades (filtro ?distrito_id=) | 200, 401, 403 |
| 28 | `POST` | `/api/v1/admin/localidades` | Si | **admin** | Crear localidad (catálogo) | 201, 401, 403, 409 |
| 29 | `PUT` | `/api/v1/admin/localidades/{id}` | Si | **admin** | Actualizar localidad | 200, 401, 403, 404, 409 |
| 30 | `PUT` | `/api/v1/admin/localidades/{id}/deactivate` | Si | **admin** | Desactivar localidad (soft delete) | 200, 401, 403, 404 |

### 5.2 Orden de Rutas (IMPORTANTE)

FastAPI procesa rutas en orden. Las rutas estaticas DEBEN ir antes de las dinamicas:

```
CORRECTO:
  GET /search        ← estatica, se evalua primero
  GET /by-documento  ← estatica, se evalua primero
  GET /{id}          ← dinamica, se evalua despues

INCORRECTO:
  GET /{id}          ← FastAPI interpreta "search" como un ID
  GET /search        ← NUNCA se alcanza
```

---

## 6. Flujo por Endpoint

### 6.1 `POST /api/v1/auth/register` — Registrar Usuario

```
DATOS DE ENTRADA (Body JSON):
{
    "nombre": "Dr. Garcia",          // str, 2-150 chars, obligatorio
    "email": "garcia@hospital.com",  // EmailStr, unico, obligatorio
    "password": "mi_password",       // str, 6-128 chars, obligatorio
    // NO existe campo "rol" a proposito (seguridad)
}

FLUJO INTERNO:
  Controller → AuthService.register()
    → Valida que el email NO exista (UsuarioRepository.get_by_email)
    → Hashea la contrasena con bcrypt
    → Crea el usuario con rol="usuario" (SIEMPRE: el registro publico no
      puede crear admins — para eso existe POST /admin/usuarios)
    → UsuarioRepository.create()

DATOS QUE SE GUARDAN EN MySQL (tabla usuarios):
  id              → AUTO_INCREMENT
  nombre          → "Dr. Garcia"
  email           → "garcia@hospital.com"
  password_hash   → "$2b$12$LJ3m4ys3G..." (bcrypt, NUNCA el texto plano)
  rol             → "usuario" (siempre)
  activo          → TRUE
  created_at      → CURRENT_TIMESTAMP
  updated_at      → CURRENT_TIMESTAMP

RESPUESTA (201):
{
    "id": 1,
    "nombre": "Dr. Garcia",
    "email": "garcia@hospital.com",
    "rol": "usuario",
    "activo": true,
    "created_at": "2025-01-15T10:30:00"
}

ERRORES:
  409 → "Ya existe un usuario con ese email"
  422 → Validacion de Pydantic (email invalido, password muy corta, etc.)
```

---

### 6.2 `POST /api/v1/auth/login` — Iniciar Sesion

```
DATOS DE ENTRADA (Body JSON):
{
    "email": "garcia@hospital.com",  // EmailStr, obligatorio
    "password": "mi_password"        // str, obligatorio
}

FLUJO INTERNO:
  Controller → AuthService.login()
    → UsuarioRepository.get_by_email(email)
    → Verifica que el usuario exista y este activo
    → bcrypt.verify(password, password_hash) → True/False
    → Crea token JWT con {sub: id, rol: rol, exp: +60min}

DATOS QUE SE GUARDAN EN MySQL:
  Ninguno — es solo lectura + creacion de token

RESPUESTA (200):
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "usuario": {
        "id": 1,
        "nombre": "Dr. Garcia",
        "email": "garcia@hospital.com",
        "rol": "usuario",
        "activo": true,
        "created_at": "2025-01-15T10:30:00"
    }
}

ERRORES:
  401 → "Credenciales invalidas" (email no existe, password incorrecto, o usuario inactivo)
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
    → Verifica que este activo
    → Retorna {id, nombre, email, rol, activo, created_at}

DATOS QUE SE LEEN DE MySQL:
  SELECT * FROM usuarios WHERE id = 1

RESPUESTA (200):
{
    "id": 1,
    "nombre": "Dr. Garcia",
    "email": "garcia@hospital.com",
    "rol": "usuario",
    "activo": true,
    "created_at": "2025-01-15T10:30:00"
}

ERRORES:
  401 → Token invalido/expirado o usuario inactivo
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
         usuario_creador_id, talla_cm, peso_kg, created_at, updated_at
  FROM pacientes ORDER BY id

RESPUESTA (200):
[
    {
        "id": 1,
        "nombre": "Juan Perez Rodriguez",
        "documento_identidad": "1032456789",
        "fecha_nacimiento": "1965-05-20",
        "sexo": "M",
        "talla_cm": 172.5,
        "peso_kg": 85.3,
        "usuario_creador_id": 2,
        "created_at": "2025-01-15T10:30:00",
        "updated_at": "2025-01-15T10:30:00"
    },
    ...
]
```

---

### 6.5 `GET /api/v1/pacientes/search` — Busqueda Parcial

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
    {"id": 1, "nombre": "Juan Perez", "documento_identidad": "1032456789", ...}
]

NOTA: Para autocomplete en el frontend — mientras el usuario escribe,
se envia la query y se muestran las sugerencias.
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
    "nombre": "Juan Perez Rodriguez",
    "documento_identidad": "1032456789",
    "fecha_nacimiento": "1965-05-20",
    "sexo": "M",
    "talla_cm": 172.5,
    "peso_kg": 85.3,
    "usuario_creador_id": 2,
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:30:00"
}

ERRORES:
  404 → "Paciente no encontrado"
```

---

### 6.7 `POST /api/v1/pacientes/` — Crear Paciente (formato detallado)

```
DATOS DE ENTRADA (Body JSON):
{
    "tipo_documento": "DNI",                    // Enum(DNI, CE, Pasaporte), default DNI
    "documento_identidad": "1032456789",        // str, 5-30 chars, UNICO, obligatorio
    "numero_historia_clinica": "72769512",      // str, UNICO, opcional
    "apellido_paterno": "Perez",               // str, 2-100, obligatorio
    "apellido_materno": "Rodriguez",           // str, opcional
    "nombres": "Juan",                          // str, 2-100, obligatorio
    "fecha_nacimiento": "1965-05-20",          // date (YYYY-MM-DD), obligatorio
    "sexo": "M",                                // Enum(M, F), obligatorio
    "telefono": "987654321",                    // str, opcional
    "direccion": "Av. Principal 123",           // str, opcional
    "distrito_id": 1,                           // int, FK → distritos.id (dropdown del doctor)
    "localidad_id": 3,                          // int, FK → localidades.id (debe pertenecer al distrito)
    "tipo_seguro": "SIS",                       // Enum(SIS, EsSalud, Privado, Otro), default SIS
    "codigo_afiliacion_seguro": "040-2-1032456789", // str, opcional
    "talla_cm": 172.5,                          // float, >0, <=300, opcional
    "peso_kg": 85.3                             // float, >0, <=500, opcional
}

FLUJO INTERNO:
  Controller → PacienteService.create(data, usuario_creador_id=user["id"])
    → Valida que NO exista otro paciente con ese documento
    → Valida que la historia clinica no este en uso (si se envia)
    → Valida distrito_id (debe existir) y localidad_id (debe existir
      Y pertenecer al distrito elegido)
    → PacienteRepository.create(usuario_creador_id=2, tipo_documento, ...)
    → INSERT INTO pacientes (...)

DATOS QUE SE GUARDAN EN MySQL (tabla pacientes):
  id, tipo_documento, documento_identidad, numero_historia_clinica,
  apellido_paterno, apellido_materno, nombres, fecha_nacimiento, sexo,
  telefono, direccion, distrito_id, localidad_id, tipo_seguro,
  codigo_afiliacion_seguro, usuario_creador_id, activo, talla_cm, peso_kg,
  created_at, updated_at

NOTA 1: usuario_creador_id se llena AUTOMATICAMENTE con el ID del usuario
autenticado (JWT). No se envia en el body.

NOTA 2: distrito_id/localidad_id se envian como ID, pero la RESPUESTA
incluye tambien los NOMBRES resueltos ("distrito": "Alto Selva Alegre")
para que el frontend los muestre sin consultas extra.

NOTA 3: El doctor NO escribe los nombres de distritos/localidades —
los ELIGE de las opciones que carga de GET /api/v1/catalogos/*
(los catálogos los gestiona el admin).

RESPUESTA (201):
{
    "id": 1,
    "tipo_documento": "DNI",
    "documento_identidad": "1032456789",
    "numero_historia_clinica": "72769512",
    "apellido_paterno": "Perez",
    "apellido_materno": "Rodriguez",
    "nombres": "Juan",
    "nombre_completo": "PEREZ RODRIGUEZ, Juan",
    "fecha_nacimiento": "1965-05-20",
    "sexo": "M",
    "telefono": "987654321",
    "direccion": "Av. Principal 123",
    "distrito_id": 1,
    "distrito": "Alto Selva Alegre",
    "localidad_id": 3,
    "localidad": "Chilpinilla",
    "tipo_seguro": "SIS",
    "codigo_afiliacion_seguro": "040-2-1032456789",
    "usuario_creador_id": 2,
    "activo": true,
    "talla_cm": 172.5,
    "peso_kg": 85.3,
    "created_at": "2026-09-01T16:02:54",
    "updated_at": "2026-09-01T16:02:54"
}

ERRORES:
  409 → "Ya existe un paciente con ese documento" | "Ya existe un paciente
        con ese numero de historia clinica" | "El distrito seleccionado no
        existe" | "La localidad no pertenece al distrito seleccionado"
  422 → Validacion de Pydantic
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
  Controller → PacienteService.update(
        1, data, current_user_id=user.id, current_user_rol=user.rol)
    → El SERVICE verifica existencia + PERMISOS (no el controller):
        Si user["rol"] == "admin" → puede editar cualquier paciente
        Si user["rol"] == "usuario" → solo puede editar si
            paciente.usuario_creador_id == user["id"]
        (si no tiene permiso → PermissionError → controller traduce a 403)
    → data.model_dump(exclude_unset=True) → {"talla_cm": 166.0, "peso_kg": 71.5}
    → Valida distrito/localidad y duplicados de historia clinica
    → PacienteRepository.update(paciente, talla_cm=166.0, peso_kg=71.5)
    → UPDATE pacientes SET talla_cm=166.0, peso_kg=71.5, updated_at=NOW() WHERE id=1

REGLAS DE PERMISOS:
  Admin:       Puede editar CUALQUIER paciente
  Medico:      Solo puede editar pacientes que EL registro (usuario_creador_id == su ID)
  Enfermera:   Solo puede editar pacientes que EL registro

  Si un medico intenta editar un paciente de otro medico → 403 FORBIDDEN

DATOS QUE SE ACTUALIZAN EN MySQL:
  Solo los campos enviados + updated_at se actualizan automaticamente

RESPUESTA (200):
{
    "id": 1,
    "nombre": "Juan Perez Rodriguez",  // NO cambio
    "documento_identidad": "1032456789", // NO cambio
    "fecha_nacimiento": "1965-05-20",  // NO cambio
    "sexo": "M",                        // NO cambio
    "talla_cm": 166.0,                 // SI cambio
    "peso_kg": 71.5,                   // SI cambio
    "usuario_creador_id": 2,           // NO cambio
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T11:45:00" // SI cambio
}

ERRORES:
  403 → "No tienes permiso para editar este paciente"
  404 → "Paciente no encontrado"
```

---

### 6.9 `POST /api/v1/evaluaciones/` — Crear Evaluacion (ML)

Este es el endpoint MAS IMPORTANTE del sistema.

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
    limit  → int, default 50 (maximo de resultados)
    offset → int, default 0  (cuantos saltar)

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
        "created_at": "2025-01-20T14:00:00"   // mas reciente primero
    },
    {
        "id": 1,
        "paciente_id": 1,
        "edad": 53,
        "probabilidad": 0.650000,
        "clasificacion": "alto",
        "created_at": "2025-01-15T10:30:00"   // mas antigua
    }
]

NOTA: Permite ver como ha cambiado el riesgo cardiaco del paciente
a lo largo del tiempo.
```

---

### 6.12 `GET /api/v1/evaluaciones/{id}` — Ver Evaluacion

```
DATOS DE ENTRADA:
  Header: Authorization: Bearer <token>
  Path param: evaluacion_id=1 (int)

RESPUESTA (200): EvaluacionResponse completa (igual que el POST)

ERRORES:
  404 → "Evaluacion no encontrada"
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
  401 → Token invalido
```

---

### 6.14 `GET /api/v1/admin/usuarios/{id}` — Obtener Usuario (Admin)

```
DATOS DE ENTRADA:
  Header: Authorization: Bearer <token> (debe ser rol "admin")
  Path param: usuario_id=2 (int)

FLUJO INTERNO:
  Controller → Depends(require_admin)
    → AdminService.get_usuario(2)
    → UsuarioRepository.get_by_id(2)
    → SELECT * FROM usuarios WHERE id = 2

RESPUESTA (200):
{
    "id": 2,
    "nombre": "Dr. Carlos Garcia",
    "email": "dr.garcia@healthcure.com",
    "rol": "usuario",
    "activo": true,
    "created_at": "2025-01-15T10:30:00"
}

ERRORES:
  404 → "Usuario no encontrado"
  403 → "Se requiere rol de administrador"
```

---

### 6.15 `POST /api/v1/admin/usuarios` — Crear Usuario (Admin)

Diferencia con el registro publico: el admin SI puede elegir el rol.

```
DATOS DE ENTRADA (Body JSON):
{
    "nombre": "Dr. Carlos Mendez",      // str, 2-150 chars, obligatorio
    "email": "dr.mendez@hospital.com",  // EmailStr, unico, obligatorio
    "password": "mendez123",            // str, 6-128 chars, obligatorio
    "rol": "admin"                      // Enum("admin","usuario"), default "usuario"
}

FLUJO INTERNO:
  Controller → Depends(require_admin)
    → AdminService.create_usuario(data)
    → Valida que el email NO exista
    → Hashea la contrasena con bcrypt
    → UsuarioRepository.create(nombre, email, password_hash, rol="admin")

DATOS QUE SE GUARDAN EN MySQL:
  id              → AUTO_INCREMENT
  nombre          → "Dr. Carlos Mendez"
  email           → "dr.mendez@hospital.com"
  password_hash   → "$2b$12$..." (bcrypt)
  rol             → "admin" (SII, a diferencia del registro publico)
  activo          → TRUE
  created_at      → CURRENT_TIMESTAMP

RESPUESTA (201):
{
    "id": 6,
    "nombre": "Dr. Carlos Mendez",
    "email": "dr.mendez@hospital.com",
    "rol": "admin",
    "activo": true,
    "created_at": "2025-01-15T10:30:00"
}

ERRORES:
  409 → "Ya existe un usuario con ese email"
  403 → "Se requiere rol de administrador"
  422 → Validacion de Pydantic
```

---

### 6.16 `PUT /api/v1/admin/usuarios/{id}` — Actualizar Usuario (Admin)

```
DATOS DE ENTRADA (Body JSON — solo campos a actualizar):
{
    "nombre": "Dr. Carlos Mendez (Editado)",
    "rol": "admin",
    "activo": true
}
// Todos los campos son opcionales. Solo se actualiza lo que se envie.

CAMPOS DISPONIBLES PARA ACTUALIZAR:
  nombre     → str, 2-150 chars
  email      → EmailStr (verifica que no este en uso por otro)
  password   → str, 6-128 chars (se hashea automaticamente)
  rol        → Enum("admin","usuario")
  activo     → bool

FLUJO INTERNO:
  Controller → Depends(require_admin)
    → AdminService.update_usuario(usuario_id, data, current_admin_id=admin.id)
    → data.model_dump(exclude_unset=True) → solo campos enviados
    → Si cambio email → verifica duplicado
    → Si cambio password → hashea con bcrypt
    → GUARDS anti-lockout (solo si se toca rol o activo):
        1) No puedes quitarte el rol admin ni desactivar tu PROPIA cuenta
        2) No puedes degradar/desactivar al ULTIMO admin activo
    → UsuarioRepository.update(usuario_id, **campos)
    → SELECT * FROM usuarios WHERE id=usuario_id (recargar)

RESPUESTA (200):
{
    "id": 6,
    "nombre": "Dr. Carlos Mendez (Editado)",
    "email": "dr.mendez@hospital.com",
    "rol": "admin",
    "activo": true,
    "created_at": "2025-01-15T10:30:00"
}

ERRORES:
  404 → "Usuario no encontrado"
  409 → "Ya existe otro usuario con ese email"
  409 → "No puedes desactivar ni cambiar el rol de tu propia cuenta..." (guard 1)
  409 → "No puedes desactivar al último administrador activo..." (guard 2)
  403 → "Se requiere rol de administrador"
  422 → Validacion de Pydantic

NOTA PARA PRUEBAS: para probar este endpoint NO edites a los usuarios del
seed (admin/Dr. Garcia). Crea primero un usuario de prueba con 6.15 y usa
su ID — asi las credenciales del seed quedan intactas.
```

---

### 6.17 `PUT /api/v1/admin/usuarios/{id}/activate` — Reactivar Usuario

```
DATOS DE ENTRADA:
  Header: Authorization: Bearer <token> (debe ser rol "admin")
  Path param: usuario_id=3 (int)

FLUJO INTERNO:
  Controller → Depends(require_admin)
    → AdminService.activate_usuario(3)
    → UPDATE usuarios SET activo=TRUE WHERE id=3

DATOS QUE SE ACTUALIZAN EN MySQL:
  activo → TRUE (reactiva al usuario)
  updated_at → CURRENT_TIMESTAMP

RESPUESTA (200):
{
    "id": 3,
    "nombre": "Enfermera Ana Martinez",
    "email": "ana.martinez@healthcure.com",
    "rol": "usuario",
    "activo": true,
    "created_at": "2025-01-15T10:30:00"
}

EFECTOS:
  + El usuario PUEDE hacer login nuevamente
  + Sus evaluaciones siguen intactas

ERRORES:
  404 → "Usuario no encontrado"
  403 → "Se requiere rol de administrador"
```

---

### 6.18 `PUT /api/v1/admin/usuarios/{id}/deactivate` — Desactivar Usuario

```
DATOS DE ENTRADA:
  Header: Authorization: Bearer <token> (debe ser rol "admin")
  Path param: usuario_id=3 (int)

FLUJO INTERNO:
  Controller → Depends(require_admin)
    → AdminService.deactivate_usuario(3, current_admin_id=ID_del_admin)
    → GUARDS anti-lockout (antes de desactivar):
        1) No puedes desactivar tu PROPIA cuenta
        2) No puedes desactivar al ULTIMO admin activo del sistema
    → UPDATE usuarios SET activo=FALSE WHERE id=3

DATOS QUE SE ACTUALIZAN EN MySQL:
  activo → FALSE (soft delete, NO borra el registro)
  updated_at → CURRENT_TIMESTAMP

RESPUESTA (200): El objeto UsuarioResponse completo (igual que activate)
{
    "id": 3, "nombre": "...", "email": "...", "rol": "usuario",
    "activo": false, "created_at": "..."
}

EFECTOS DEL SOFT DELETE:
  X El usuario NO puede hacer login (AuthService valida activo=True)
  V El usuario SIGUE existiendo en la BD (para auditoria)
  V Sus evaluaciones siguen intactas (FK no se rompen)

ERRORES:
  404 → "Usuario no encontrado"
  409 → "No puedes desactivar ni cambiar el rol de tu propia cuenta..." (guard 1)
  409 → "No puedes desactivar al último administrador activo..." (guard 2)
  403 → "Se requiere rol de administrador"
```

---

## 7. Mapa de CRUD

| Entidad | Create | Read (uno) | Read (listar) | Read (buscar) | Update | Delete |
|---------|--------|------------|---------------|---------------|--------|--------|
| **Usuarios** | `POST /auth/register` (publico) + `POST /admin/usuarios` (admin) | `GET /auth/me` + `GET /admin/usuarios/{id}` (admin) | `GET /admin/usuarios` *(admin)* | — | `PUT /admin/usuarios/{id}` *(admin)* | `PUT /admin/{id}/deactivate` *(admin, soft)* + `PUT /admin/{id}/activate` *(admin)* |
| **Pacientes** | `POST /pacientes/` | `GET /pacientes/{id}` + `GET /by-documento/{doc}` | `GET /pacientes/` | `GET /search?documento=` | `PUT /pacientes/{id}` *(creador o admin)* | — |
| **Evaluaciones** | `POST /evaluaciones/` | `GET /evaluaciones/{id}` | `GET /evaluaciones/` *(paginado)* | `GET /by-paciente/{id}` | — | — |
| **Distritos** *(catálogo)* | `POST /admin/distritos` *(admin)* | `GET /admin/distritos/{id}` | `GET /admin/distritos` *(admin)* + `GET /catalogos/distritos` *(doctor)* | — | `PUT /admin/distritos/{id}` *(admin)* | `PUT /admin/distritos/{id}/deactivate` *(admin, soft)* |
| **Localidades** *(catálogo)* | `POST /admin/localidades` *(admin)* | `GET /admin/localidades/{id}` | `GET /admin/localidades` *(admin)* + `GET /catalogos/localidades` *(doctor)* | `GET /catalogos/localidades?distrito_id=` | `PUT /admin/localidades/{id}` *(admin)* | `PUT /admin/localidades/{id}/deactivate` *(admin, soft)* |

**Notas:**
- No hay DELETE duro en ninguna entidad (soft delete en usuarios/distritos/localidades, no existe en pacientes/evaluaciones)
- No hay UPDATE de evaluaciones (son inmutables — cada una es una instantanea)
- Los pacientes tienen permisos: solo el creador o un admin puede editarlos
- El admin puede crear usuarios con cualquier rol (admin o usuario)
- **Catálogos (distritos/localidades): el admin los gestiona (CRUD), el doctor solo los LEE**
  para llenar sus formularios (dropdowns en /catalogos/*)
- El paciente referencia distrito/localidad por ID, y la respuesta incluye el NOMBRE
  resuelto para mostrar (ej: "distrito": "Alto Selva Alegre")

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

| # | Variable | Tipo | Rango | Descripcion |
|---|----------|------|-------|-------------|
| 1 | `edad` | int | 1-120 | Edad del paciente |
| 2 | `presion_alta` | bool→int | 0/1 | Diagnostico de presion alta |
| 3 | `colesterol_alto` | bool→int | 0/1 | Colesterol alto diagnosticado |
| 4 | `tabaquismo` | bool→int | 0/1 | Fuma o fumo >=100 cigarrillos |
| 5 | `actividad_fisica` | bool→int | 0/1 | Hace actividad fisica en ultimos 30 dias |
| 6 | `antecedente_acv` | bool→int | 0/1 | Antecedente de accidente cerebrovascular |
| 7 | `diabetes` | bool→int | 0/1 | Diagnostico de diabetes |
| 8 | `salud_general` | int | 1-5 | Escala CDC: 1=excelente, 5=mala |
| 9 | `dificultad_para_caminar` | bool→int | 0/1 | Dificultad para caminar subir escaleras |

**Orden de columnas que el modelo espera** (PREDEFINE en `preprocessor.py`):
```
edad → presion_alta → colesterol_alto → tabaquismo → actividad_fisica
→ antecedente_acv → diabetes → salud_general → dificultad_para_caminar
```

### 8.3 Clasificacion de Riesgo

```
Probabilidad de enfermedad cardiaca:

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
| **Archivo** | `app/resources/modelo_cardiaco.joblib` (no existe aun) |
| **Version** | `1.0.0` |
| **Estado** | El server funciona sin el modelo — solo falla al predecir |

### 8.5 Comportamiento sin Modelo

Si el archivo `.joblib` no existe:
- Login, registro, pacientes → funcionan normal
- `POST /evaluaciones/` → retorna **500** con "Modelo ML no disponible"
- Seed de datos de prueba → crea usuarios, pacientes y evaluaciones de ejemplo (con datos hardcodeados, no del ML)

---

## 9. Seed de Datos de Prueba

Ejecuta automaticamente al iniciar el servidor (`main.py` lifespan). Solo crea datos si la BD esta vacia.

### 9.1 Usuarios Creados

| Nombre | Email | Password | Rol |
|--------|-------|----------|-----|
| Administrador | `admin@healthcure.com` | `admin123` | **admin** |
| Dr. Carlos Garcia | `dr.garcia@healthcure.com` | `doctor123` | usuario |
| Enfermera Ana Martinez | `ana.martinez@healthcure.com` | `enfermera123` | usuario |

### 9.2 Catálogos Creados (distritos y localidades)

| Distrito | Localidades |
|----------|-------------|
| Alto Selva Alegre | Chilpinilla, El Mirador, La Tomilla, Mariano Melgar |
| Cayma | Huachipa, La Pampilla, Trujamanes |
| Miraflores | Campina, El Golf, Lara |
| Yanahuara | La Perla, Mirador de Yanahuara |
| Cerro Colorado | El Progreso, La Mansión, Tahuaycani |

### 9.3 Pacientes Creados (formato detallado)

Todos creados por Dr. Garcia (usuario_creador_id = 2):

| Apellidos, Nombres | Documento | H. Clinica | Distrito | Localidad | Seguro | Sexo |
|--------------------|-----------|------------|----------|-----------|--------|------|
| PEREZ RODRIGUEZ, Juan | 1032456789 | 72769512 | Alto Selva Alegre | Chilpinilla | SIS | M |
| LOPEZ QUISPE, Maria Fernanda | 1098765432 | 88123456 | Cayma | La Pampilla | EsSalud | F |
| GOMEZ CHAVEZ, Roberto Carlos | 1122334455 | 90345678 | Cerro Colorado | Tahuaycani | SIS | M |
| MARTINEZ ROJAS, Laura Daniela | 1055667788 | 76543210 | Yanahuara | Mirador de Yanahuara | Privado | F |
| SANCHEZ HUAMAN, Pedro Antonio | 1066778899 | 69988776 | Miraflores | El Golf | EsSalud | M |

### 9.4 Evaluaciones Creadas (ejemplos hardcodeados)

| Paciente | Edad | Riesgo | Probabilidad | Clasificacion | Factores clave |
|----------|------|--------|-------------|---------------|----------------|
| Juan Perez | 61 | Alto | 78.5% | **alto** | presion + colesterol + tabaquismo + diabetes |
| Maria Lopez | 48 | Moderado | 35.2% | **moderado** | solo presion alta, activa |
| Roberto Gomez | 71 | Alto | 92.1% | **alto** | presion + colesterol + ACV + diabetes + inmovilidad |

---

## 10. Matriz de Permisos

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

### Reglas de Permisos para Pacientes

```
QUIEN PUEDE EDITAR UN PACIENTE?

  Si eres ADMIN → puedes editar CUALQUIER paciente
  Si eres MEDICO/ENFERMERA → solo puedes editar pacientes que TU registraste
    (donde paciente.usuario_creador_id == tu usuario.id)

  Si un medico intenta editar un paciente de otro medico:
    → 403 FORBIDDEN: "No tienes permiso para editar este paciente"
```

### Diferencia entre Registro Publico y Admin

```
POST /auth/register (cualquiera):
  - SIEMPRE crea usuarios con rol "usuario"
  - El schema NI SIQUIERA incluye campo "rol" (si envias "rol": "admin"
    como extra, Pydantic lo ignora y el usuario queda "usuario")

POST /admin/usuarios (solo admin):
  - El admin PUEDE elegir el rol ("admin" o "usuario")
  - Puede crear otros admins
```

### Reglas anti-lockout (usuarios admin)

```
PUT /admin/usuarios/{id}  y  PUT /admin/usuarios/{id}/deactivate

Un admin NO puede:
  1. Desactivar ni quitarse el rol admin a SI MISMO             → 409
  2. Desactivar/degradar al ULTIMO admin activo del sistema      → 409

Motivo: evitar que un error deje la app SIN NINGUN administrador
(lockout total). Con 2+ admins activos, un admin SI puede desactivar
normalmente a otro admin o a cualquier usuario normal.
```

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
│   ├── paciente.py            # Tabla pacientes (formato detallado + usuario_creador_id)
│   ├── evaluacion.py          # Tabla evaluaciones (predicciones ML)
│   ├── distrito.py            # Catalogo de distritos (gestiona el admin)
│   └── localidad.py           # Catalogo de localidades (depende del distrito)
├── schemas/
│   ├── __init__.py
│   ├── usuario.py             # UsuarioCreate, Login, Response, Token, Update, AdminCreate
│   ├── paciente.py            # PacienteCreate, Update, Response
│   ├── evaluacion.py          # EvaluacionCreate, Response, PredictionResult
│   └── catalogo.py            # Distrito/Localidad Create, Update, Response
├── mappers/
│   ├── __init__.py
│   └── evaluacion_mapper.py   # Request→ML→ORM→Response
├── repositories/
│   ├── __init__.py
│   ├── usuario_repository.py  # CRUD usuarios (+ update, activate, count_active_admins)
│   ├── paciente_repository.py # CRUD pacientes (+ joinedload de distrito/localidad)
│   ├── evaluacion_repository.py # CRUD evaluaciones
│   ├── distrito_repository.py # CRUD distritos (catálogo)
│   └── localidad_repository.py # CRUD localidades (catálogo)
├── ml/
│   ├── __init__.py
│   ├── model_loader.py        # Singleton: carga .joblib una vez
│   ├── predictor.py           # predict() → probabilidad + clasificacion
│   └── preprocessor.py        # Limpieza/validacion/orden de columnas
├── services/
│   ├── __init__.py
│   ├── auth_service.py        # JWT + bcrypt + registro/login
│   ├── paciente_service.py    # CRUD pacientes + permisos (solo creador o admin)
│   ├── evaluacion_service.py  # Orquesta ML + BD
│   ├── admin_service.py       # CRUD usuarios + guards anti-lockout + CRUD catálogos
│   └── catalogo_service.py    # Lectura de catálogos para el doctor (dropdowns)
├── api/
│   ├── __init__.py
│   ├── deps.py                # get_current_user + require_admin
│   └── v1/
│       ├── __init__.py
│       ├── auth.py            # /auth/*
│       ├── pacientes.py       # /pacientes/* (permisos en el Service)
│       ├── evaluaciones.py    # /evaluaciones/*
│       ├── catalogos.py       # /catalogos/* (opciones activas para el doctor)
│       └── admin.py           # /admin/* (usuarios + distritos + localidades)
├── exceptions/
│   ├── __init__.py
│   └── ml_exceptions.py       # ModelNotFoundError, PredictionError, etc.
├── seeds/
│   ├── __init__.py
│   └── seed.py                # Datos de prueba + backfill idempotente de creadores
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Fixtures: SQLite en memoria (sin MySQL)
│   ├── test_evaluacion_mapper.py   # Transformaciones del mapper
│   ├── test_preprocessor.py        # Validacion del preprocesador ML
│   └── test_permisos_pacientes.py  # Permisos + guards anti-lockout (HTTP)
├── clients/
│   └── __init__.py            # (vacio — no se consumen APIs externas)
└── resources/
    ├── __init__.py
    ├── schema.sql             # DDL MySQL completo (referencia)
    ├── modelo_cardiaco.joblib # (pendiente — modelo entrenado)
    └── plantilla_pacientes.csv # (pendiente — plantilla de carga)

main.py                         # FastAPI entry point + lifespan (seed)
requirements.txt                # Dependencias de produccion
requirements-dev.txt            # Dependencias de tests (pytest, httpx)
.gitignore                      # Excluye .env, __pycache__, venv, etc.
.env.example                    # Template del .env (SIEMPRE versionado)
.env                            # Credenciales reales — NO se commitea
README.md                       # Documentacion del proyecto
postman/
└── HealthCure_API.postman_collection.json  # Coleccion Postman completa
docs/
└── MAPPEO_BACKEND.md           # Este documento
```
