# Integración del Modelo ML — CardioPredict

Documento que explica **a detalle y paso a paso** el trabajo de integración
del modelo de Machine Learning hecho sobre el backend. Lee esto en orden:
primero entiende el flujo, luego entrena el modelo real y por último prueba.

---

## 1. Resumen de lo que se hizo

El backend ya tenía la arquitectura ML lista (`app/ml/`) pero **sin modelo
entrenado**: `POST /api/v1/evaluaciones/` respondía `500 "Modelo ML no
disponible"` porque faltaba el archivo `app/resources/modelo_cardiaco.joblib`.

Se hizo:

| Paso | Qué | Resultado |
|------|-----|-----------|
| 1 | Revisar el plan de entrenamiento propuesto | Correcto en columnas/orden/ruta, pero con 4 bugs y 1 trampa |
| 2 | Crear `entrenar_modelo.py` | Script de entrenamiento corregido y listo para el CSV real |
| 3 | Agregar `mapear_edad_cdc()` en `app/ml/preprocessor.py` | La edad en años se convierte al rango 1–13 que el modelo aprendió |
| 4 | Agregar tests unitarios del mapeo de edad | 27 tests pasando |
| 5 | Verificación end-to-end con dataset sintético | `201` con riesgo `bajo` y `alto` correctos |
| 6 | Limpieza de artefactos sintéticos | El repo queda sin modelos falsos |

---

## 2. Cómo funciona la capa ML (arquitectura ya existente)

```
POST /api/v1/evaluaciones/
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ app/services/evaluacion_service.py   (orquesta)             │
│   1. Valida que el paciente exista                          │
│   2. Mapper: request → dict de variables (bool → 0/1)      │
│   3. predictor.predict(dict)  ← import LAZY (solo aquí)    │
│   4. Mapper: dict + predicción → registro para BD          │
│   5. repository.create() → se guarda en MySQL              │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ app/ml/preprocessor.py    limpiar + convertir + ordenar     │
│   - valida que existan las 9 variables                      │
│   - valida rangos (edad 1-120 años, salud 1-5)              │
│   - mapear_edad_cdc(55) → 8   (años → código CDC)           │
│   - arma DataFrame con FEATURE_COLUMNS en orden exacto      │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ app/ml/model_loader.py   carga .joblib UNA vez (singleton)  │
│ app/ml/predictor.py      predict_proba → probabilidad       │
│   - clasifica: <0.30 bajo | 0.30-0.60 moderado | >0.60 alto │
└─────────────────────────────────────────────────────────────┘
```

**Import lazy:** el modelo solo se importa dentro de `evaluate()`. Si el
`.joblib` no existe, el servidor sigue funcionando para auth, pacientes,
catálogos y admin — solo falla la predicción. Ese comportamiento es
intencional (ver `evaluacion_service.py`).

---

## 3. El punto CLAVE: la codificación de la edad (1–13)

El dataset de entrenamiento (**Heart Disease Health Indicators, CDC/BRFSS
2015**) no trae la edad en años: trae la columna `Age` **ya codificada en
13 rangos**:

| Código | Rango de años |
|--------|---------------|
| 1 | 18–24 |
| 2 | 25–29 |
| 3 | 30–34 |
| 4 | 35–39 |
| 5 | 40–44 |
| 6 | 45–49 |
| 7 | 50–54 |
| 8 | 55–59 |
| 9 | 60–64 |
| 10 | 65–69 |
| 11 | 70–74 |
| 12 | 75–79 |
| 13 | 80+ |

**Consecuencia (la trampa):**

- En el **entrenamiento** (`entrenar_modelo.py`) la edad NO se convierte:
  el CSV ya viene en 1–13.
- En la **API** el médico ingresa la edad real en años (55). Si mandáramos
  55 al modelo, este lo interpretaría como "código 55" → predicción
  basura. Por eso la conversión vive en **`app/ml/preprocessor.py`**
  (lado inferencia), con la función `mapear_edad_cdc()`:

```python
mapear_edad_cdc(55) -> 8
mapear_edad_cdc(80) -> 13
```

Ambos lados (entrenamiento e inferencia) usan la **misma tabla de rangos**.
Está documentada en los dos archivos y protegida por tests unitarios
(`app/tests/test_preprocessor.py`).

---

## 4. Archivos creados / modificados

### 4.1 `entrenar_modelo.py` (NUEVO — raíz del proyecto)

Entrena un `RandomForestClassifier` con el CSV de Kaggle y guarda el
modelo donde el backend lo busca.

Correcciones aplicadas al plan original:

1. **Sin emojis en los `print`** — la consola de Windows (cp1252) crashea
   con `✅`/`🌱` (el mismo bug que ya se arregló en el seed).
2. **`class_weight="balanced"`** — solo ~9% de los registros tienen
   enfermedad cardíaca; sin esto el modelo aprendería "siempre no".
3. **Diabetes binarizada a 0/1** — BRFSS usa `2` = prediabetes/solo en
   embarazo, pero la API solo manda `0/1`. El modelo no debe ver valores
   que jamás verá en producción.
4. **Ruta del CSV como argumento** + validación de columnas con error claro.
5. Imprime `Accuracy`, `F1`, `ROC AUC` y matriz de confusión.

Uso:

```bash
python entrenar_modelo.py                                   # CSV en la raíz
python entrenar_modelo.py ruta/al/archivo.csv               # ruta explícita
```

### 4.2 `app/ml/preprocessor.py` (MODIFICADO)

- Nueva función **`mapear_edad_cdc(edad_anios)`** (tabla de la sección 3).
- Dentro de `preprocess()` se agrega el **Paso 3**: convertir la edad
  real a código CDC **después** de validar el rango (1–120 años) y
  **antes** de construir el DataFrame.
- El resto (orden de `FEATURE_COLUMNS`, validaciones) no cambió.

### 4.3 `app/tests/test_preprocessor.py` (MODIFICADO)

Tests nuevos que fijan las fronteras del mapeo (24→1, 25→2, 29→2, 30→3,
54→7, 55→8, 79→12, 80→13, 95→13) y que el DataFrame que ve el modelo
lleva el código (edad 55 → fila con `edad = 8`).

### 4.4 `.gitignore` (MODIFICADO)

El CSV de Kaggle es grande y con datos sensibles de salud → nunca se
commitea:

```gitignore
heart_disease_health_indicators*.csv
*.BRFSS2015*.csv
```

### 4.5 Colección Postman (MODIFICADO)

Se agregó el request **"1 - Crear Evaluacion (Prediccion ML)"** en la
carpeta Evaluaciones (antes solo había GETs) y la variable de colección
`paciente_id`, que también usan el historial por paciente.

---

## 5. Entrenar el modelo REAL — paso a paso

### Requisitos
- CSV descargado de Kaggle:
  https://www.kaggle.com/datasets/alexteboul/heart-disease-health-indicators-dataset
  Archivo: `heart_disease_health_indicators_BRFSS2015.csv` (~253 mil filas).

### Pasos

```bash
# 1. Coloca el CSV en la raíz del proyecto (NO se commitea)

# 2. Con el venv activo, entrena (tarda ~10-30 segundos):
python entrenar_modelo.py

# 3. Salida esperada (valores aproximados con el dataset real):
#    [TRAIN] Filas: 253680 | Positivos: ~9.1%
#    Accuracy:  ~0.74-0.76
#    F1:        ~0.60-0.65
#    ROC AUC:   ~0.75-0.80
#    Modelo guardado en app/resources/modelo_cardiaco.joblib

# 4. Reinicia el servidor (con --reload se reinicia solo al tocar un .py;
#    el .joblib se lee en la PRIMERA predicción, así que no hace falta
#    reiniciar si el modelo se guardó con el server corriendo).
```

> 💡 Si ya tienes un modelo cargado en memoria y reentrenaste, puedes
> forzar la recarga con `app/ml/model_loader.py::reload_model()` o
> simplemente reiniciando uvicorn.

---

## 6. Verificación end-to-end (lo que se ejecutó)

Para comprobar que TODO el pipeline funciona (sin esperar el CSV real),
se generó un **dataset sintético** con las mismas columnas y se repitió
el flujo completo:

```
[1] Generar CSV sintético (3000 filas, 26.8% positivos)
[2] python entrenar_modelo.py _sintetico_brfss.csv
    → ROC AUC 0.7515 | Matriz conf. [[338,101],[66,95]]
    → Modelo guardado en app/resources/modelo_cardiaco.joblib
[3] POST /api/v1/evaluaciones/
    Caso A: 30 años, sano          → 201 | prob=0.013 | riesgo=bajo
    Caso B: 70 años, muchos factores → 201 | prob=0.937 | riesgo=alto
[4] GET /api/v1/evaluaciones/by-paciente/1 → historial OK
[5] python -m pytest app/tests → 27 passed
[6] Limpieza: se borraron el CSV y el .joblib sintéticos
```

Resultado: el backend predice y guarda correctamente. Las probabilidades
"bajo/alto" responden de forma coherente a los factores de riesgo.

---

## 7. Probar en Postman (con el modelo real entrenado)

1. Login como médico → guarda el token.
2. Carpeta **Evaluaciones → "1 - Crear Evaluacion (Prediccion ML)"**:
   - Ajusta `paciente_id` (variable de colección) al paciente que quieras.
   - Edita `edad` (en AÑOS, el backend la convierte solo) y los factores.
   - Send → debe responder **201**:

```json
{
    "id": 6,
    "paciente_id": 1,
    "usuario_id": 2,
    "edad": 70,
    "presion_alta": true,
    "...": "...",
    "probabilidad": 0.937349,
    "clasificacion": "alto",
    "modelo_version": "1.0.0"
}
```

3. **"Historial por Paciente ({{paciente_id}})"** → muestra la línea de
   tiempo del paciente (re-evaluaciones de visitas posteriores).

---

## 8. Troubleshooting

| Síntoma | Causa | Solución |
|---------|-------|----------|
| `500 "Modelo ML no disponible"` | No existe `app/resources/modelo_cardiaco.joblib` | Ejecutar `python entrenar_modelo.py` (sección 5) |
| `500 "Error ML: No se pudo cargar el modelo: ..."` | El `.joblib` está corrupto o fue entrenado con otra versión de sklearn | Reentrenar y volver a guardar |
| Probabilidades raras (todo ~50%) | Edad sin convertir o columnas en otro orden | Verificar `mapear_edad_cdc` y `FEATURE_COLUMNS` (sección 3) |
| `422` al crear evaluación | Body con campos faltantes o edad fuera de 1–120 | Revisar la pestaña Response de Postman (dice el campo exacto) |
| Consola llena de SQL | `DEBUG=True` en `.env` | Cambiar a `DEBUG=False` |

### Umbrales de clasificación (ajustables)

`app/ml/predictor.py::_classify()` usa umbrales fijos para el MVP:

| Probabilidad | Clasificación |
|--------------|---------------|
| < 0.30 | bajo |
| 0.30 – 0.60 | moderado |
| > 0.60 | alto |

En una fase posterior se pueden calibrar con la curva ROC y criterio
clínico — el código ya está aislado en una función para tocarlo sin
romper nada más.
