# Reporte PDF académico tipo FUA

Estado vigente: 15/10/2026. `GET /api/v1/evaluaciones/{id}/fua`, con JWT, devuelve PDF adjunto o 404. El formato es una demostración académica inspirada en FUA; no acredita conformidad con un formato oficial.

## Implementación

`app/services/reporte_service.py` dibuja el documento con ReportLab, en tamaño oficio peruano (215 x 330 mm), bloques verticales y salto de página. `EvaluacionMapper` proporciona la interpretación persistida o un fallback si los textos históricos son NULL.

Bloques: encabezado, paciente, evaluación/profesional, variables, resultado, antecedentes/orientación y firmas. Los datos de identidad, peso y talla se leen del paciente; no son una instantánea histórica de esos datos administrativos. El documento de evaluación no sustituye el registro completo de diagnóstico/tratamiento de atenciones.

## Interpretación del resultado

Se muestra **índice del modelo sobre 100**, sin porcentaje. `probabilidad` es el nombre interno heredado del score, cuya semántica depende de la versión. Las evaluaciones v3 imprimen calibración interna, versión de reglas y sus cortes; los históricos sin snapshot se identifican como sin calibrar. Hay una advertencia visible: prototipo académico, no probabilidad clínica, diagnóstico o pronóstico; reglas experimentales que no determinan urgencias.

La categoría original de diabetes se imprime si existe. Si el historial solo conserva el booleano, se informa que falta detalle. La lectura de presión, si existe, se imprime por separado y no altera el antecedente de hipertensión.

Los títulos «Antecedentes registrados» y «Hábitos declarados» describen respuestas, no explicaciones locales del algoritmo. Las orientaciones nuevas dejan las decisiones al profesional. Los textos históricos persistidos se conservan y el PDF avisa de ese hecho.

## Datos y migración

Base nueva: `schema.sql`. Existente: `python scripts/aplicar_migracion_003.py` antes de iniciar esta versión. Las tres columnas nuevas admiten NULL; no se inventan valores de evaluaciones anteriores.

## Verificación

```bash
python -m pytest app/tests -q
```

La suite cubre generación y endpoint PDF, categorías de riesgo, lectura histórica y recorrido con prediabetes/medición persistidas. Para cambios de maquetación se renderiza el PDF y se inspecciona visualmente: un header `%PDF` correcto no garantiza ausencia de texto cortado.

Dependencia: la versión fijada de ReportLab en `requirements.txt`. La etiqueta, datos y limitaciones del modelo se documentan en [MODELO_ML](MODELO_ML.md) y [MODEL_CARD](MODEL_CARD.md).
