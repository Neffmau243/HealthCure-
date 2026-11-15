# Contexto e historial por atención

Cada visita tiene su propio tipo de atención (`ambulatoria` o `emergencia`) y
condición materna (`ninguna`, `gestante` o `puerpera`). La condición materna es
independiente del grupo etario y la registra el profesional; no se deduce de la edad.
Con el contrato actual, gestante/puérpera exige sexo femenino registrado.

El backend calcula el grupo a partir de la fecha de nacimiento y guarda una
instantánea con `edad_al_atender`:

| Grupo | Edad en la fecha de atención |
|---|---|
| `nino` | 0–17 |
| `adulto` | 18–59 |
| `adulto_mayor` | Desde 60 |

El paciente expone además su `grupo_etario` **actual**, calculado al consultar.
El historial muestra el grupo y la condición guardados en cada atención, sin
recalcularlos cuando cambia la edad o se corrige el registro administrativo.

## Flujo de uso

1. Registrar al paciente. El formulario y el directorio muestran su grupo actual.
2. Desde 18 años se mantiene el triaje cardiovascular habitual.
   Los menores no entran al triaje ML ni a su cola de pendientes: desde la lista
   «Todos» pueden ir directamente a consultorio con «Atender sin ML».
3. En Consultorio seleccionar el tipo y la condición materna de **esta visita**;
   registrar diagnóstico, tratamiento e indicaciones.
4. La atención aparece en Consultorio, Historias Clínicas e Historial de Atenciones
   con su contexto y descarga de su FUA final.

La emergencia la selecciona el profesional: no se determina desde el índice ML.
El modelo, sus nueve variables y sus umbrales no se modificaron ni se reentrenaron.
La API también bloquea el ML de menores aunque un cliente envíe una edad adulta.

## API y FUA

`POST /api/v1/atenciones/` incorpora `tipo_atencion` y `condicion_materna`.
El servidor asigna `grupo_etario` y `edad_al_atender`; no confía en categorías
calculadas por el cliente. Para conservar compatibilidad, si clientes anteriores
omiten el contexto en una **nueva** visita se usan `ambulatoria` y `ninguna`.

Los endpoints de lectura de atenciones devuelven los cuatro campos. La nueva ruta
`GET /api/v1/atenciones/{id}/fua` descarga un FUA por atención con contexto,
diagnóstico, tratamiento, indicaciones, profesional y evaluación ML si se vinculó.
Funciona también sin evaluación, incluido el caso de menores.

El PDF por evaluación (`GET /api/v1/evaluaciones/{id}/fua`) sigue disponible como
reporte de tamizaje; no identifica una visita final concreta, porque una misma
evaluación puede asociarse a varias atenciones. La interfaz distingue ambas descargas.

## Base existente

Desde la raíz:

```powershell
python -m scripts.migrar_contexto_atencion
```

La migración 003 agrega solo cuatro columnas opcionales y puede ejecutarse más
de una vez. No borra ni reclasifica registros: las atenciones antiguas conservan
`NULL`, mostrado como «No registrado». Para bases nuevas, `schema.sql` ya incluye
las columnas. Reiniciar el backend después de actualizar el código.

## Verificación

```powershell
python -m pytest app/tests -q -p no:cacheprovider
cd frontend
npm test
npm run lint
npm run build
```

`test_contexto_atencion.py` prueba login real, creación de paciente, atención,
persistencia, historial, contenido del PDF, grupos límite, visitas gestante y
puérpera, registros antiguos, migración idempotente y rechazo de ML para menores.
El caso adulto comprueba la predicción real de referencia sin alterar el modelo.

Para repetir la verificación en navegador con datos ficticios:

```powershell
python -m app.tests.browser_app
```

Abrir `http://127.0.0.1:8765` y usar `e2e@example.com` / `e2e-password`.
Este servidor usa SQLite en memoria y omite completamente el seed de MySQL;
sus datos desaparecen al detenerlo. Requiere el frontend compilado.
