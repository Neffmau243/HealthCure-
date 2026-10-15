# Arquitectura del backend — estado vigente

Referencia actualizada el 15/10/2026. El mapeo anterior está en [histórico](historico/MAPPEO_BACKEND.md); no debe usarse para interpretar el estado actual.

## Capas y datos

```text
FastAPI /api/v1 → servicios → repositorios → MySQL
                      ↓
              mapper → predictor → XGBoost + sigmoid v3.0.0
                      ↓
              reglas experimentales → evaluación persistida
```

`app/api/v1` valida autenticación y traduce errores; `app/services` contiene reglas de negocio; `app/repositories` accede a BD; `app/models` representa las seis tablas; `app/schemas` define entrada/salida; `app/ml` carga y aplica el modelo.

Entidades: usuarios, distritos, localidades, pacientes, evaluaciones y atenciones. Evaluaciones guarda nueve predictores, score, banda, versión y textos. Desde la migración 003 guarda además categoría original de diabetes y presión medida (opcionales, fuera del vector ML). Atenciones guarda diagnóstico, tratamiento e indicaciones escritos por el profesional, con vínculo opcional a evaluación del mismo paciente.

## Autenticación y permisos

JWT con expiración de 60 minutos y contraseñas con bcrypt. Roles reales: `admin` y `usuario`; médico/enfermera comparten `usuario`. Registro público crea solo `usuario`. Administración exige admin. Usuarios autenticados pueden leer pacientes y evaluaciones; solo creador o admin edita un paciente con creador asignado. Existen controles para evitar desactivar/degradar al último administrador o la propia cuenta.

La edición restringida de pacientes no significa aislamiento de lectura por profesional. No se presenta como cumplimiento completo para uso asistencial real.

## Evaluación

El servicio busca al paciente, calcula edad desde nacimiento en America/Lima y rechaza menores o discrepancias. El esquema exige nueve predictores. El mapper entrega únicamente esas nueve variables al preprocesador. La medición de presión no sustituye el diagnóstico previo de hipertensión.

La salida `probabilidad` es un score con calibración interna para v3; nombre conservado por compatibilidad. Reglas y colores no son un protocolo validado. Los textos persistidos del historial se devuelven intactos; NULL históricos se interpretan al leer sin modificar la fila.

## Ejecución y migraciones

[README](../README.md) contiene instalación y arranque. Base nueva: `schema.sql`. Base existente: migraciones pendientes 001/002 y luego `python scripts/aplicar_migracion_003.py` antes de iniciar esta versión. Ese último script es repetible y no actualiza evaluaciones existentes.

Pruebas: `python -m pytest app/tests -q`, SQLite en memoria. Incluyen API, permisos, coherencia de datos, migración repetible, historial, modelo real y PDF. El código de SQL/MySQL debe verificarse también en el entorno configurado.

Rutas y frontend: [MAPEO_RUTAS_FRONT_BACK](MAPEO_RUTAS_FRONT_BACK.md). Experimento y límites: [MODELO_ML](MODELO_ML.md) y [MODEL_CARD](MODEL_CARD.md).

La [integración v3 y generalización](INTEGRACION_V3_Y_GENERALIZACION.md) documenta bandas versionadas, migración 004 y estabilidad.
