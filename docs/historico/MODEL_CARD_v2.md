> Histórico: documentación de v2 antes de integrar la release calibrada. Ver [versión vigente](../MODEL_CARD.md).

# Model Card — CardioPredict 2.0.0

Estado vigente: 15/10/2026. **Prototipo académico, sin validación clínica.** Referencia experimental completa: [MODELO_ML](../MODELO_ML.md).

## Modelo y tarea

XGBClassifier, 400 árboles, profundidad 3, ponderación positiva 9.62. Artefacto y metadata en `app/resources/modelo_cardiaco.joblib` y `modelo_cardiaco_metadata.json`, entrenados el 09/10/2026. Nueve features. Se eligió por mayor ROC AUC de CV frente a Random Forest; la pequeña diferencia no demuestra superioridad general ni equivalencia estadística.

Clasifica perfiles asociados con antecedentes autodeclarados de enfermedad coronaria o infarto. No estima incidencia futura ni cubre cualquier enfermedad cardíaca.

## Uso previsto y población

Demostración académica de integración entre una clasificación supervisada, gestión de pacientes y reglas experimentales de priorización. Usuarios de la demo: personal de salud con revisión humana.

Solo adultos de 18 a 120 años con fecha de nacimiento registrada y nueve respuestas explícitas. La API rechaza menores, predictores omitidos y edad incompatible con nacimiento. La edad se evalúa en America/Lima.

Fuera de alcance: diagnóstico o descarte, pronóstico futuro, urgencias, selección de tratamiento, uso autónomo con pacientes y extrapolación a población local sin validación.

## Datos y variables

BRFSS 2015 transformado por el dataset de Kaggle: 253,680 filas, 23,893 positivos (9.42%), nueve features seleccionadas. Encuesta de adultos de EE.UU.; condiciones autodeclaradas, no confirmación diagnóstica independiente.

Variables: edad, hipertensión diagnosticada previamente, colesterol alto, antecedente de al menos 100 cigarrillos en la vida, actividad física en 30 días, antecedente de ACV, prediabetes/diabetes agrupada, salud general y dificultad al caminar.

La aplicación conserva `estado_diabetes` aparte. Los booleanos históricos positivos no permiten inferir cuál categoría se declaró. La presión medida se guarda aparte y no sustituye el antecedente de hipertensión en el input ML.

## Salida e interpretación

`probabilidad` es el nombre histórico del **score no calibrado [0,1]**. Se muestra como índice **[0,100]**, sin porcentaje. Las bandas <0.30, 0.30–<0.60 y >=0.60 son reglas experimentales; no son cortes clínicos validados.

Los antecedentes listados provienen de respuestas, no de atribuciones locales del modelo. Las evaluaciones con textos históricos persistidos conservan sus textos y se identifican como históricas en la advertencia del resultado.

## Evaluación interna

80/20 estratificado, seed 42: test 50,736 casos, 4,779 positivos. ROC AUC **0.8403**, average precision **0.3537**. A 0.50: precision **0.2297**, recall **0.8192**, F1 **0.3588**; matriz `[[32831,13126],[864,3915]]`.

A 0.30 (moderado o alto): recall **0.9188**, precision **0.1770**. Banda alta: 3,419 positivos de 12,587 casos (**27.16%**), captura el 71.54% de positivos. El 8.12% de positivos queda en banda baja; esa banda no descarta enfermedad.

Brier **0.1714** frente a **0.0853** del baseline de prevalencia. El score no debe interpretarse como probabilidad clínica. El F1 óptimo **0.4101** a 0.7026 fue seleccionado y evaluado en el mismo test: es exploratorio y requiere una validación independiente del umbral.

## Limitaciones y equidad

- Sin datos locales, validación temporal o clínica. Generalización asistencial desconocida.
- Filas repetidas y perfiles idénticos entre train/test requieren análisis de sensibilidad; no se deduce identidad de personas de esa coincidencia.
- El desbalance no demuestra un límite máximo de F1 o average precision. Faltan baseline sencillo e intervalos.
- Es posible evaluar sexo y edad offline con el CSV y el split; la segunda etapa ya reporta diferencias descriptivas por sexo y edad; eso no acredita equidad. En la aplicación se guardan sexo del paciente y edad evaluada.
- El artefacto activo no está calibrado y no hay SHAP por paciente ni monitoreo de deriva. Existe calibración interna de candidatos offline, sin validación clínica.
- Las reglas de orientación no están validadas por un protocolo clínico y no determinan exámenes o tratamiento.
- La aplicación no incluye un flujo de consentimiento o una política de retención para uso asistencial real.

## Mantenimiento y trazabilidad

Los inputs, score, banda y versión se guardan por evaluación. Se preservan el texto histórico y los nuevos datos originales opcionales mediante migración aditiva 003.

La metadata y el modelo se cachean por separado. Tras reemplazarlos hay que reiniciar o recargar ambos. El nuevo entrenamiento experimental usa carpetas nuevas con código, hashes, configuración, particiones, candidatos y una copia de la referencia activa. No sobrescribe el modelo de la app. Aún falta promover y versionar conjuntamente nuevas reglas y bandas; la versión histórica por sí sola no permite reconstruir todas las decisiones pasadas.

Las evaluaciones del seed son valores fijos de demostración v1.0.0, no evidencia de predicciones del modelo actual. Las métricas y el modelo v2.0.0 se verifican con `python scripts/generar_figuras.py`.

La [segunda etapa experimental](../SEGUNDA_ETAPA_EXPERIMENTAL.md) ya evaluó umbrales elegidos en validation, sensibilidad a duplicados, baselines, intervalos y subgrupos. El candidato sigmoid obtuvo AUC 0.8285 y Brier 0.0773 en un test agrupado distinto del de v2. El modelo de esta card sigue siendo v2.0.0; el candidato offline no lo reemplaza. El test nuevo es interno sobre un CSV previamente explorado, no validación externa.

## Referencias

[Dataset](https://www.kaggle.com/datasets/alexteboul/heart-disease-health-indicators-dataset) · [Codebook CDC](https://www.cdc.gov/brfss/annual_data/2015/pdf/codebook15_llcp.pdf) · [Calibración](https://scikit-learn.org/stable/modules/calibration.html) · [Documentación técnica](../MODELO_ML.md).
