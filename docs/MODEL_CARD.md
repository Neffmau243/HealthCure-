# Model Card — CardioPredict 3.0.0

Fecha: 15/10/2026. **Uso académico, sin validación clínica ni local.** [Referencia técnica](MODELO_ML.md).

## Tarea y uso

Clasifica perfiles asociados con antecedentes autodeclarados de enfermedad coronaria o infarto en BRFSS. No predice el futuro. Uso previsto: demostración educativa de clasificación supervisada, gestión de pacientes y revisión humana. Fuera de alcance: diagnóstico/descarte, urgencias, tratamientos y decisiones autónomas con pacientes.

Adultos 18–120 con fecha de nacimiento registrada y nueve respuestas explícitas. La API comprueba mayoría de edad, fecha de nacimiento, rangos y coherencia de los datos originales. En BRFSS la edad está agrupada; la categoría superior es 80+.

## Artefacto y política

XGBoost ponderado con calibración sigmoid ajustada en un conjunto separado del entrenamiento. Versión 3.0.0; nueve features: edad, hipertensión previa, colesterol alto, tabaco de por vida >=100 cigarrillos, actividad en 30 días, ACV, prediabetes/diabetes agrupadas, salud general y movilidad. Sexo se usa para auditoría offline, no como predictor.

Se guarda categoría original de diabetes y presión medida fuera del vector ML. El nombre `probabilidad` es histórico: se presenta como índice sobre 100 y no como probabilidad clínica.

Bandas académicas `bandas-academicas-3.0.0`: <0.051065 bajo; 0.051065–<0.210469 moderado; >=0.210469 alto. Cortes seleccionados en validation: recall >=90% para intermedia/alta y máximo F1 para alta. Ese objetivo no garantiza recall en otros datos. El score se redondea a seis decimales antes de clasificar.

Cada evaluación conserva snapshot de reglas y cortes. Los históricos sin snapshot siguen con sus textos/score de versión anterior. El índice no es comparable entre versiones sin considerar el cambio de escala. La v2 se archiva íntegra.

## Datos y evaluación interna

CSV transformado de BRFSS 2015, EE.UU., 253,680 filas, 9.42% positivas. Son respuestas de encuesta, no confirmación clínica independiente. Separación por perfiles disjuntos: entrenamiento 152,725; calibración 36,116; validación 27,564; test 37,275. Los parámetros proceden del desarrollo anterior en el mismo CSV: no es una cohorte externa inédita.

Test principal: ROC AUC 0.8285, AP 0.3513, Brier 0.0773. Al corte alto: precision 0.2953, recall 0.6435, F1 0.4048. Al corte inferior: recall 0.8778, precision 0.2070. La banda baja no descarta enfermedad. El baseline logístico tiene rendimiento cercano; no se demuestra superioridad estadística de XGBoost.

Las cinco repeticiones adicionales y la fuente externa temporal se documentan con sus resultados, procedencia y límites en [integración v3 y generalización](INTEGRACION_V3_Y_GENERALIZACION.md).

## Limitaciones y subgrupos

- El recall al corte alto es bajo en jóvenes y varía por sexo y composición de edad. No se ha demostrado equidad ni eliminado esas diferencias.
- La calibración interna no es una calibración clínica peruana, ni convierte el objetivo retrospectivo en pronóstico futuro.
- Los perfiles de nueve variables son discretos y pueden coincidir entre personas diferentes; la deduplicación es sensibilidad, no identificación de encuestados.
- Intervalos bootstrap por perfiles no incluyen toda la incertidumbre de selección de modelo. Las repeticiones usan el mismo CSV; no son cohortes independientes.
- No hay explicaciones locales SHAP, seguimiento clínico, evaluación de utilidad, monitoreo de deriva o validación profesional de las reglas.
- Se necesitan consentimiento, protección y retención de datos apropiados antes de cualquier uso asistencial real.

## Mantenimiento

Modelo/metadata y reglas se distribuyen juntos, con hash verificado y fallo explícito ante incoherencia. Las releases y snapshots permiten distinguir resultados nuevos e históricos. El seed contiene valores fijos de demostración; no demuestra rendimiento del modelo actual. El entrenamiento offline no modifica automáticamente la aplicación.

La [card anterior de v2](historico/MODEL_CARD_v2.md) se conserva como historia del proyecto.

## Evaluación temporal externa completada

BRFSS 2017: 373,536 casos completos, 34,408 positivos; modelo y bandas congelados, sin ajuste con esos datos. ROC AUC 0.8398, AP 0.3509, Brier 0.0704. Recall intermedia/alta 0.8971; en banda alta, recall 0.5963 y F1 0.3984. Persiste recall reducido en jóvenes (0.4214 al corte inferior, 0.1625 al superior).

Es otra edición de la encuesta de EE.UU., obtenida de una copia pública archivada con procedencia y hashes registrados; no una cohorte clínica peruana. El cambio de selección de casos y los patrones discretos compartidos entre años limitan las conclusiones. Ver [protocolo, subgrupos y límites de la evaluación externa](INTEGRACION_V3_Y_GENERALIZACION.md).
