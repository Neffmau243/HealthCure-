# Mapa y estado vigente de HealthCure

Actualizado el 15/10/2026. [Versión histórica anterior](historico/MAPPEO_Y_ESTADO_DEL_PROYECTO.md).

## Qué está implementado

- Backend FastAPI por capas, MySQL, JWT y roles admin/usuario.
- Registro y consulta de pacientes, permisos de edición y catálogos.
- XGBoost + sigmoid v3.0.0 con nueve predictores y metadata; el artefacto está incluido.
- Validación de adultos, coherencia de edad y presencia de predictores.
- Conservación de estado original de diabetes y presión medida mediante migración 003.
- Reglas experimentales de priorización; preservación de textos históricos.
- Atenciones del consultorio registradas por profesionales.
- Frontend React integrado y servido desde el backend tras compilar.
- Resumen agregado del dashboard y cola diaria de triaje.
- Reporte PDF académico con índice de 0 a 100.
- Pruebas backend, pruebas de transformación del formulario, lint y build.

## Alcance académico

Clasifica perfiles asociados con antecedentes declarados de enfermedad coronaria o infarto; no predice eventos futuros. El score v3 tiene calibración interna; no validación clínica. Las bandas no determinan diagnóstico, urgencia ni tratamiento. El seed es demostrativo, no evidencia del modelo.

## Segunda etapa y pendientes

La [segunda etapa experimental](SEGUNDA_ETAPA_EXPERIMENTAL.md) ya implementa y ejecuta selección de umbral en validation, calibración separada, sensibilidad a duplicados, baselines, intervalos y subgrupos. Archiva código y artefactos por ejecución sin cambiar la app.

Quedan integración/versionado de bandas del candidato, estabilidad entre particiones, validación externa/local, investigación de diferencias entre subgrupos y monitoreo. No hay validación clínica.

## Mapa de lectura

1. [README](../README.md): propósito, instalación y ejecución.
2. [Arquitectura backend](MAPPEO_BACKEND.md): capas, datos y permisos.
3. [Rutas e integración web](MAPEO_RUTAS_FRONT_BACK.md).
4. [ML](MODELO_ML.md): referencia técnica vigente y métricas.
5. [Model Card](MODEL_CARD.md): población y límites.
6. [Reglas](TRIAGE_CLINICO.md) y [PDF](FUA_PDF.md).
7. [Guía de integración](INTEGRACION_ML.md): contrato y migración.

Evitar duplicar métricas en documentos de arquitectura: el valor de referencia está en la metadata y se contrasta en MODELO_ML.

La [integración v3 y generalización](INTEGRACION_V3_Y_GENERALIZACION.md) documenta bandas versionadas, migración 004 y estabilidad.
