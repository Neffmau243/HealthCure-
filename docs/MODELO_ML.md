# Modelo de Machine Learning — CardioPredict (HealthCure)

Documento de referencia del componente de ML: **cómo funciona**, **qué datos
espera**, **cómo se entrenó**, **qué datos/artefactos entrega** y **cómo se
verifica**. Toda la información está contrastada contra el código y contra la
ficha técnica real generada por el entrenamiento (v2.0.0).

> Entrada rápida: el modelo vive en `app/resources/modelo_cardiaco.joblib`
> y su ficha técnica en `app/resources/modelo_cardiaco_metadata.json`.
> Se consume con `POST /api/v1/evaluaciones/`.

---

## Índice

1. [Qué es y dónde vive](#1-qué-es-y-dónde-vive)
2. [Cómo funciona (arquitectura del pipeline)](#2-cómo-funciona-arquitectura-del-pipeline)
3. [Qué datos espera (entrada)](#3-qué-datos-espera-entrada)
4. [Cómo se entrenó](#4-cómo-se-entrenó)
5. [Umbrales de decisión y clasificación](#5-umbrales-de-decisión-y-clasificación)
6. [Qué debe entregar](#6-qué-debe-entregar)
7. [Métricas reales e interpretación](#7-métricas-reales-e-interpretación)
8. [Cómo reentrenar y versionar](#8-cómo-reentrenar-y-versionar)
9. [Cómo verificar que todo está OK](#9-cómo-verificar-que-todo-está-ok)
10. [Limitaciones y próximos pasos](#10-limitaciones-y-próximos-pasos)
11. [Glosario](#11-glosario)

---

## 1. Qué es y dónde vive

Es un modelo de **clasificación binaria supervisada**: dado un perfil clínico
de 9 variables, estima la probabilidad de que el paciente tenga o desarrolle
**enfermedad cardíaca** y la traduce a un nivel de riesgo para el triaje.

| Elemento | Ruta / valor |
|----------|--------------|
| Modelo serializado | `app/resources/modelo_cardiaco.joblib` |
| Ficha técnica (metadata) | `app/resources/modelo_cardiaco_metadata.json` |
| Algoritmo (v2.0.0) | XGBoost (`XGBClassifier`) |
| Versión | `2.0.0` |
| Dataset | Heart Disease Health Indicators — CDC/BRFSS 2015 |
| Se sirve en | `POST /api/v1/evaluaciones/` |

**Código de la capa ML** (`app/ml/`):

| Archivo | Responsabilidad |
|---------|-----------------|
| `preprocessor.py` | Valida, convierte (edad años→código CDC) y ordena las 9 features en un DataFrame. |
| `model_loader.py` | Carga el `.joblib` **una sola vez** (singleton en RAM). |
| `metadata.py` | Lee la ficha técnica: versión y umbrales. Sin hardcodeos. |
| `predictor.py` | Ejecuta `predict_proba`, clasifica el riesgo y devuelve `PredictionResult`. |

---

## 2. Cómo funciona (arquitectura del pipeline)

```
 POST /api/v1/evaluaciones/   (body JSON con paciente_id + 9 variables)
        │
        ▼
 app/services/evaluacion_service.py     ← orquesta (único que habla con BD y ML)
        │  1. Valida que el paciente exista
        │  2. EvaluacionMapper.request_to_model_input()  → bool → int (0/1)
        │  3. Import LAZY de app.ml.predictor  (si falta el .joblib, el resto de la API sigue viva)
        ▼
 app/ml/preprocessor.py::preprocess()
        │  • Verifica que estén las 9 variables
        │  • Valida rangos (edad 1-120 años, salud_general 1-5)
        │  • mapear_edad_cdc(edad en años) → código 1-13   ← punto crítico
        │  • Devuelve DataFrame con FEATURE_COLUMNS en el ORDEN exacto
        ▼
 app/ml/model_loader.py::load_model()   ← modelo cacheado en RAM (singleton)
        ▼
 app/ml/predictor.py::predict()
        │  • model.predict_proba(df)[0][1] → probabilidad de clase 1
        │  • _classify(probabilidad) → "bajo" | "moderado" | "alto"
        │  • modelo_version ← get_model_version() (de la ficha técnica)
        ▼
 PredictionResult(probabilidad, clasificacion, modelo_version)
        │
        ▼
 EvaluacionMapper.create_to_model()  →  genera el TRIAJE CLÍNICO (reglas de negocio)
        │
        ▼
 EvaluacionRepository.create()  →  INSERT en MySQL  →  EvaluacionResponse (201)
```

**Puntos de diseño que no se deben romper:**

- **Import lazy**: el modelo solo se importa dentro de `evaluate()`. Si el
  `.joblib` no existe, auth/pacientes/catálogos siguen funcionando y solo falla
  la predicción (con un `500` claro).
- **Orden de columnas**: `FEATURE_COLUMNS` (inferencia) debe coincidir con el
  orden usado en el entrenamiento. Si cambia, el modelo predice basura en
  silencio. Está protegido por tests.
- **Edad**: se entrena con el código CDC 1-13, no con años. Ver sección 3.
- **Triaje**: se calcula en el mapper (lógica de negocio), NO dentro del modelo.

---

## 3. Qué datos espera (entrada)

### 3.1 Las 9 variables predictoras

Todas provienen del cuestionario CDC/BRFSS. La API las recibe dentro del JSON
de evaluación, además de `paciente_id` (que **no** entra al modelo).

| # | Variable (API) | Tipo API | Valores | Variable CDC | Descripción |
|---|----------------|----------|---------|--------------|-------------|
| 1 | `edad` | int | 1-120 (años) | `Age` (1-13) | Edad del paciente. Se convierte a código CDC. |
| 2 | `presion_alta` | bool | true/false | `HighBP` | Diagnóstico de hipertensión. |
| 3 | `colesterol_alto` | bool | true/false | `HighChol` | Colesterol alto diagnosticado. |
| 4 | `tabaquismo` | bool | true/false | `Smoker` | Fumó ≥100 cigarrillos en su vida. |
| 5 | `actividad_fisica` | bool | true/false | `PhysActivity` | Actividad física en los últimos 30 días. |
| 6 | `antecedente_acv` | bool | true/false | `Stroke` | Antecedente de accidente cerebrovascular. |
| 7 | `diabetes` | bool | true/false | `Diabetes` | Diagnóstico de diabetes (BRFSS 0/1/2 → 0/1). |
| 8 | `salud_general` | int | 1-5 | `GenHlth` | 1=excelente, 2=muy buena, 3=buena, 4=regular, 5=mala. |
| 9 | `dificultad_para_caminar` | bool | true/false | `DiffWalk` | Dificultad para caminar o subir escaleras. |

En el entrenamiento los `bool` se usan como 0/1 y `GenHlth`/`Age` como enteros.

### 3.2 La trampa de la edad (crítico)

El dataset **no trae la edad en años**: la columna `Age` ya viene codificada en
13 rangos. La API recibe años reales, así que hay que convertir.

| Código | Rango | Código | Rango |
|--------|-------|--------|-------|
| 1 | 18-24 | 8 | 55-59 |
| 2 | 25-29 | 9 | 60-64 |
| 3 | 30-34 | 10 | 65-69 |
| 4 | 35-39 | 11 | 70-74 |
| 5 | 40-44 | 12 | 75-79 |
| 6 | 45-49 | 13 | 80+ |
| 7 | 50-54 | | |

- **Entrenamiento** (`entrenar_modelo.py`): usa `Age` **tal cual** (ya es 1-13).
- **Inferencia** (`app/ml/preprocessor.py`): `mapear_edad_cdc(55) → 8`.
- Ambas tablas deben ser idénticas. Si se manda `55` sin convertir, el modelo lo
  lee como "código 55" → predicción sin sentido. Protegido por
  `app/tests/test_preprocessor.py`.

### 3.3 Ejemplo de request

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

Respuesta **201** (v2.0.0 real para este perfil):

```json
{
    "probabilidad": 0.51315,
    "clasificacion": "moderado",
    "modelo_version": "2.0.0",
    "triaje_clinico": { "codigo_color": "amarillo", "...": "..." }
}
```

### 3.4 Errores de entrada esperados

| Caso | Respuesta |
|------|-----------|
| Falta una variable o `edad` fuera de 1-120 / `salud_general` fuera de 1-5 | `422` (Pydantic) |
| `paciente_id` inexistente | `400 "Paciente no encontrado"` |
| Falta el `.joblib` | `500 "Modelo ML no disponible"` |

---

## 4. Cómo se entrenó

Todo el entrenamiento está en un único script reproducible:
**`entrenar_modelo.py`** (raíz del proyecto).

### 4.1 Dataset

| Dato | Valor |
|------|-------|
| Nombre | Heart Disease Health Indicators (CDC/BRFSS 2015) |
| Fuente | Kaggle — `alexteboul/heart-disease-health-indicators-dataset` |
| Archivo | `heart_disease_health_indicators_BRFSS2015.csv` (~22 MB, **no se commitea**) |
| Filas | 253,680 |
| Features usadas | 9 (de las 22 disponibles) |
| Variable objetivo | `HeartDiseaseorAttack` (0=no, 1=sí) |
| Clase positiva | 23,893 → **9.42%** (dataset desbalanceado) |

> El `.gitignore` excluye el CSV (`heart_disease_health_indicators*.csv`):
> se descarga aparte. El **modelo sí se commitea** para que la API funcione al
> clonar sin reentrenar.

### 4.2 Pasos del pipeline de entrenamiento

1. **Carga y preparación** — se seleccionan las 10 columnas necesarias (9 +
   target), se renombran a los nombres que usa la API y `Diabetes` se binariza
   (`>0 → 1`) para que el modelo nunca vea valores que la API no manda.
2. **Split estratificado** — 80% train (202,944) / 20% test (50,736), `random_state=42`.
   Estratificado para conservar el 9.4% de positivos en ambos conjuntos.
3. **Búsqueda de hiperparámetros** — `RandomizedSearchCV` con validación cruzada
   **estratificada de 3 folds**, **8 candidatos por familia**, scoring doble
   (`roc_auc` y `average_precision` = PR AUC).
4. **Comparación de familias** — Random Forest vs XGBoost. Gana la de mayor
   **ROC AUC de CV**.
5. **Reajuste** — el ganador se reentrena con **todo** el train.
6. **Optimización del umbral** — sobre la curva precision-recall del test se
   elige el umbral binario que maximiza F1.
7. **Persistencia** — se guarda el modelo `.joblib` y la ficha técnica JSON.

### 4.3 Resultado de la comparación

| Familia | CV ROC AUC | CV PR AUC | Mejores hiperparámetros |
|---------|-----------|-----------|-------------------------|
| Random Forest | 0.8373 | 0.3544 | `n_estimators=200, max_depth=8, min_samples_leaf=5, class_weight="balanced"` |
| **XGBoost** ✅ | **0.8391** | **0.3583** | `n_estimators=400, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8` |

**Ganador: XGBoost** (por ROC AUC de CV; la diferencia con RF es pequeña, ambos
son válidos y por eso se documenta la comparación).

### 4.4 La restricción de ponderación (importante)

Ambos estimadores se entrenan con **ponderación de la clase positiva**
(`class_weight="balanced"` en RF, `scale_pos_weight = neg/pos ≈ 9.62` en XGBoost).

¿Por qué? Porque la API aplica **umbrales clínicos fijos** (0.30 / 0.60) sobre
la salida del modelo. Con una prevalencia del 9.4%, un modelo **sin** ponderar
concentra las probabilidades muy por debajo de 0.30 y **el triaje colapsa a una
sola banda** (todos "bajo", incluidos enfermos evidentes). La ponderación
mantiene una **escala de riesgo** en la que 0.30 y 0.60 separan las 3 bandas.
El script además valida esto con la `distribucion_triaje_test`.

### 4.5 Reproducibilidad

| Fuente | Valor |
|--------|-------|
| Semilla | `random_state=42` (split, búsqueda y modelos) |
| Librerías | scikit-learn 1.9.0 · xgboost 3.4.1 · pandas 3.0.5 · joblib 1.5.3 |
| Fecha de entrenamiento | Guardada en `entrenado_en` de la ficha técnica |

---

## 5. Umbrales de decisión y clasificación

Aquí conviven **dos tipos de umbral** que no hay que confundir:

### 5.1 Bandas clínicas (regla de negocio, 3 niveles)

Definen el color del triaje. Se leen de la ficha técnica
(`umbrales_clasificacion_clinica`), con fallback a 0.30/0.60.

| Probabilidad | Clasificación | Triaje |
|--------------|---------------|--------|
| `< 0.30` | bajo | 🟢 verde |
| `0.30 – 0.60` | moderado | 🟡 amarillo |
| `>= 0.60` | alto | 🔴 rojo |

### 5.2 Umbral binario óptimo (referencia técnica)

El entrenamiento también calcula el umbral que maximiza F1 para la decisión
**enfermo / no enfermo**:

| Métrica | Valor |
|---------|-------|
| Umbral óptimo F1 | **0.7026** |
| F1 en ese punto | 0.4101 |

Notar que **0.7026 > 0.60**: la banda clínica "alto" es más sensible que el
punto óptimo de F1. Es coherente: en screening se prefiere *no dejar pasar
enfermos* (recall alto) aunque baje la precisión.

---

## 6. Qué debe entregar

Un entrenamiento correcto **entrega dos artefactos** (y la API los usa ambos):

### 6.1 Checklist de entregables

| Entregable | Ruta | Obligatorio |
|------------|------|-------------|
| Modelo serializado | `app/resources/modelo_cardiaco.joblib` | Sí |
| Ficha técnica | `app/resources/modelo_cardiaco_metadata.json` | Sí |
| Métricas del modelo | `metricas_test_umbral_0.50` en la ficha | Sí |
| Versión del modelo | `model_version` en la ficha | Sí |
| Umbrales clínicos | `umbrales_clasificacion_clinica` en la ficha | Sí |

> Si falta el `.joblib` → `POST /evaluaciones/` responde `500`.
> Si falta la ficha → la API sigue funcionando con versión `1.0.0` y umbrales
> por defecto (diseño defensivo de `app/ml/metadata.py`).

### 6.2 Campos de la ficha técnica

| Campo | Qué entrega |
|-------|-------------|
| `model_version` | Versión del artefacto (la reporta la API). |
| `algoritmo` | Familia ganadora (`XGBoost` / `RandomForest`). |
| `entrenado_en` | Fecha UTC del entrenamiento. |
| `dataset` | Nombre, fuente, archivo, filas, features, positivos, train/test. |
| `features` | Orden exacto de las 9 features (debe ser `FEATURE_COLUMNS`). |
| `hiperparametros` | Configuración final del modelo. |
| `validacion_cruzada` | Método, scoring, folds y resultado **por familia** (la comparación). |
| `metricas_test_umbral_0.50` | Accuracy, precision, recall, F1, ROC AUC, PR AUC, matriz de confusión. |
| `metricas_test_umbral_optimo` | Lo mismo en el umbral óptimo de F1. |
| `umbral_decision` | Umbral por defecto (0.50) y óptimo de F1. |
| `umbrales_clasificacion_clinica` | Bandas 0.30 / 0.60. |
| `distribucion_triaje_test` | Reparto % de casos en bajo/moderado/alto (guardrail). |
| `restriccion_ponderacion` | Explica la ponderación y su motivo. |
| `librerias` | Versiones de scikit-learn, xgboost, pandas, joblib. |

---

## 7. Métricas reales e interpretación

Evaluadas sobre el 20% reservado (50,736 casos, 4,779 positivos reales).

### 7.1 Comparativa por umbral

| Métrica | Umbral 0.50 (default) | Umbral óptimo F1 (0.7026) |
|---------|----------------------|---------------------------|
| Accuracy | 0.7243 | 0.8488 |
| Precision | 0.2297 | 0.3242 |
| **Recall** | **0.8192** | 0.5581 |
| **F1** | 0.3588 | **0.4101** |
| ROC AUC | 0.8403 | 0.8403 |
| PR AUC | 0.3537 | 0.3537 |

Matriz de confusión (umbral 0.50):

```
                  Predijo NO   Predijo SÍ
Real NO (45,776)    32,831      13,126
Real SÍ  (4,779)       864       3,915
```

### 7.2 Distribución del triaje (guardrail de producto)

| Banda | Casos | % |
|-------|-------|---|
| bajo | 25,929 | 51.11% |
| moderado | 12,220 | 24.09% |
| alto | 12,587 | 24.81% |

Las tres bandas quedan pobladas → el semáforo del triaje informa de verdad.

### 7.3 Cómo leer esto (honestidad)

- **ROC AUC ≈ 0.84** es un resultado **bueno y realista** para predicción de
  enfermedad cardíaca con BRFSS (la literatura reporta ~0.80-0.84). No esperar 0.95.
- **F1 ≈ 0.36 en el umbral 0.50** es **esperable** con 9.4% de positivos y PR AUC
  ≈ 0.35. Un F1 alto exigiría un problema más separable.
- Se prioriza **recall (0.82)** en el umbral por defecto: en salud, dejar pasar un
  enfermo (falso negativo) es más costoso que una falsa alarma. Si se prioriza
  precisión, el umbral 0.7026 sube el F1 a 0.41 y baja el recall a 0.56.
- La probabilidad de salida es una **escala de riesgo ponderada**, no una
  probabilidad calibrada a la prevalencia real (ver limitaciones).

> ⚠️ **Nota histórica:** versiones anteriores de `README.md` e
> `INTEGRACION_ML.md` mencionaban "F1 ~0.60-0.65". Ese valor **era incorrecto**
> (se esperaba, nunca se midió). Las cifras de esta sección salen de la ficha
> técnica real y se reproducen con `python entrenar_modelo.py`.

---

## 8. Cómo reentrenar y versionar

```bash
# 1. Descarga el CSV y colócalo en la raíz del proyecto (no se commitea)
#    https://www.kaggle.com/datasets/alexteboul/heart-disease-health-indicators-dataset

# 2. (Opcional) Sube MODEL_VERSION en entrenar_modelo.py si cambias el modelo
#    MODEL_VERSION = "2.0.0"   →   "2.1.0"

# 3. Entrena (comparación + CV: ~2-3 minutos)
python entrenar_modelo.py
#    o con ruta explícita:
python entrenar_modelo.py heart_disease_health_indicators_BRFSS2015.csv

# 4. Reinicia uvicorn (o usa reload_model()/reload_metadata() si el server sigue vivo)
uvicorn main:app --reload --port 8000
```

**Versionado:** la versión **no está hardcodeada** en la API. `predictor.py` la
lee con `app/ml/metadata.py::get_model_version()` desde la ficha técnica. Al
reentrenar con otra `MODEL_VERSION`, las evaluaciones nuevas reportan la versión
nueva automáticamente.

---

## 9. Cómo verificar que todo está OK

### 9.1 Tests automáticos

```bash
python -m pytest app/tests -v
```

Debe dar **72 tests en verde**, de los cuales **17 son del modelo real**
(`app/tests/test_modelo_real.py`) y cubren:

- Existencia del `.joblib` y de la ficha técnica (versionado).
- Campos mínimos de la ficha y métricas sanas (`ROC AUC >= 0.70`).
- Guardia anti-dataset-sintético (`dataset.n_rows > 200_000`).
- `features` de la metadata == `FEATURE_COLUMNS` del preprocessor.
- El modelo tiene 9 features y `predict_proba`.
- Pipeline real `preprocess → predict()` end-to-end y determinista.
- Coherencia clínica: perfil de alto riesgo > perfil de bajo riesgo.
- `_classify` respeta los umbrales de la ficha.
- **E2E por HTTP** de `POST /api/v1/evaluaciones/` (TestClient → router →
  service → mapper → modelo real → repositorio SQLite): `201` + predicción
  real + persistencia (GET por id y por paciente), ordenamiento de riesgo,
  `401` sin token y `400` con paciente inexistente.

### 9.2 Smoke test manual

```python
from app.ml.predictor import predict
from app.ml.metadata import get_model_version

print(get_model_version())  # 2.0.0

casos = {
    "sano 30":    dict(edad=30, presion_alta=0, colesterol_alto=0, tabaquismo=0,
                       actividad_fisica=1, antecedente_acv=0, diabetes=0,
                       salud_general=1, dificultad_para_caminar=0),
    "riesgo 75":  dict(edad=75, presion_alta=1, colesterol_alto=1, tabaquismo=1,
                       actividad_fisica=0, antecedente_acv=1, diabetes=1,
                       salud_general=5, dificultad_para_caminar=1),
}
for nombre, datos in casos.items():
    r = predict(datos)
    print(nombre, r.probabilidad, r.clasificacion.value)
# sano 30   → ~0.021 → bajo
# riesgo 75 → ~0.962 → alto
```

---

## 10. Limitaciones y próximos pasos

**Limitaciones conocidas (honestas):**

1. **Probabilidad no calibrada.** La ponderación hace que la salida sea una
   *escala de riesgo*, no `P(enfermedad)` real. Mejora posible: envolver el
   modelo en `CalibratedClassifierCV` y recalibrar los umbrales clínicos.
2. **Desbalance y F1 moderado.** Con 9.4% de positivos, F1 ~0.36-0.41 es el techo
   realista del dataset. No se debe prometer más.
3. **Población distinta.** El dataset es de EE.UU. (BRFSS); la población objetivo
   es local. Puede haber *dataset shift*. No usar como diagnóstico definitivo.
4. **Umbrales clínicos fijos.** 0.30/0.60 son una decisión de producto; conviene
   validarlos con criterio médico.
5. **Reentrenamiento manual.** No hay pipeline programado ni monitoreo de drift.
6. **Versión manual.** `MODEL_VERSION` se sube a mano en el script.

**Próximos pasos sugeridos:**

- Calibración de probabilidades + recalibración de umbrales.
- Explicabilidad por paciente (SHAP) para justificar el riesgo.
- Análisis de equidad por subgrupos (sexo, edad, seguro).
- Pipeline automático de descarga/preparación y monitoreo de desempeño en producción.
- Validación con datos clínicos locales.

---

## 11. Glosario

| Término | Significado |
|---------|-------------|
| **ROC AUC** | Capacidad de ordenar positivos por encima de negativos. 0.5 = azar, 1.0 = perfecto. |
| **PR AUC** | Área bajo la curva precision-recall. Más informativa con clases desbalanceadas. |
| **Precision** | De los que marcó como enfermos, cuántos lo eran. |
| **Recall** | De los enfermos reales, cuántos detectó. |
| **F1** | Media armónica de precision y recall. |
| **Validación cruzada (CV)** | Entrenar/evaluar en K particiones para estimar desempeño sin sesgo de un solo split. |
| **Umbral de decisión** | Corte de probabilidad que separa "enfermo" de "no enfermo". |
| **Ponderación de clases** | Dar más peso a la clase minoritaria para que el modelo no la ignore. |
| **Ficha técnica** | JSON con versión, dataset, hiperparámetros y métricas del artefacto. |
| **Guardrail** | Verificación que evita un estado inválido (p. ej. banda de triaje vacía). |
