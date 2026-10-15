# Reglas experimentales de priorización

Referencia vigente: 15/10/2026. Se conserva el nombre técnico `triaje_clinico` en el contrato por compatibilidad. **No es un protocolo clínico validado.** El prototipo no determina urgencias, diagnóstico, exámenes, tratamiento ni derivación.

## Responsabilidades

El modelo entrega un score; `app/ml/predictor.py` aplica bandas leídas de metadata. El mapper invoca `app/services/evaluacion_triaje_service.py`, guarda los textos y construye la respuesta. El ML no escribe recomendaciones.

| Campo API | Significado |
|---|---|
| `nivel_alerta`, `codigo_color` | Etiquetas históricas y color de la banda experimental |
| `accion_sugerida` | Orientación para revisión humana del perfil |
| `factores_riesgo_detectados` | Antecedentes presentes en las respuestas; no explica contribuciones del modelo |
| `factores_protectores` | Hábitos declarados; no implica efecto causal individual demostrado |
| `recomendaciones_medicas` | Orientaciones generales del prototipo; nombre histórico del contrato |

## Bandas

| Score con calibración interna | Banda | Color | Orientación vigente |
|---|---|---|---|
| <0.051065 | bajo | verde | Continuar evaluación profesional; bajo no descarta enfermedad |
| 0.051065 a <0.210469 | moderado | amarillo | Revisar antecedentes durante la consulta |
| >=0.210469 | alto | rojo | Revisión del perfil sin establecer urgencia |

Reglas `bandas-academicas-3.0.0`. El corte inferior es el mayor que conserva recall >=90% en validation; el superior maximiza F1 en validation. Son criterios académicos, no clínicos ni garantías en otras cohortes. Se seleccionan con el score redondeado a seis decimales, igual que en inferencia.

Cada nueva evaluación guarda `politica_modelo` con reglas, cortes y semántica del score. El fallback usa ese snapshot; los históricos sin snapshot mantienen 0.30/0.60 y textos previos. No se aplican cortes nuevos a scores antiguos.

Para todas las bandas se propone verificar los antecedentes, dejar estudios/seguimiento/tratamiento al profesional e indicar que la regla no decide urgencias. No se prescribe ECG inmediato ni cambios de medicación.

## Semántica de antecedentes

- Hipertensión: diagnóstico previo declarado; una lectura elevada no activa automáticamente ese antecedente.
- Tabaco: al menos 100 cigarrillos durante la vida, no tabaquismo activo. Un negativo se describe como ausencia de ese antecedente, no como «No fumador».
- Diabetes: `estado_diabetes` distingue ninguna/prediabetes/diabetes. Si solo hay booleano positivo, se informa que falta el detalle; no se inventa diagnóstico.
- Actividad: declarada en los últimos 30 días; no se afirma regularidad no medida.

## Persistencia y registros anteriores

Las seis columnas de textos/listas conservan la salida creada en cada evaluación. Si el texto ya está persistido, se devuelve **sin reescribirlo**. Por ello el resultado incluye una advertencia de que los textos históricos pueden reflejar reglas anteriores.

Si las columnas antiguas son NULL, el mapper arma una interpretación al leer, sin actualizar la fila. Los campos nuevos de detalle de diabetes, presión y snapshot de política quedan NULL en el historial antiguo. Migraciones 003 y 004 son aditivas y no actualizan esas filas.

Los nombres y datos históricos no deben emplearse como protocolo vigente. Para migrar datos originales, ver [INTEGRACION_ML](INTEGRACION_ML.md).

## Pruebas

`python -m pytest app/tests -q` cubre colores, límites, antecedentes, reglas sin indicaciones clínicas prescriptivas, persistencia histórica, coherencia de inputs y recorrido HTTP con el modelo real.

Cambiar reglas requiere revisar el texto del servicio y sus pruebas. Si se modifica la interpretación del score, actualizar conjuntamente [MODELO_ML](MODELO_ML.md), [MODEL_CARD](MODEL_CARD.md), frontend y reporte PDF.
