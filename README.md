# HealthCure — CardioPredict


Prototipo académico que clasifica perfiles asociados con **antecedentes declarados de enfermedad coronaria o infarto** e integra gestión de pacientes, evaluaciones, atenciones y reglas experimentales de priorización.

> El XGBoost incluido entrega un **score con calibración interna (v3.0.0)**, mostrado como índice del modelo de **0 a 100**. No es probabilidad clínica, diagnóstico ni predicción de eventos futuros. Las bandas y orientaciones no están validadas clínicamente y no determinan urgencias ni tratamiento.

```text
Paciente adulto → Nueve respuestas → XGBoost → Índice + banda experimental
 → Orientación para revisión humana → Historial y PDF académico
```

La referencia vigente del experimento es [MODELO_ML](docs/MODELO_ML.md) y sus usos y límites están en [MODEL_CARD](docs/MODEL_CARD.md). La [segunda etapa experimental](docs/SEGUNDA_ETAPA_EXPERIMENTAL.md) ya fue ejecutada: el candidato calibrado se integró como v3.0.0 con [bandas versionadas, estabilidad y evaluación externa](docs/INTEGRACION_V3_Y_GENERALIZACION.md). Los relatos anteriores se conservan en `docs/historico/`.

---

## 🚀 Levantar el proyecto (1 comando, 1 puerto)

**1) Todo en un solo puerto — desde la raíz del repo:**

```bash
python -m uvicorn main:app --reload --port 8000
```

→ **App en <http://localhost:8000>** · API en `/api/v1` · Swagger en <http://localhost:8000/docs>

El backend sirve la interfaz React ya compilada (`frontend/dist`) desde el mismo
puerto: no hay que levantar un segundo servidor. Si cambias algo del frontend,
reconstruye:

```bash
cd frontend && npm install && npm run build
```

> **Nota Windows:** usa siempre `python -m uvicorn` y no el comando `uvicorn`:
> el `uvicorn.exe` que instala pip puede quedar bloqueado por el Control
> inteligente de aplicaciones (Smart App Control) con el error
> _«Una directiva de Control de aplicaciones bloqueó este archivo»_.

**2) Opcional — modo desarrollo del frontend (recarga instantánea), en otra terminal:**

```bash
cd frontend && npm run dev
```

→ App en <http://localhost:5173>. Es el mismo frontend sin compilar: las llamadas a
`/api/*` se redirigen al backend del 8000 (proxy de Vite). Úsalo solo si estás
tocando el frontend y quieres ver los cambios al instante.

> **Requisito:** crea la base de datos `healthcure_db` en MySQL y pon tus credenciales en `.env` antes del primer arranque (ver [Instalación](#-instalación)). El backend siembra solo los datos y usuarios de prueba la primera vez que se levanta.

---

## 🔑 Credenciales de prueba (seed automático)

Al levantar el backend con la BD vacía se crean estas cuentas:

| Rol | Email | Password |
|-----|-------|----------|
| Admin | `admin@healthcure.com` | `admin123` |
| Médico | `dr.garcia@healthcure.com` | `doctor123` |
| Enfermera | `ana.martinez@healthcure.com` | `enfermera123` |

> El frontend **ya está integrado con la API**: el login llama a `POST /api/v1/auth/login` y
> guarda el JWT. Estas son las cuentas con las que puedes entrar. El backend debe estar
> corriendo en `http://localhost:8000` (el frontend apunta ahí por defecto y se puede cambiar
> con `VITE_API_URL`). Detalle de la integración en
> [`docs/MAPEO_RUTAS_FRONT_BACK.md`](docs/MAPEO_RUTAS_FRONT_BACK.md).

---

## ✨ Qué hay ahora mismo

| Feature | Estado |
|---------|--------|
| Clasificación ML (índice + banda experimental) | ✅ Funcionando |
| **Reglas experimentales de priorización** | ✅ **Implementado** |
| Endpoints REST (FastAPI + Swagger) | ✅ Funcionando |
| Autenticación JWT + roles (admin/usuario) | ✅ Funcionando |
| Gestión de pacientes | ✅ Funcionando |
| Atenciones del consultorio (diagnóstico/tratamiento) | ✅ Implementado |
| Catálogos (distritos/localidades) | ✅ Funcionando |
| Admin (gestión de usuarios + catálogos) | ✅ Funcionando |
| **Frontend React integrado con la API** | ✅ **Funcionando** |
| Tests (pytest, SQLite en memoria) | ✅ Cubiertos |
| Figuras de evaluación del modelo (`scripts/generar_figuras.py`) | ✅ Incluidas |
| Ficha del modelo / Model Card | ✅ Incluida |
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
| ML | XGBoost (comparado con Random Forest) — scikit-learn |
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

**Opción recomendada** — el entorno exacto ya verificado (incluye las
dependencias indirectas):

```bash
pip install -r requirements-lock.txt
```

**Opción por partes** — si prefieres ver solo las dependencias directas:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt   # pytest + httpx + matplotlib (figuras del modelo)
```

> En esta opción las dependencias indirectas (numpy, scipy, starlette…) las
> elige pip, así que pueden quedar versiones más nuevas que las probadas.
> Si estás en Windows con Smart App Control, usa el lock.

Las versiones están **fijadas** (`==`), no con rangos: así cualquier máquina
instala exactamente lo que corren los tests (ver la cabecera de
`requirements.txt`). El lock (`requirements-lock.txt`) añade todas las
dependencias indirectas con su versión exacta; se regenera con
`pip freeze > requirements-lock.txt`.

> **⚠️ Windows — Control inteligente de aplicaciones (Smart App Control)**
>
> Si al instalar o al arrancar ves el error _«Una directiva de Control de
> aplicaciones bloqueó este archivo»_, no es un problema del proyecto: Windows
> está bloqueando un binario recién descargado que aún no tiene reputación.
> Suele pasar con `uvicorn.exe` y con las DLL compiladas de paquetes muy nuevos
> (SQLAlchemy 2.1, pandas, scikit-learn, xgboost).
>
> Soluciones, de menor a mayor:
>
> 1. Usa `python -m uvicorn` en vez del comando `uvicorn` (ver
>    [Levantar el proyecto](#-levantar-el-proyecto-1-comando-1-puerto)).
> 2. Si falla el `import` de un paquete, crea el entorno virtual reutilizando
>    los que ya tienes instalados y permitidos:
>    ```bash
>    python -m venv venv --system-site-packages
>    ```
> 3. Desactivar Smart App Control en **Seguridad de Windows → Control de
>    aplicaciones y navegador**. Ojo: es **irreversible** sin reinstalar Windows
>    y no admite exclusiones, así que agota las opciones 1 y 2 primero.

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

> **Si tu BD ya existe** (creada con schema.sql anterior), aplica las migraciones:
> ```bash
> mysql -u root -p healthcure_db < app/resources/migrations/001_triaje_clinico.sql
> mysql -u root -p healthcure_db < app/resources/migrations/002_atenciones.sql
> python scripts/aplicar_migracion_003.py
python scripts/aplicar_migracion_004.py
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

### 6. Compilar el frontend (una sola vez)

```bash
cd frontend && npm install && npm run build && cd ..
```

Genera `frontend/dist`, que el backend sirve en el mismo puerto. Repítelo cada
vez que cambies algo del frontend.

### 7. Levantar el servidor

```bash
python -m uvicorn main:app --reload --port 8000
```

### 8. Verificar

- **http://localhost:8000** → interfaz del sistema (login)
- **http://localhost:8000/docs** → Swagger UI con todos los endpoints

### 9. Correr los tests

```bash
python -m pytest app/tests -v
```

Los tests usan **SQLite en memoria** — no necesitan MySQL levantado.

Validación del formulario y frontend:

```bash
cd frontend
npm test
npm run lint
npm run build
```

Los nueve predictores son obligatorios. Solo se admiten adultos de 18 a 120 años y la edad debe coincidir con nacimiento a la fecha de consulta (America/Lima). `presion_alta` es el diagnóstico previo, no una lectura aislada. La presión medida se guarda aparte. `estado_diabetes` conserva la respuesta original; el booleano `diabetes` agrupa prediabetes y diabetes solo para ML.

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
| GET | `/api/v1/evaluaciones/resumen` | Conteos exactos para el dashboard (total, hoy, por nivel y pacientes ya triados hoy) |

### Atenciones del Consultorio (requiere JWT)

Registra el acto médico: diagnóstico, tratamiento e indicaciones, con trazabilidad del
profesional que atendió y vínculo opcional a la evaluación que lo originó.

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/atenciones/` | Registrar atención (diagnóstico/tratamiento) |
| GET | `/api/v1/atenciones/` | Listar todas (paginado) |
| GET | `/api/v1/atenciones/by-paciente/{id}` | Historial de atenciones del paciente |
| GET | `/api/v1/atenciones/{id}` | Ver una atención |

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

## 🧪 Datos de Prueba (seed automático)

Al levantar el servidor con la BD vacía se crean, además de las [credenciales de prueba](#-credenciales-de-prueba-seed-automático):

5 distritos, 15 localidades, 5 pacientes de ejemplo y 3 evaluaciones de prueba.

---

## 📋 Ejemplo de evaluación académica

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
    "estado_diabetes": "prediabetes",
    "presion_sistolica": 120,
    "presion_diastolica": 80,
    "salud_general": 3,
    "dificultad_para_caminar": false
}
```

### Response (201 Created)

La respuesta incluye inputs, categoría original de diabetes, presión medida, score `probabilidad`, banda, versión, snapshot `politica_modelo` e interpretación experimental. Para ese perfil el predictor directo devuelve el resultado de v3.0.0 (ver [integración](docs/INTEGRACION_ML.md)). En la API la edad ilustrativa debe sustituirse por la edad real del paciente elegido; no se admite un perfil con edad diferente de su fecha de nacimiento.

Ver [request y errores del contrato vigente](docs/INTEGRACION_ML.md).

---

## 🎯 Bandas experimentales

| Score interno | Índice sobre 100 | Banda | Color |
|---|---|---|---|
| <0.051065 | <5.1065 | bajo | verde |
| 0.051065 a <0.210469 | 5.1065 a <21.0469 | moderado | amarillo |
| >=0.210469 | >=21.0469 | alto | rojo |

Los cortes proceden de metadata y se conservan como decisión experimental. Los antecedentes listados proceden de respuestas; no explican contribuciones individuales del modelo. El personal de salud determina cualquier decisión clínica.

Los textos históricos persistidos se conservan como fueron registrados. Las nuevas orientaciones son generales y no prescriben exámenes, plazos ni tratamientos. Ver [reglas vigentes](docs/TRIAGE_CLINICO.md).

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
    "estado_diabetes": "prediabetes",
    "presion_sistolica": 120,
    "presion_diastolica": 80,
    "salud_general": 3,
    "dificultad_para_caminar": false
}
```

---

## 📝 Notas de Desarrollo

- **Dependencias:** `requirements.txt` (producción) y `requirements-dev.txt` (tests). `bcrypt` está fijado a `4.0.1` por compatibilidad con passlib 1.7.4.
- **Dataset:** Heart Disease Health Indicators (CDC/BRFSS 2015, Kaggle)
- **Entrenamiento experimental:** `entrenar_modelo.py` — separa train/calibration/validation/test, elige umbrales en validation, calibra con datos separados y compara particiones por filas, perfiles y deduplicación. Incluye logística, baseline de prevalencia, intervalos y subgrupos. Guarda candidatos versionados en `experimentos_ml/` sin reemplazar automáticamente el modelo activo v3.0.0. Ver [segunda etapa y pendientes](docs/SEGUNDA_ETAPA_EXPERIMENTAL.md).
- **Figuras históricas v2 (archivada):** `python scripts/generar_figuras.py` — genera ROC, precision-recall, matriz de confusión, calibración, importancia de variables, barrido de umbral y distribución de riesgo en `docs/figuras/`. No reentrena: carga el `.joblib` y **verifica** que las métricas coincidan con la ficha técnica.
- **Modelo actual (v3.0.0):** XGBoost + sigmoid · test interno por perfiles: ROC AUC 0.8285 · AP 0.3513 · F1 0.4048 y recall 0.6435 al corte superior · Brier 0.0773 (detalle completo en [`docs/MODELO_ML.md`](docs/MODELO_ML.md))
- **Postman:** `postman/HealthCure_API.postman_collection.json` con todos los endpoints
- **Frontend:** vive en `frontend/`. El backend sirve su build (`frontend/dist`) en el mismo
  puerto 8000, así que para el uso normal solo hay que compilar: `cd frontend && npm run build`.
  Con `npm run dev` (puerto 5173) queda el modo desarrollo con recarga instantánea y las
  peticiones `/api/*` se redirigen al 8000. La URL del backend se puede forzar con
  `VITE_API_URL` (ver `frontend/.env.example`); por defecto es relativa (`/api/v1`).
- **BD nueva:** `schema.sql` ya incluye las columnas de triaje y la tabla `atenciones`
- **BD existente:** aplicar 001/002 si están pendientes y ejecutar `python scripts/aplicar_migracion_003.py` y `python scripts/aplicar_migracion_004.py` antes del arranque. El último script es repetible y no recalcula el historial

---

## 📚 Documentación Adicional

- **Modelo ML (entrada, entrenamiento, métricas y entregables):** [`docs/MODELO_ML.md`](docs/MODELO_ML.md) — arquitectura del pipeline, qué datos espera, cómo se entrenó/versiona y qué métricas entrega.
- **Ficha del modelo (Model Card):** [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md) — uso previsto y fuera de alcance, datos de entrenamiento, métricas con su interpretación experimental, calibración, evaluación por subgrupos, consideraciones éticas y limitaciones conocidas.
- **Triaje Clínico detallado:** [`docs/TRIAGE_CLINICO.md`](docs/TRIAGE_CLINICO.md) — Arquitectura, reglas clínicas, flujo completo, compatibilidad con evaluaciones antiguas y guía de extensión.
- **Mapeo rutas Frontend ↔ Backend:** [`docs/MAPEO_RUTAS_FRONT_BACK.md`](docs/MAPEO_RUTAS_FRONT_BACK.md) — Rutas de ambos lados, contraste, desalineaciones y lo que falta para integrar.

---

## 🎯 Proyecto Academico — HealthCure CardioPredict

Licencia: Proyecto académico
