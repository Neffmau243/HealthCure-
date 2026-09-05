# HealthCure — CardioPredict: Triaje Clínico

> Documento de referencia: cómo el backend traduce la probabilidad del ML en
> información clínica estructurada para médicos y enfermeros.
> Generado a partir del código fuente actual del proyecto.

---

## Tabla de Contenidos

1. [¿Qué es el triaje clínico?](#1-qué-es-el-triaje-clínico)
2. [¿Por qué existe?](#2-por-qué-existe)
3. [Arquitectura: ¿quién hace qué?](#3-arquitectura-quién-hace-qué)
4. [Flujo completo paso a paso](#4-flujo-completo-paso-a-paso)
5. [¿Qué parte pone el texto? (corazón del sistema)](#5-qué-parte-pone-el-texto-corazón-del-sistema)
6. [Las reglas clínicas en detalle](#6-las-reglas-clínicas-en-detalle)
7. [Persistencia en MySQL](#7-persistencia-en-mysql)
8. [Compatibilidad con evaluaciones antiguas](#8-compatibilidad-con-evaluaciones-antiguas)
9. [Ejemplo real (request → response)](#9-ejemplo-real-request--response)
10. [Tests](#10-tests)
11. [Cómo modificar / extender el triaje](#11-cómo-modificar--extender-el-triaje)

---

## 1. ¿Qué es el triaje clínico?

Es un objeto JSON anidado dentro de la respuesta de cada evaluación cardíaca
(`triaje_clinico`) que traduce el número frío del modelo ML (ej: `0.459186`)
en **instrucciones accionables** para el personal de salud.

```json
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
}
```

---

## 2. ¿Por qué existe

Un médico o enfermero **no lee** `0.459` o `"moderado"` y sabe qué hacer.
Necesita, de un vistazo:

| Necesidad del personal | Campo que la cubre |
|------------------------|--------------------|
| Qué tan rápido actuar | `nivel_alerta` |
| Semáforo visual | `codigo_color` (verde / amarillo / rojo) |
| Por qué dio ese riesgo | `factores_riesgo_detectados` |
| Qué se está haciendo bien | `factores_protectores` |
| Próximos pasos clínicos | `accion_sugerida` + `recomendaciones_medicas` |

---

## 3. Arquitectura: ¿quién hace qué?

```
┌─────────────────────────────────────────────────────────────────┐
│  API Route  app/api/v1/evaluaciones.py                           │
│  Recibe el request → llama al service → retorna response         │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  SERVICE  app/services/evaluacion_service.py                     │
│  Orquesta: valida paciente → ML → mapper → repository            │
└───────────────┬───────────────────────────────┬─────────────────┘
                │                               │
                ▼                               ▼
┌───────────────────────────────┐  ┌─────────────────────────────────┐
│  ML  app/ml/predictor.py      │  │  MAPPER  app/mappers/evaluacion_ │
│  predict_proba → probabilidad │  │  mapper.py                       │
│  _classify → clasificacion    │  │  create_to_model() y to_response │
└───────────────────────────────┘  └───────────────┬─────────────────┘
                                                   │ llama
                                                   ▼
                                ┌─────────────────────────────────────┐
                                │  TRIAGE SERVICE  app/services/       │
                                │  evaluacion_triaje_service.py         │
                                │  generar_triaje_clinico()             │
                                │  ★ EL QUE ESCRIBE EL TEXTO ★          │
                                └─────────────────────────────────────┘
```

**Punto clave:** el modelo ML **NO** genera el texto del triaje. Solo produce
`probabilidad` y `clasificacion`. Las reglas clínicas viven en
`evaluacion_triaje_service.py` y son **100% deterministas** (mismos inputs →
mismo triaje), lo que las hace fáciles de testear y auditar.

---

## 4. Flujo completo paso a paso

Tomando como ejemplo el `POST /api/v1/evaluaciones/` con `probabilidad 0.459186`:

| # | Paso | Archivo | Qué pasa |
|---|------|---------|----------|
| 1 | Validar paciente | `evaluacion_service.py` → `evaluate()` | Busca al paciente; 400 si no existe |
| 2 | Request → input ML | `evaluacion_mapper.py` → `request_to_model_input()` | Convierte bools a ints (True → 1, False → 0) |
| 3 | Predecir | `ml/predictor.py` → `predict()` | `predict_proba(df)[0][1]` = `0.459186`, `_classify` = `"moderado"` |
| 4 | Generar triaje | `evaluacion_mapper.py` → `create_to_model()` llama a `generar_triaje_clinico()` | Construye los 6 campos clínicos (ver sección 5) |
| 5 | Guardar | `evaluacion_repository.py` → `create()` | INSERT con las 6 columnas de triaje |
| 6 | Construir respuesta | `evaluacion_mapper.py` → `to_response()` | Arma el objeto `TriajeClinico` (o lo recalcula si falta) |
| 7 | Retornar | `evaluaciones.py` | 201 + JSON completo |

---

## 5. ¿Qué parte pone el texto? (corazón del sistema)

El texto clínico se genera en **dos momentos**, ambos en `evaluacion_mapper.py`:

### 5.1 Al guardar: `create_to_model()`

Este método combina request + predicción + **triaje** en el dict que se guarda
en MySQL. Aquí se llama a `generar_triaje_clinico()`:

```python
triaje = generar_triaje_clinico(
    data={
        "presion_alta":            data.presion_alta,
        "colesterol_alto":         data.colesterol_alto,
        "tabaquismo":              data.tabaquismo,
        "actividad_fisica":        data.actividad_fisica,
        "antecedente_acv":         data.antecedente_acv,
        "diabetes":                data.diabetes,
        "salud_general":           data.salud_general,
        "dificultad_para_caminar": data.dificultad_para_caminar,
    },
    probabilidad=prediction.probabilidad,
    clasificacion=prediction.clasificacion,
)
```

Y el dict resultante incluye las 6 claves del triaje para persistirlas.

### 5.2 Al responder: `to_response()` → `_triaje_clinico()`

Construye el objeto `TriajeClinico` que ve el frontend:

- Si la evaluación **tiene triaje persistido** (columnas llenas) → se usa tal
  cual (fuente de verdad = BD).
- Si es una evaluación **antigua** (columnas NULL) → se **recalcula on-the-fly**
  con `generar_triaje_clinico()` usando los predictores guardados. Así las
  evaluaciones históricas también devuelven interpretación clínica.

### 5.3 El servicio que escribe: `evaluacion_triaje_service.py`

`generar_triaje_clinico(data, probabilidad, clasificacion)` orquesta 3 helpers:

1. `_normalizar_clasificacion()` → acepta `"bajo"` como str o `ClasificacionEnum`.
2. `_nivel_de_alerta(clasificacion)` → **el texto fijo** (tablas de la sección 6).
3. `_factores_de_riesgo(data)` / `_factores_protectores(data)` → listas dinámicas
   según los bools del paciente.

Además tiene un **respaldo**: si la clasificación llega con un valor inesperado,
la deriva de la probabilidad con los mismos umbrales del predictor ML
(`< 0.30` bajo, `< 0.60` moderado, resto alto).

---

## 6. Las reglas clínicas en detalle

### 6.1 Textos por nivel de riesgo (`_nivel_de_alerta`)

| Clasificación | `nivel_alerta` | `codigo_color` | `accion_sugerida` |
|---------------|----------------|----------------|-------------------|
| **alto** | ALTA PRIORIDAD - RIESGO ELEVADO | `rojo` | Priorizar atención médica. Evaluación por Cardiología requerida. |
| **moderado** | RIESGO MODERADO - SEGUIMIENTO PREVENTIVO | `amarillo` | Programar consulta médica de control en los próximos 15 a 30 días. |
| **bajo** | BAJO RIESGO - CONTROL DE RUTINA | `verde` | Mantener controles anuales de salud preventiva. |

> **Nota de diseño:** `codigo_color` es **semántico** ("verde"/"amarillo"/"rojo"),
> no un hex. El spec pidió explícitamente "cadenas listas para consumir sin
> estilos visuales" — el renderizado (tarjetas, badges) lo hace el frontend.

### 6.2 `recomendaciones_medicas` por nivel

| Nivel | Recomendaciones |
|-------|-----------------|
| **alto** | 1. Realizar Electrocardiograma (ECG) de base de inmediato.<br>2. Solicitar perfil lipídico completo, HbA1c y función renal (Creatinina/Urea).<br>3. Evaluar inicio o ajuste de tratamiento antihipertensivo/hipolipemiante. |
| **moderado** | 1. Solicitar perfil lipídico y examen de glucosa en ayunas.<br>2. Monitoreo ambulatorio de presión arterial durante 1 semana.<br>3. Reforzar cambios en el estilo de vida (dieta cardioprotectora). |
| **bajo** | 1. Continuar promoviendo la actividad física y hábitos saludables.<br>2. Reevaluación de triaje anual o según síntomas. |

### 6.3 Factores de riesgo (`_factores_de_riesgo`)

Se incluyen **solo los que están en `True`**:

| Input del paciente | Texto que aparece |
|--------------------|-------------------|
| `presion_alta` = true | Hipertensión Arterial |
| `colesterol_alto` = true | Dislipidemia (Colesterol Alto) |
| `diabetes` = true | Diabetes Mellitus |
| `tabaquismo` = true | Consumo de Tabaco Activo |
| `antecedente_acv` = true | Antecedente de Accidente Cerebrovascular (ACV) |
| `dificultad_para_caminar` = true | Dificultad para Caminar (Movilidad Reducida) |
| `salud_general` ≥ 4 | Percepción de Salud General Regular o Mala |

### 6.4 Factores protectores (`_factores_protectores`)

| Condición | Texto que aparece |
|-----------|-------------------|
| `actividad_fisica` = true | Realiza Actividad Física Regular |
| `tabaquismo` = false | No Fumador |

> Ojo: si `tabaquismo` = true, NO aparece "No Fumador" (aparece el factor de
> riesgo "Consumo de Tabaco Activo" en su lugar).

---

## 7. Persistencia en MySQL

### 7.1 Columnas nuevas en `evaluaciones`

| Columna | Tipo MySQL | Contenido |
|---------|------------|-----------|
| `nivel_alerta` | `VARCHAR(100)` NULL | Texto del nivel |
| `codigo_color` | `VARCHAR(20)` NULL | `verde` / `amarillo` / `rojo` |
| `accion_sugerida` | `TEXT` NULL | Protocolo de triaje |
| `factores_riesgo_detectados` | `JSON` NULL | Lista de strings |
| `factores_protectores` | `JSON` NULL | Lista de strings |
| `recomendaciones_medicas` | `JSON` NULL | Lista de strings |

Todas son NULL-able a propósito: no rompen filas existentes y permiten el
fallback de recálculo de la sección 8.

### 7.2 Migración

- **BD nueva:** el `schema.sql` actualizado ya incluye las columnas.
- **BD existente:** aplicar una vez `app/resources/migrations/001_triaje_clinico.sql`:

```bash
mysql -u tu_usuario -p healthcure_db < app/resources/migrations/001_triaje_clinico.sql
```

### 7.3 Modelo SQLAlchemy

```python
nivel_alerta = Column(String(100), nullable=True)
codigo_color = Column(String(20), nullable=True)
accion_sugerida = Column(Text, nullable=True)
factores_riesgo_detectados = Column(JSON, nullable=True)
factores_protectores = Column(JSON, nullable=True)
recomendaciones_medicas = Column(JSON, nullable=True)
```

---

## 8. Compatibilidad con evaluaciones antiguas

Las evaluaciones creadas **antes** de esta feature tienen las columnas en NULL.
El mapper lo resuelve en `_triaje_clinico()`:

```
evaluacion.nivel_alerta is not None?
    ├── SÍ → usar triaje persistido (tal cual salió de la BD)
    └── NO → recalcular con generar_triaje_clinico()
              (usando los predictores guardados + probabilidad + clasificación)
```

Resultado: **todas** las evaluaciones (viejas y nuevas) devuelven
`triaje_clinico` en la API. La BD no necesita backfill.

---

## 9. Ejemplo real (request → response)

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

**Lectura clínica de este ejemplo:** riesgo moderado (45.9%) → semáforo amarillo,
seguimiento preventivo en 15–30 días. Factores que lo disparan: hipertensión +
dislipidemia + diabetes. A favor: hace actividad física y no fuma.

---

## 10. Tests

Cobertura en `app/tests/`:

| Archivo | Qué cubre |
|---------|-----------|
| `test_evaluacion_triaje.py` | Reglas puras: nivel/color por clasificación, factores de riesgo/protectores, fallback por probabilidad, aceptación de Enum |
| `test_evaluacion_mapper.py` | `create_to_model` incluye triaje; `to_response` usa persistido o recalcula; decimales y enums |

Correr:

```bash
python -m pytest app/tests -v
```

---

## 11. Cómo modificar / extender el triaje

Todo el texto vive en **un solo archivo**: `app/services/evaluacion_triaje_service.py`.

- **Cambiar un texto** (ej: otra redacción de recomendación) → editar
  `_nivel_de_alerta()`.
- **Cambiar umbrales de color** → editar el fallback de `generar_triaje_clinico()`
  (y en paralelo `_classify()` de `ml/predictor.py` si se quiere coherencia total).
- **Agregar un factor de riesgo nuevo** → añadir un `if` en `_factores_de_riesgo()`
  con el nombre clínico del factor.
- **Agregar un campo nuevo al triaje** → añadir columna (modelo + migración),
  campo en `TriajeClinico` (schema), y la clave en el dict del servicio.

> ⚠️ Los textos son clínicos: cualquier cambio debería validarse con personal
> de salud antes de producción.