# Componente ML — release 3.0.0

Estado vigente: 15/10/2026. Prototipo académico de clasificación de perfiles asociados con antecedentes autodeclarados de enfermedad coronaria o infarto. No estima eventos futuros ni determina diagnóstico, tratamiento o urgencia.

## Modelo activo y trazabilidad

XGBoost ponderado + calibración sigmoid (`CalibratedClassifierCV`, estimador congelado). La aplicación carga `app/resources/modelo_cardiaco.joblib` y `modelo_cardiaco_metadata.json`. La release íntegra está en `app/resources/modelos/3.0.0/`; la referencia anterior, en `app/resources/modelos/2.0.0/`.

La metadata valida features, versión, cortes y política. El cargador comprueba SHA256 del modelo antes de deserializar; incoherencia de bundle o cachés causa error, sin aplicar cortes de respaldo a un calibrador distinto. `reload_model()` recarga también metadata; para una instancia en ejecución se recomienda reiniciar el servidor.

Cada evaluación nueva guarda `modelo_version` y el snapshot `politica_modelo`: versión de reglas, cortes, semántica y precisión del score. La migración aditiva 004 añade JSON nullable; los históricos conservan score, clasificación y textos. Un registro sin snapshot sigue interpretándose como histórico sin calibrar. No comparar valores entre versiones como si compartieran escala.

## Contrato de entrada

Los nueve predictores son obligatorios y mantienen orden/codificación:

| Predictor | Significado |
| --- | --- |
| edad | API: años 18–120, coherentes con nacimiento a fecha de Lima; se convierte a CDC 1–13 |
| presion_alta | Diagnóstico previo declarado, no medición aislada |
| colesterol_alto | Antecedente declarado de colesterol alto |
| tabaquismo | Al menos 100 cigarrillos en la vida; no consumo actual |
| actividad_fisica | Actividad declarada en últimos 30 días |
| antecedente_acv | Antecedente declarado de ACV |
| diabetes | Prediabetes o diabetes agrupadas |
| salud_general | 1 excelente, 2 muy buena, 3 buena, 4 regular, 5 mala |
| dificultad_para_caminar | Dificultad al caminar o subir escaleras |

Edad CDC: 1=18–24, 2=25–29, 3=30–34, 4=35–39, 5=40–44, 6=45–49, 7=50–54, 8=55–59, 9=60–64, 10=65–69, 11=70–74, 12=75–79, 13=80+. El CSV ya contiene códigos; no se convierten por segunda vez al entrenar.

Se conservan aparte `estado_diabetes` (ninguna/prediabetes/diabetes) y presión sistólica/diastólica opcionales. No son nuevas features. API: 422 para omisiones, rangos o contradicciones; 400 para inexistencia del paciente, edad real fuera de población o discrepante; 401 sin autenticación.

## Entrenamiento y calibración

253,680 filas del CSV transformado de BRFSS 2015, 23,893 positivos; nueve features. XGBoost: 400 árboles, profundidad 3, learning rate 0.05, subsample/colsample 0.8. Configuración procedente del experimento v2, sin una nueva búsqueda de hiperparámetros.

Separación por perfiles idénticos de las nueve features, sin target ni sexo en los grupos: train 152,725; calibration 36,116; validation 27,564; test 37,275. Cero perfiles compartidos entre particiones. Entrena solo en train, calibra solo en calibration y elige variante/cortes solo en validation. No hay reajuste posterior con validation/test.

El CSV y los hiperparámetros ya habían sido explorados. La separación interna mejora el protocolo, pero no convierte esos datos en una cohorte nueva. El experimento de origen está documentado en [segunda etapa](SEGUNDA_ETAPA_EXPERIMENTAL.md).

## Score y política activa

`probabilidad` conserva su nombre API histórico. En v3 es un score con calibración interna, redondeado a seis decimales **antes de clasificar y persistir**; se presenta como índice sobre 100. La calibración interna no demuestra probabilidad clínica individual o generalización local.

Reglas **bandas-academicas-3.0.0**:

| Score | Índice sobre 100 | Banda |
| --- | --- | --- |
| <0.051065 | <5.1065 | bajo |
| 0.051065 a <0.210469 | 5.1065 a <21.0469 | moderado |
| >=0.210469 | >=21.0469 | alto |

Corte inferior: mayor umbral con recall >=90% en validation; superior: máximo F1 en validation, empate mayor umbral. Son criterios académicos, no puntos clínicos. El 90% es objetivo de selección en validation, no garantía de recall en test u otras poblaciones. Los textos nuevos describen bandas y revisión experimental; no prioridad de urgencias.

## Métricas internas de la release

Test por perfiles, 37,275 filas y 3,798 positivos (10.19%): ROC AUC **0.8285**, AP **0.3513**, Brier **0.0773** frente a 0.1907 del candidato crudo y 0.0916 de prevalencia constante de train. Calibrar cambia escala, no mejora aquí AUC/AP.

| Corte | Precision | Recall | F1 | Fracción marcada |
| --- | --- | --- | --- | --- |
| >=0.051065: intermedia o alta | 0.2070 | 0.8778 | 0.3350 | 0.4321 |
| >=0.210469: alta | 0.2953 | 0.6435 | 0.4048 | 0.2221 |

AUC IC95% por bootstrap de perfiles: 0.8040–0.8487. F1 al corte superior: 0.3804–0.4277. Condicionados en modelo/umbral, no incluyen variación de reentrenamiento. AP es `average_precision_score`, no área trapezoidal.

Las cinco particiones adicionales, investigación de subgrupos y evaluación temporal externa se presentan en [integración y generalización](INTEGRACION_V3_Y_GENERALIZACION.md). No ocultar el recall inferior de jóvenes ni las diferencias por sexo; no se afirma equidad ni utilidad clínica.

## Ejecutar y verificar

```bash
python scripts/aplicar_migracion_003.py
python scripts/aplicar_migracion_004.py
python -m pytest app/tests -q
# Nuevo experimento offline; no promueve candidatos automáticamente:
python entrenar_modelo.py --output experimentos_ml/otra_ejecucion --report-dir docs/experimentos/otra_ejecucion
```

El script `preparar_release_v3.py` documenta la promoción realizada: congela política, genera metadata, archiva referencia anterior e instala una release. Preparar dos veces el mismo destino falla para conservar evidencia; activar una release ya instalada es idempotente.

`python scripts/generar_figuras.py` reproduce exclusivamente **v2 archivada**, con su split histórico 80/20 seed 42. Sus figuras no representan la v3. Las métricas antiguas y limitaciones del umbral sobre test se conservan en [documentación histórica v2](historico/MODELO_ML_v2.md).

## Referencias

[Model Card](MODEL_CARD.md), [reglas y persistencia](TRIAGE_CLINICO.md), [contrato API](INTEGRACION_ML.md), [CDC BRFSS](https://www.cdc.gov/brfss/annual_data/annual_2017.html), [calibración sklearn](https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html).

## Evaluación temporal externa completada

BRFSS 2017: 373,536 casos completos, 34,408 positivos; modelo y bandas congelados, sin ajuste con esos datos. ROC AUC 0.8398, AP 0.3509, Brier 0.0704. Recall intermedia/alta 0.8971; en banda alta, recall 0.5963 y F1 0.3984. Persiste recall reducido en jóvenes (0.4214 al corte inferior, 0.1625 al superior).

Es otra edición de la encuesta de EE.UU., obtenida de una copia pública archivada con procedencia y hashes registrados; no una cohorte clínica peruana. El cambio de selección de casos y los patrones discretos compartidos entre años limitan las conclusiones. Ver [protocolo, subgrupos y límites de la evaluación externa](INTEGRACION_V3_Y_GENERALIZACION.md).
