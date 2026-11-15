# Ficha del Modelo (Model Card) — Clasificador de riesgo cardíaco CardioPredict

Documento de transparencia del modelo de Machine Learning del sistema
**HealthCure / CardioPredict**. Sigue la estructura recomendada por
*Model Cards for Model Reporting* (Mitchell et al., 2019), adaptada al alcance
real de este proyecto.

> ⚠️ **Advertencia principal:** este modelo es una **herramienta de apoyo al
> triaje**. No es un dispositivo médico, no emite diagnóstico y **no ha sido
> validado clínicamente**. Toda decisión clínica es responsabilidad del personal
> de salud.

---

## Índice

1. [Detalles del modelo](#1-detalles-del-modelo)
2. [Uso previsto](#2-uso-previsto)
3. [Factores relevantes](#3-factores-relevantes)
4. [Datos de entrenamiento](#4-datos-de-entrenamiento)
5. [Métricas y desempeño](#5-métricas-y-desempeño)
6. [Evaluación por subgrupos](#6-evaluación-por-subgrupos)
7. [Consideraciones éticas y de equidad](#7-consideraciones-éticas-y-de-equidad)
8. [Limitaciones conocidas](#8-limitaciones-conocidas)
9. [Recomendaciones de uso responsable](#9-recomendaciones-de-uso-responsable)
10. [Mantenimiento y monitoreo](#10-mantenimiento-y-monitoreo)

---

## 1. Detalles del modelo

| Campo | Valor |
|---|---|
| **Nombre** | Clasificador de riesgo cardíaco CardioPredict |
| **Versión** | `2.0.0` |
| **Tipo de tarea** | Clasificación binaria supervisada (aprendizaje por lotes, no continuo) |
| **Algoritmo** | XGBoost (gradient boosting) — 400 árboles, `max_depth=3`, `learning_rate=0.05`, `subsample=0.8`, `colsample_bytree=0.8` |
| **Selección del algoritmo** | Elegido por CV estratificada frente a Random Forest: XGBoost 0.8391 vs RF 0.8373 (ROC AUC). Diferencia de 0.0018 → en la práctica son **equivalentes**; se eligió XGBoost por parsimonia de árboles (`max_depth=3`) |
| **Artefacto** | `app/resources/modelo_cardiaco.joblib` (467 KB) |
| **Ficha técnica** | `app/resources/modelo_cardiaco_metadata.json` |
| **Fecha de entrenamiento** | 2026-10-09 |
| **Ponderación de clases** | Sí — `scale_pos_weight=9.62` (ver §8.1) |
| **Umbrales clínicos** | 0.30 / 0.60 (regla de negocio del triaje) |
| **Umbral binario óptimo (F1)** | 0.7026 (referencia técnica, no usado en el triaje) |
| **Entorno de ejecución** | API REST FastAPI + scikit-learn 1.9.0 / XGBoost 3.4.1 / pandas 3.0.5 |
| **Estado** | Operativo en entorno de **desarrollo**. Sin validación clínica ni uso en producción real |
| **Mantenido por** | Equipo HealthCure / CardioPredict |
| **Licencia / uso** | Proyecto académico. Ver §7 y §9 |

---

## 2. Uso previsto

### 2.1 Uso primario

**Apoyar la priorización del triaje en el consultorio.** Dado un conjunto de 9
factores de riesgo declarados o medidos en la consulta, el modelo estima una
probabilidad y el sistema la traduce a un **nivel de riesgo** de tres bandas:

| Banda | Rango | Acción sugerida por el sistema |
|---|---|---|
| 🟢 bajo | `< 0.30` | Sin priorización especial |
| 🟡 moderado | `0.30 – 0.60` | Evaluación en el flujo normal |
| 🔴 alto | `≥ 0.60` | Priorizar la atención y revisar factores de riesgo |

**Usuarios previstos:** personal de salud (médico, enfermero) del consultorio.
No está diseñado para uso directo por el paciente.

**Valor esperado:** con la regla de triaje (`≥ 0.30` = derivar a revisión),
medido sobre el conjunto de test, se deja fuera de la banda baja solo al
**8.1% de los pacientes que realmente tienen enfermedad** y se prioriza al
**71.5%** de ellos en la banda `alto` (§5.3).

### 2.2 Fuera de alcance — NO usar para

- ❌ **Diagnosticar** enfermedad coronaria o descartarla.
- ❌ Decidir tratamiento, dosis, alta o derivación urgente.
- ❌ Sustituir el criterio clínico o cualquier prueba diagnóstica.
- ❌ Usarlo con **menores de 18 años** (el dataset de entrenamiento solo cubre
  adultos; BRFSS excluye a menores).
- ❌ Usarlo sin revisión humana ("automatización complaciente").
- ❌ Interpretar el valor como **probabilidad absoluta** de enfermedad
  (no está calibrado — §8.1).
- ❌ Uso con poblaciones fuera de la población de entrenamiento sin validación
  local previa (§4.4).

---

## 3. Factores relevantes

### 3.1 Variables de entrada (9)

Entrenado con: `edad`, `presion_alta`, `colesterol_alto`, `tabaquismo`,
`actividad_fisica`, `antecedente_acv`, `diabetes`, `salud_general`,
`dificultad_para_caminar`.

| Grupo | Detalle |
|---|---|
| Demográfico | `edad` |
| Condiciones declaradas | `presion_alta`, `colesterol_alto`, `diabetes`, `antecedente_acv` |
| Conducta | `tabaquismo`, `actividad_fisica` |
| Estado autopercibido | `salud_general` (escala 1-5), `dificultad_para_caminar` |

> **Trampa crítica de la edad:** el modelo espera el **código CDC 1-13**, no años
> reales. La conversión (`mapear_edad_cdc`) vive en `app/ml/preprocessor.py`;
> enviar años crudos produciría predicciones silenciosamente erróneas.
> Ver `docs/MODELO_ML.md` §3.2.

### 3.2 Variables ausentes (por qué importa)

El modelo **no** recibe: sexo, raza/etnia, nivel de ingreso, IMC, presión
arterial medida, colesterol medido, medicación, antecedentes familiares,
resultados de laboratorio ni ECG.

Consecuencia: el modelo no puede ajustar por sexo ni por nivel
socioeconómico, y **no es posible medir equidad por subgrupos con el contrato
actual** (§6). También explica el techo de desempeño: 9 variables
autodeclaradas no pueden superar ROC AUC ≈ 0.84 para este problema.

---

## 4. Datos de entrenamiento

### 4.1 Dataset

| Campo | Valor |
|---|---|
| Nombre | Heart Disease Health Indicators (CDC/BRFSS 2015) |
| Fuente | <https://www.kaggle.com/datasets/alexteboul/heart-disease-health-indicators-dataset> |
| Archivo | `heart_disease_health_indicators_BRFSS2015.csv` (no versionado en git por tamaño) |
| Filas | 253,680 |
| Variables usadas | 9 |
| Positivos (enfermos) | 23,893 (**9.42%**) |
| Partición | 80/20 estratificada: 202,944 train / 50,736 test |
| Semilla | `RANDOM_STATE = 42` (reproducible) |

### 4.2 Procedimiento

1. Carga y renombrado de columnas al contrato en español del backend.
2. Normalización de `diabetes` a 0/1 (BRFSS usa `2` para prediabetes/embarazo).
3. Split estratificado 80/20 (preserva el 9.42% de positivos en ambos lados).
4. `RandomizedSearchCV` con `StratifiedKFold(3)` y scoring doble
   (`roc_auc` + `average_precision`), 8 candidatos por familia, comparando
   Random Forest vs XGBoost.
5. Reajuste del ganador sobre todo el train.
6. Optimización del umbral de decisión para maximizar F1.
7. Serialización del modelo **y** de su ficha técnica (§1).

Reproducible con: `python entrenar_modelo.py`

### 4.3 Limitaciones de los datos

- **Autodeclarado.** BRFSS es una encuesta telefónica: las condiciones son
  reportadas por el encuestado, no verificadas clínicamente → hay
  subregistro y error de medición en las etiquetas.
- **Año y país.** Datos de EE.UU., 2015. La prevalencia y los patrones de
  riesgo no coinciden necesariamente con la población objetivo del sistema.
- **Sin menores de 18 años.**
- **DESBALANCE ESTRUCTURAL:** solo 9.42% de positivos, lo que limita las
  métricas alcanzables (ver §5 y §8.2).
- **Sesgo por ponderación:** al aplicar `scale_pos_weight`, las probabilidades
  dejan de ser calibradas a propósito (ver §8.1).

### 4.4 Riesgo de *dataset shift*

El sistema se usa con pacientes locales (catálogos de distritos del consultorio)
pero el modelo se entrenó con población estadounidense. Esto es un riesgo
**no medido**: mientras no se valide con datos locales, el desempeño real en
producción es desconocido.

---

## 5. Métricas y desempeño

Evaluado sobre el **20% reservado** (50,736 casos, 4,779 positivos reales).
Reproducible con `python scripts/generar_figuras.py`, que **verifica** que las
métricas coincidan con la ficha técnica del artefacto.

### 5.1 Comparativa por umbral

| Métrica | Umbral 0.50 (default) | Umbral óptimo F1 = 0.7026 |
|---|---|---|
| Accuracy | 0.7243 | 0.8488 |
| Precision | 0.2297 | 0.3242 |
| **Recall** | **0.8192** | 0.5581 |
| F1 | 0.3588 | **0.4101** |
| **ROC AUC** | **0.8403** | 0.8403 |
| **PR AUC** | **0.3537** | 0.3537 |

### 5.2 Matriz de confusión (umbral 0.50)

```
                  Predijo NO   Predijo SÍ
Real NO (45,957)    32,831      13,126   ← falsas alarmas
Real SÍ  (4,779)       864       3,915   ← 864 enfermos NO detectados
```

### 5.3 Desempeño de la regla de triaje real

El triaje deriva a revisión a todo caso `moderado` o `alto` (≥ 0.30):

| Métrica de la regla | Valor |
|---|---|
| Sensibilidad (recall) | **91.88%** |
| Especificidad | 55.58% |
| Precision (PPV) | 17.70% |
| Pacientes derivados a revisión | 48.9% (24,807 de 50,736) |
| Enfermos que caen en banda `bajo` (no priorizados) | **8.1%** (388) |

**PPV por banda — lo que ve el médico:**

| Banda | Pacientes | % | Enfermos en la banda | **PPV** | % de enfermos capturados |
|---|---|---|---|---|---|
| bajo | 25,929 | 51.1% | 388 | 1.5% | 8.1% |
| moderado | 12,220 | 24.1% | 972 | 8.0% | 20.3% |
| alto | 12,587 | 24.8% | 3,419 | **27.2%** | **71.5%** |

### 5.4 Calibración (medida, no supuesta)

| Métrica | Valor |
|---|---|
| Brier del modelo | **0.1714** |
| Brier de predecir siempre la prevalencia (9.42%) | **0.0853** |

> El modelo tiene **peor Brier que un clasificador trivial** que siempre diga
> "9.42%". Es consecuencia directa y consciente de la ponderación de clases
> (§8.1): las probabilidades sirven para **ordenar** riesgo, no para leerse como
> riesgo absoluto.

### 5.5 Interpretación honesta

- ✅ **ROC AUC 0.8403** es un resultado realista y bueno para BRFSS
  (la literatura reporta ≈0.80–0.84). No se debe esperar 0.95.
- ✅ **La regla de triaje captura el 91.9% de los enfermos**: como filtro de
  priorización, cumple.
- ⚠️ **PR AUC 0.3537 y F1 0.3588** son el techo realista con 9.42% de positivos,
  no un defecto de implementación.
- ⚠️ **PPV 27.2% en la banda `alto`**: ~3 de cada 4 pacientes marcados en rojo
  **no** están enfermos. El modelo **prioriza; no confirma**.

### 5.6 Evidencia visual

Figuras en [`docs/figuras/`](figuras/): curva ROC, precision-recall, matriz de
confusión, calibración, importancia de variables (gain), barrido de umbral y
distribución de riesgo. Descritas en `docs/MODELO_ML.md` §7.6.

**Variables más influyentes (gain de XGBoost):** la figura
`05_importancia_features.png` muestra el orden real. La importancia se concentra
en `salud_general`, `edad` y las condiciones cardiovasculares declaradas, lo cual
es coherente con el conocimiento clínico (validez aparente).

---

## 6. Evaluación por subgrupos

**No realizada — y no es posible con el contrato actual.**

| Grupo | ¿Medido? | Motivo |
|---|---|---|
| Sexo | ❌ | La API no recibe ni persiste el sexo |
| Edad | ⚠️ Parcial | La edad entra al modelo (codificada 1-13), pero no se reportaron métricas por tramo etario |
| Raza/etnia, ingreso, educación | ❌ | El dataset los trae, el modelo no los usa y la API no los captura |
| Ubicación (distrito) | ❌ | Existe catálogo de distritos, pero no se usa en el modelo |

**Implicación:** no se puede afirmar que el modelo funcione igual de bien para
todos los grupos. Cualquier afirmación de equidad sería infundada. Si el
proyecto requiere un análisis de equidad, el **primer paso es capturar los
campos** (sexo, tramo etario explícito y distrito) y **segundo**, medir PPV y
sensibilidad por subgrupo.

---

## 7. Consideraciones éticas y de equidad

1. **Asimetría del error.** Un falso negativo (enfermo no priorizado) tiene
   consecuencias graves; un falso positivo es una consulta adicional. El sistema
   está afinado hacia el recall (0.8192) precisamente por eso, y el umbral de F1
   óptimo (0.7026) **no** se usa en el triaje porque dejaría escapar al 44% de
   los enfermos.
2. **Human in the loop obligatorio.** El modelo nunca debe tomar la decisión:
   sugiere una banda y el sistema ya expone los factores de riesgo individuales
   (triaje clínico) para que el profesional juzgue.
3. **Sesgo de representación.** Entrenado con población de EE.UU. (§4.4). La
   ausencia de datos locales es un riesgo de equidad no medido, no solo de
   precisión.
4. **Datos personales sensibles.** El sistema persiste evaluaciones con datos de
   salud vinculados a un paciente identificable. Requiere: control de acceso por
   roles (implementado), política de retención, consentimiento informado y
   cumplimiento de la normativa de protección de datos personales aplicable
   (**no implementado** — el proyecto no incluye flujo de consentimiento).
5. **Riesgo de automatización complaciente.** Mostrar un porcentaje puede
   inducir a confiar más de lo que corresponde. Mitigación: etiquetar siempre el
   resultado como *apoyo al triaje* y no como probabilidad de enfermedad (§8.1).
6. **Reidentificación.** Las 9 variables son reidentificables en poblaciones
   pequeñas. No publicar datasets de evaluaciones reales sin anonimizar.

---

## 8. Limitaciones conocidas

### 8.1 Probabilidades no calibradas (medido)
`scale_pos_weight=9.62` infla las probabilidades **a propósito** para que las
bandas fijas 0.30/0.60 queden pobladas; sin ponderación, el triaje colapsa a
"todo bajo". Efecto secundario: Brier 0.1714 > 0.0853 (§5.4).
**Mitigación pendiente:** `CalibratedClassifierCV` + recalibrar las bandas
(solo calibrar sin mover los umbrales rompería el triaje).

### 8.2 Métricas limitadas por el desbalance
Con 9.42% de positivos, PR AUC 0.3537 y F1 0.3588 son el techo realista. Se debe
**comunicar contra el baseline** (prevalencia), nunca contra el 100%.

### 8.3 Dataset no europeo y desactualizado
BRFSS 2015, EE.UU., autodeclarado. Sin validación con datos locales (§4.4).

### 8.4 Umbrales clínicos fijos definidos sin validación médica
0.30/0.60 son una **decisión de producto** del equipo de desarrollo. Deben
validarse con criterio clínico y, si cambian, recalibrar y reentrenar.

### 8.5 El contrato permite omitir variables predictoras
En `app/schemas/evaluacion.py`, las 8 variables booleanas tienen
`default = False` y `salud_general` tiene `default = 3`. Omitir un campo **no
produce error (422)**: entra como "sin ese factor". Esto sesga el riesgo
**hacia abajo** si un cliente olvida `diabetes` o `presion_alta`
(y hacia arriba si olvida `actividad_fisica`, que es protector).
**Recomendación:** hacer los 9 campos obligatorios (o exigir
`"desconocido"` explícito) y coordinar con el frontend.

### 8.6 Sin explicabilidad por paciente
El modelo no explica *por qué* ese paciente quedó en rojo. El sistema compensa
parcialmente con las reglas de triaje clínico, pero no hay SHAP ni importancia
local.

### 8.7 Sesgo de variable omitida
Al no incluir sexo, IMC, medicación ni laboratorio, el modelo no puede
distinguir matices clínicamente relevantes.

### 8.8 Sin monitoreo de deriva
Nada detecta si la distribución de entrada cambia o si el desempeño cae en el
tiempo.

---

## 9. Recomendaciones de uso responsable

1. Presentar siempre el resultado como **apoyo al triaje**, nunca como
   diagnóstico.
2. Mostrar los **factores de riesgo individuales** junto al nivel (ya implementado
   en el triaje clínico) para evitar el "número mágico".
3. **No** usar la banda `bajo` para descartar enfermedad: contiene al 8.1% de los
   enfermos.
4. **No** interpretar 0.60 como "60% de probabilidad".
5. Validar con datos locales antes de cualquier uso asistencial real.
6. Requerir revisión de un profesional para cualquier acción clínica.

---

## 10. Mantenimiento y monitoreo

| Tarea | Comando | Frecuencia sugerida |
|---|---|---|
| Reentrenar (subir `MODEL_VERSION`) | `python entrenar_modelo.py` | Al cambiar datos o hiperparámetros |
| Regenerar figuras y verificar integridad | `python scripts/generar_figuras.py` | Tras cada reentrenamiento |
| Tests automáticos (72) | `python -m pytest app/tests -q` | Antes de cada entrega |
| Recargar modelo en caliente | `reload_model()` / `reload_metadata()` | Tras reentrenar sin reiniciar |

**Pendiente (no implementado):** monitoreo de deriva de datos, monitoreo de
calibración en producción, auditoría de predicciones y pipeline automático de
reentrenamiento.

**Trazabilidad:** la versión del modelo (`modelo_version`) se devuelve en cada
respuesta de la API y se guarda en cada evaluación, de modo que toda decisión
pasada es reconstruible contra el artefacto que la produjo.

---

## Referencias

- Mitchell, M. et al. (2019). *Model Cards for Model Reporting*. FAT\*.
- CDC/BRFSS 2015 — Heart Disease Health Indicators.
  <https://www.kaggle.com/datasets/alexteboul/heart-disease-health-indicators-dataset>
- Documentación interna: [`MODELO_ML.md`](MODELO_ML.md) ·
  [`TRIAGE_CLINICO.md`](TRIAGE_CLINICO.md) · [`INTEGRACION_ML.md`](INTEGRACION_ML.md)
- Ficha técnica del artefacto: `app/resources/modelo_cardiaco_metadata.json`
