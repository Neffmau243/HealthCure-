# HealthCure — CardioPredict: Mapeo de Rutas Frontend ↔ Backend

> Estado de la integración entre el backend FastAPI y el frontend React.
> Incluye el mapa completo de rutas de ambos lados, su correspondencia,
> las desalineaciones que se corrigieron y lo que queda pendiente.
>
> Última revisión: tras la integración del MVP (rama `ML1.2`).

---

## Tabla de Contenidos

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Mapa de rutas del Backend](#2-mapa-de-rutas-del-backend)
3. [Mapa de rutas del Frontend](#3-mapa-de-rutas-del-frontend)
4. [Contraste Frontend ↔ Backend](#4-contraste-frontend--backend)
5. [Desalineaciones corregidas](#5-desalineaciones-corregidas)
6. [Lo que ya tenemos (✅)](#6-lo-que-ya-tenemos-)
7. [Pendientes y mejoras futuras](#7-pendientes-y-mejoras-futuras)
8. [Cómo levantar y verificar](#8-cómo-levantar-y-verificar)
9. [Anexo: contratos de datos](#9-anexo-contratos-de-datos)

---

## 1. Resumen ejecutivo

| Aspecto | Backend (FastAPI) | Frontend (React + Vite) |
|---------|-------------------|--------------------------|
| **Estado** | ✅ 34 endpoints | ✅ **Integrado con la API** |
| **Puerto / URL** | `http://localhost:8000` | `http://localhost:5173` |
| **Prefijo API** | `/api/v1` | `http://localhost:8000/api/v1` (`VITE_API_URL`) |
| **Auth** | JWT + bcrypt + roles `admin` / `usuario` | Login real, JWT en `localStorage`, 401 → login |
| **Datos** | MySQL (`healthcure_db`) + `atenciones` | Sin mocks: todo viene de la API |

**Conclusión:** el flujo completo funciona end-to-end — login → pacientes → triaje/evaluación ML →
consulta y atención → historia clínica → FUA PDF → gestión de usuarios (admin).

---

## 2. Mapa de rutas del Backend

Todas las rutas viven bajo el prefijo `/api/v1` (excepto las de sistema).
Routers registrados en `main.py`: `auth`, `pacientes`, `evaluaciones`, `atenciones`, `admin`, `catalogos`.

### 2.1 Sistema (sin prefijo)

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/health` | ❌ | Health check: `{status, app, version}` |
| `GET` | `/docs` | ❌ | Swagger UI (probar endpoints) |
| `GET` | `/redoc` | ❌ | Documentación alternativa |
| `GET` | `/openapi.json` | ❌ | Esquema OpenAPI |

### 2.2 Auth — `/api/v1/auth`

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/auth/register` | ❌ | Registro público. **Siempre rol `usuario`**. 201 / 409 / 422 |
| `POST` | `/auth/login` | ❌ | Login → `{access_token, token_type, usuario}`. 200 / 401 |
| `GET` | `/auth/me` | ✅ | Datos del usuario autenticado. 200 / 401 |

### 2.3 Pacientes — `/api/v1/pacientes` (requiere JWT)

| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| `GET` | `/pacientes/` | cualquiera | Listar todos los pacientes |
| `GET` | `/pacientes/search?documento=` | cualquiera | Búsqueda parcial (autocomplete, max 10) |
| `GET` | `/pacientes/by-documento/{documento}` | cualquiera | Documento exacto. 404 si no existe |
| `GET` | `/pacientes/{paciente_id}` | cualquiera | Obtener uno por ID |
| `POST` | `/pacientes/` | cualquiera | Registrar paciente (formato peruano). 201 / 409 |
| `PUT` | `/pacientes/{paciente_id}` | **creador o admin** | Actualizar parcial. 403 si no es su creador |

### 2.4 Evaluaciones cardíacas (ML) — `/api/v1/evaluaciones` (requiere JWT)

| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| `POST` | `/evaluaciones/` | cualquiera | **★ Predicción ML + triaje clínico**. 201 / 400 / 500 |
| `GET` | `/evaluaciones/` | cualquiera | Listar paginado (`?limit=50&offset=0`) |
| `GET` | `/evaluaciones/by-paciente/{paciente_id}` | cualquiera | Historial del paciente |
| `GET` | `/evaluaciones/{evaluacion_id}` | cualquiera | Ver una evaluación. 404 |
| `GET` | `/evaluaciones/{evaluacion_id}/fua` | cualquiera | **PDF Formato Único de Atención** (oficio) |

### 2.5 Atenciones del consultorio — `/api/v1/atenciones` (requiere JWT) ★ NUEVO

| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| `POST` | `/atenciones/` | cualquiera | Registrar atención (diagnóstico/tratamiento/indicaciones). 201 / 400 |
| `GET` | `/atenciones/` | cualquiera | Listar paginado (`?limit=50&offset=0`) |
| `GET` | `/atenciones/by-paciente/{paciente_id}` | cualquiera | Historial de atenciones del paciente |
| `GET` | `/atenciones/{atencion_id}` | cualquiera | Ver una atención. 404 |

**Reglas de validación del `POST /atenciones/`:**
- El `paciente_id` debe existir (si no → 400).
- Si se envía `evaluacion_id`, la evaluación debe existir **y pertenecer al mismo paciente** (si no → 400).

### 2.6 Catálogos (lectura para el médico) — `/api/v1/catalogos` (requiere JWT)

| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| `GET` | `/catalogos/distritos` | cualquiera | Distritos **activos** (dropdown) |
| `GET` | `/catalogos/localidades?distrito_id=` | cualquiera | Localidades activas (dropdown encadenado) |

### 2.7 Admin — `/api/v1/admin` (requiere JWT + rol `admin`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/admin/usuarios` | Listar usuarios |
| `GET` | `/admin/usuarios/{usuario_id}` | Ver un usuario |
| `POST` | `/admin/usuarios` | Crear usuario (**sí puede elegir rol**) |
| `PUT` | `/admin/usuarios/{usuario_id}` | Actualizar parcial (guards anti-lockout) |
| `PUT` | `/admin/usuarios/{usuario_id}/activate` | Reactivar |
| `PUT` | `/admin/usuarios/{usuario_id}/deactivate` | Desactivar (soft delete) |
| `GET` | `/admin/distritos` | Listar distritos (activos e inactivos) |
| `POST` | `/admin/distritos` | Crear distrito |
| `PUT` | `/admin/distritos/{distrito_id}` | Actualizar distrito |
| `PUT` | `/admin/distritos/{distrito_id}/deactivate` | Desactivar distrito |
| `GET` | `/admin/localidades?distrito_id=` | Listar localidades |
| `POST` | `/admin/localidades` | Crear localidad |
| `PUT` | `/admin/localidades/{localidad_id}` | Actualizar localidad |
| `PUT` | `/admin/localidades/{localidad_id}/deactivate` | Desactivar localidad |

**Total: 34 endpoints de negocio + 4 de sistema/docs.**

### 2.8 Matriz de permisos (resumen)

| Grupo | Sin token | Token `usuario` | Token `admin` |
|-------|-----------|-----------------|---------------|
| `/health`, `/auth/register`, `/auth/login` | 200/201 | 200/201 | 200/201 |
| `/auth/me`, `/pacientes/*`, `/evaluaciones/*`, `/atenciones/*`, `/catalogos/*` | **401** | 200/201 | 200/201 |
| `/pacientes/{id}` (PUT) | **401** | 200 **solo si es el creador** (si no 403) | 200 |
| `/admin/*` | **401** | **403** | 200/201 |

---

## 3. Mapa de rutas del Frontend

Router: `react-router-dom` en `frontend/src/routes/AppRouter.jsx`.
Layout protegido: `DashboardLayout` (Sidebar + Topbar + `<Outlet />`).

El sidebar está **agrupado por secciones y ordenado por el flujo de atención**
(registrar paciente → triaje → consulta → historial), con los pasos 1-2-3 numerados.

| Ruta | Componente | Sección del sidebar | Endpoints que consume |
|------|-----------|---------------------|----------------------|
| `/login` | `LoginPage` | — | `POST /auth/login` |
| `/dashboard` | `DashboardPage` | Principal | `GET /pacientes/`, `GET /evaluaciones/` |
| `/dashboard/pacientes` | `PacientesPage` | Atención clínica · **paso 1** | `GET/POST /pacientes/`, `PUT /pacientes/{id}`, `GET /catalogos/*` |
| `/dashboard/triaje` | `TriajePage` | Atención clínica · **paso 2** | `GET /pacientes/`, `GET /evaluaciones/`, `POST /evaluaciones/` |
| `/dashboard/consultorio` | `ConsultorioPage` | Atención clínica · **paso 3** | `GET /pacientes/`, `GET /evaluaciones/by-paciente/{id}`, `GET/POST /atenciones/*`, `GET /evaluaciones/{id}/fua` |
| `/dashboard/historiales` | `HistoriasClinicasPage` | Registros | `GET /pacientes/search`, `GET /evaluaciones/by-paciente/{id}`, `GET /atenciones/by-paciente/{id}`, `GET /evaluaciones/{id}/fua` |
| `/dashboard/atenciones` | `AtencionesPage` | Registros | `GET /atenciones/`, `GET /evaluaciones/{id}/fua` |
| `/dashboard/usuarios` | `UsuariosPage` | Administración (solo admin) | `GET/POST/PUT /admin/usuarios*` |
| `*` | → `Navigate` a `/login` | — | — |

### 3.1 Flujo de la Estación de Triaje

La página de Triaje explica el proceso en pantalla y lo ejecuta de verdad:

1. **Guía del proceso** con 3 pasos y contadores en vivo (pacientes, pendientes, evaluaciones).
2. **Filtros** `Pendientes de triaje (n)` · `Ya evaluados (n)` · `Todos (n)`, con los pendientes
   siempre primero (son los que requieren acción).
3. **Botón por paciente** → `Iniciar triaje` (sin evaluaciones, destacado) o
   `Nueva evaluación` (ya evaluado).
4. **Modal de triaje** → captura peso, talla, presión, temperatura, FC, saturación,
   antecedentes, hábitos y percepción de salud; bloquea el envío si el paciente no tiene
   edad válida (≥ 18).
   - **Precarga automática:** el *peso* y la *talla* vienen del registro del paciente
     (`talla_cm` / `peso_kg` de `GET /pacientes/{id}`), y los *antecedentes, hábitos y
     percepción de salud* se heredan de su **última evaluación** (son datos que no cambian
     entre consultas). Los datos variables (presión, temperatura, FC, saturación) siempre
     se piden de nuevo. El modal avisa qué se precargó para que el profesional lo verifique.
5. **`POST /evaluaciones/`** → el modelo ML responde y la vista hace *scroll* automático al
   bloque **“Resultado del modelo ML”** con probabilidad, clasificación, semáforo clínico,
   factores de riesgo/protectores, recomendaciones y descarga del FUA.
6. **Atajo “Siguiente paso: Ir al Consultorio”** para continuar el flujo de atención.

**Piezas de integración:**

- `src/services/api.js` → instancia de `axios`, `BASE_URL` configurable, interceptor de token y de 401.
- `src/services/{auth,pacientes,catalogos,evaluaciones,atenciones,usuarios}.js` → un módulo por recurso.
- `src/context/AuthContext.jsx` + `src/context/useAuth.js` → sesión real (JWT + usuario).
- `src/utils/triaje.js` → IMC, prioridad, parseo de presión y **`construirPayloadEvaluacion`** (las 9 variables del modelo).
- `src/components/triaje/TarjetaTriaje.jsx` → render del resultado ML + triaje clínico + descarga FUA.
- `src/components/ui/{Tabla,Feedback}.jsx` → tabla y estados de carga/error/vacío.

---

## 4. Contraste Frontend ↔ Backend

### 4.1 Flujo completo (funcionando)

```
Login → POST /auth/login → JWT
      ↓
PacientesPage → GET /pacientes/ + GET /catalogos/{distritos,localidades} → tabla real
             → POST /pacientes/ · PUT /pacientes/{id} → alta y edición reales
      ↓
TriajePage → POST /evaluaciones/ → probabilidad + clasificación + TRIAJE CLÍNICO
      ↓
ConsultorioPage → GET /evaluaciones/by-paciente/{id} → resultado del modelo
               → POST /atenciones/ → diagnóstico/tratamiento persistidos
               → GET /evaluaciones/{id}/fua → PDF descargable
      ↓
HistoriasClinicasPage → expediente completo (evaluaciones + atenciones + FUA)
AtencionesPage        → GET /atenciones/ (paginado)
UsuariosPage (admin)  → CRUD de usuarios + activar/desactivar
```

### 4.2 Correspondencia por módulo

| Módulo frontend | Endpoint(s) backend | ¿Conectado? |
|-----------------|---------------------|:-----------:|
| Login / sesión | `POST /auth/login` · `GET /auth/me` | ✅ |
| Pacientes (listar/alta/editar/buscar) | `/pacientes/*` | ✅ |
| Catálogos (distrito/localidad) | `/catalogos/*` | ✅ |
| Triaje (alta de variables) | `POST /evaluaciones/` | ✅ |
| Triaje (interpretación clínica) | `triaje_clinico` en la respuesta | ✅ |
| Historial por paciente | `GET /evaluaciones/by-paciente/{id}` | ✅ |
| Historial general | `GET /evaluaciones/` · `GET /atenciones/` | ✅ |
| Descarga FUA (PDF) | `GET /evaluaciones/{id}/fua` | ✅ |
| Atención del consultorio | `POST /atenciones/` | ✅ |
| Gestión de usuarios | `/admin/usuarios/*` | ✅ |
| Gestión de catálogos (admin) | `/admin/distritos/*`, `/admin/localidades/*` | ⛔ sin UI (API lista) |

---

## 5. Desalineaciones corregidas

| # | Problema (estado anterior) | Corrección aplicada |
|---|----------------------------|---------------------|
| 1 | `baseURL` apuntaba a `http://localhost:8080/api` | `BASE_URL` = `http://localhost:8000/api/v1` (`VITE_API_URL`) |
| 2 | El token se guardaba en `user` pero se leía de `localStorage['token']` | `AuthContext` guarda `token` + `user`; el interceptor los usa |
| 3 | Roles frontend `administrador`/`medico`/`enfermero` vs backend `admin`/`usuario` | `constants/roles.js` usa los roles reales del backend |
| 4 | Login enviaba `username` (texto) | Login envía `{ email, password }` |
| 5 | Login con credenciales y token en duro | `POST /auth/login` real + JWT persistido |
| 6 | `ProtectedRoute` no aplicaba `PERMISSIONS` (no recibía `path`) | Usa `useLocation().pathname` |
| 7 | Campos mock (`dni`, `apellidos`, `genero`) ≠ backend | Se usan `documento_identidad`, `apellido_paterno/materno`, `sexo` |
| 8 | `TriajePage` enviaba 17 variables BRFSS → 422 | `construirPayloadEvaluacion` envía las 9 variables correctas |
| 9 | `ConsultorioPage` llamaba a `finalizarAtencion` (no existía) | Consultorio reconstruido sobre `/evaluaciones` y `/atenciones` |
| 10 | Navegaba a `/dashboard/historial` (ruta inexistente) | Navega a `/dashboard/historiales` con `state.pacienteId` |
| 11 | `ModalPaciente` sin distrito/localidad/seguro/historia clínica | Formulario completo con dropdowns de catálogo encadenados |
| 12 | No había UI para atención ni para el PDF FUA | Formulario de atención + descarga FUA como blob autenticado |

---

## 6. Lo que ya tenemos (✅)

### Backend
- ✅ FastAPI con **34 endpoints** y Swagger en `/docs`.
- ✅ Autenticación JWT + bcrypt, roles `admin` / `usuario`.
- ✅ CRUD de pacientes con permisos (creador o admin).
- ✅ **Predicción ML** real (Random Forest entrenado).
- ✅ **Triaje clínico** determinista (nivel de alerta, semáforo, factores, recomendaciones).
- ✅ **Atenciones del consultorio** (diagnóstico/tratamiento/indicaciones) — nuevo.
- ✅ **PDF FUA** descargable por evaluación.
- ✅ Catálogos distritos/localidades + CRUD admin.
- ✅ Gestión de usuarios con guards anti-lockout.
- ✅ Migraciones `001_triaje_clinico.sql` y `002_atenciones.sql`.
- ✅ Tests pytest (SQLite en memoria) — incluye `test_atenciones.py`.
- ✅ Seed automático de datos de prueba.

### Frontend
- ✅ Login real y sesión JWT con 401 → relogin.
- ✅ 8 páginas funcionales conectadas a la API (sin datos mock).
- ✅ Servicios por recurso, manejo de errores de FastAPI (409/422/401).
- ✅ Tabla de pacientes con búsqueda, alta y edición.
- ✅ Triaje que crea evaluaciones reales y muestra el semáforo clínico.
- ✅ Consultorio con resultado del modelo, registro de atención y descarga FUA.
- ✅ Historia clínica por paciente y listado global de atenciones.
- ✅ Gestión de usuarios (crear/editar/activar/desactivar) solo para admin.
- ✅ Dashboard con métricas reales.
- ✅ `npm run lint` y `npm run build` sin errores.

---

## 7. Pendientes y mejoras futuras

### Limitaciones conocidas del MVP
- ⚠️ **Signos vitales no persistidos.** El modal de triaje captura temperatura, frecuencia
  cardíaca, saturación, IMC, frutas/verduras/alcohol y días de mala salud, pero el backend solo
  guarda las **9 variables del modelo** (más `presion_alta`, derivada de la lectura de presión).
  El resto se usa para el cálculo en pantalla y se descarta. Persistirlos requiere una tabla
  nueva de evolución clínica.
- ⚠️ **Sin `DELETE`.** No hay borrado duro en ninguna entidad (solo soft delete en usuarios,
  distritos y localidades). Pacientes, evaluaciones y atenciones no se pueden eliminar.
- ⚠️ **Evaluaciones inmutables.** No existe endpoint de edición de evaluaciones (cada una es una
  instantánea clínica).
- ⚠️ **Sin refresh token.** El JWT dura 60 minutos; al expirar el frontend redirige al login.
- ⚠️ **`GET /pacientes/` sin paginación.** El frontend carga la lista completa y filtra en
  cliente (adecuado para decenas de pacientes, no para miles).
- ⚠️ **Sin endpoint de conteo.** El dashboard pide `limit=200` para calcular las métricas.

### Trabajo futuro sugerido
- [ ] UI de administración de catálogos (distritos/localidades) — la API ya existe.
- [ ] Paginación/búsqueda server-side en pacientes para volúmenes grandes.
- [ ] Endpoint de estadísticas agregadas para el dashboard (contadores por clasificación).
- [ ] Persistir signos vitales y construir una línea de tiempo clínica del paciente.
- [ ] Refresh token o renovación silenciosa de sesión.
- [ ] Notificaciones reales en la Topbar (hoy es un placeholder).

---

## 8. Cómo levantar y verificar

```bash
# 1) Backend (raíz del repo) → http://localhost:8000/docs
uvicorn main:app --reload --port 8000

# 2) Frontend (otra terminal) → http://localhost:5173
cd frontend && npm install && npm run dev
```

| Rol | Email | Password |
|-----|-------|----------|
| Admin | `admin@healthcure.com` | `admin123` |
| Personal de salud | `dr.garcia@healthcure.com` | `doctor123` |
| Personal de salud | `ana.martinez@healthcure.com` | `enfermera123` |

```bash
# Tests del backend (no necesitan MySQL)
python -m pytest app/tests -v

# Calidad del frontend
cd frontend && npm run lint && npm run build
```

### Probar el flujo completo (5 pasos, ~2 minutos)

El **triaje es donde vive el modelo ML**. Ruta: sidebar → *Atención clínica* → **Triaje**
(paso 2) → `/dashboard/triaje`.

1. Entra con `dr.garcia@healthcure.com` / `doctor123`.
2. **Pacientes** (paso 1) → botón *Nuevo Paciente* → completa y guarda.
   (Si no quieres crear uno, usa cualquier paciente existente.)
3. **Triaje** (paso 2) → en la fila del paciente pulsa **Iniciar triaje** (o *Nueva evaluación*)
   → completa signos vitales, antecedentes, hábitos y percepción de salud →
   **Guardar y Calcular Riesgo**.
   → La vista hace *scroll* al bloque **Resultado del modelo ML**: probabilidad, clasificación,
   semáforo clínico, acción sugerida, factores de riesgo/protectores, recomendaciones y
   descarga del **FUA (PDF)**. Ese es el corazón del proyecto en acción.
4. **Consultorio** (paso 3) → elige al paciente en la columna izquierda → revisa el resultado
   del modelo → escribe diagnóstico y tratamiento → **Registrar Atención**.
5. **Historias Clínicas** → busca por documento → verás el expediente completo: todas las
   evaluaciones con su semáforo + FUA y todas las atenciones.

> Consejo para demos: en Triaje usa el filtro **Pendientes de triaje (n)** para ver solo los
> pacientes que todavía no tienen evaluación, y así mostrar el proceso desde cero.

---

## 9. Anexo: contratos de datos

### 9.1 Login — `POST /api/v1/auth/login`

```json
// Request
{ "email": "dr.garcia@healthcure.com", "password": "doctor123" }

// Response 200
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "usuario": { "id": 2, "nombre": "Dr. Carlos García", "email": "...", "rol": "usuario", "activo": true, "created_at": "..." }
}
```

### 9.2 Crear paciente — `POST /api/v1/pacientes/`

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
  "localidad_id": 3,
  "tipo_seguro": "SIS",
  "codigo_afiliacion_seguro": "040-2-1032456789",
  "talla_cm": 172.5,
  "peso_kg": 85.3
}
```

### 9.3 Crear evaluación (ML) — `POST /api/v1/evaluaciones/`

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

> **Solo 9 variables predictoras** (+ `paciente_id`).

### 9.4 Response 201 (incluye triaje clínico)

```json
{
  "id": 8,
  "paciente_id": 1,
  "usuario_id": 2,
  "edad": 55,
  "probabilidad": 0.459186,
  "clasificacion": "moderado",
  "modelo_version": "2.0.0",
  "triaje_clinico": {
    "nivel_alerta": "RIESGO MODERADO - SEGUIMIENTO PREVENTIVO",
    "codigo_color": "amarillo",
    "accion_sugerida": "Programar consulta médica de control en los próximos 15 a 30 días.",
    "factores_riesgo_detectados": ["Hipertensión Arterial", "Diabetes Mellitus"],
    "factores_protectores": ["Realiza Actividad Física Regular", "No Fumador"],
    "recomendaciones_medicas": ["Solicitar perfil lipídico...", "..."]
  },
  "created_at": "2026-09-05T08:30:13"
}
```

### 9.5 Crear atención — `POST /api/v1/atenciones/`

```json
// Request
{
  "paciente_id": 1,
  "evaluacion_id": 8,
  "diagnostico": "HTA en control, riesgo cardiovascular moderado.",
  "tratamiento": "Losartán 50mg cada 12h por 30 días.",
  "indicaciones": "Dieta hiposódica y control en 15 días."
}

// Response 201
{
  "id": 1,
  "paciente_id": 1,
  "paciente_nombre": "Pérez Rodríguez, Juan",
  "evaluacion_id": 8,
  "usuario_id": 2,
  "diagnostico": "HTA en control, riesgo cardiovascular moderado.",
  "tratamiento": "Losartán 50mg cada 12h por 30 días.",
  "indicaciones": "Dieta hiposódica y control en 15 días.",
  "created_at": "2026-10-06T10:30:00",
  "updated_at": "2026-10-06T10:30:00"
}
```

### 9.6 Clasificación de riesgo

| Probabilidad | `clasificacion` | Semáforo |
|--------------|-----------------|----------|
| < 0.30 | `bajo` | 🟢 verde |
| 0.30 – 0.60 | `moderado` | 🟡 amarillo |
| > 0.60 | `alto` | 🔴 rojo |
