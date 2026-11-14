# Contexto e historial por atención

Cada visita tiene su propio tipo de atención (`ambulatoria`, `referencia` o
`emergencia`), su lugar de atención (`intramural` o `extramural`) y
condición materna (`ninguna`, `gestante` o `puerpera`). La condición materna es
independiente del grupo etario y la registra el profesional; no se deduce de la edad.
Con el contrato actual, gestante/puérpera exige sexo femenino registrado.

## Categoría administrativa para el FUA

Registro de pacientes, Triaje y Consultorio comparten tres opciones visibles:
**General**, **Gestante** y **Puérpera**. General es la opción inicial; muestra
el grupo calculado por edad (niño/a, adulto/a o adulto/a mayor). El proyecto no
tiene un grupo independiente «joven»: mantiene los intervalos de la tabla inferior.

El contexto actual se guarda en `pacientes.contexto_atencion`. Puede actualizarse
en una visita posterior y no es una clasificación permanente de la persona.
La categoría actual sirve para precargar el siguiente formulario; debe verificarse.
Las instantáneas de evaluaciones y atenciones anteriores no se modifican.

| Categoría | Campos administrativos específicos del FUA |
|---|---|
| General | Identificación y grupo por edad; sin datos maternos |
| Gestante | Fecha probable de parto, edad gestacional en semanas, número de control prenatal, altura uterina |
| Puérpera | Fecha de parto y número de control puerperal |

Los datos específicos son opcionales: lo desconocido permanece sin registrar.
Cambiar de categoría limpia los campos del formulario anterior, previa confirmación
si ya contienen datos. El servidor rechaza campos de otra categoría y fechas de
parto futuras. Los datos maternos de la visita se conservan en
`observaciones_clinicas.datos_maternos` y se imprimen en las casillas de salud
materna del formulario oficial y en su anexo.

En Triaje, **Guardar categoría para el FUA** usa
`PUT /api/v1/pacientes/{id}/contexto-atencion`: guarda únicamente este contexto,
sin ejecutar el modelo ni cambiar los datos de identidad. El personal autenticado
que registra visitas puede actualizar este contexto; la edición administrativa
general conserva sus permisos anteriores. **Guardar y Calcular Riesgo** mantiene
la evaluación cardiovascular para adultos como acción separada.

En Consultorio no se habilita la atención hasta elegir paciente; vincular una
evaluación ML es opcional. Al guardar se ofrece la descarga inmediata de ese FUA.

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

`POST /api/v1/atenciones/` incorpora `tipo_atencion`, `lugar_atencion` y `condicion_materna`.
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
python -m scripts.migrar_categoria_paciente
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

### Casos de demostración disponibles en el puerto 8765

| Documento ficticio | Paciente | Caso inicial |
|---|---|---|
| E2E-10001 | Prueba, Lucía Materna | Mujer de 20 años, General; permite probar General → Gestante → Puérpera |
| E2E-10002 | Prueba, Diego Infantil | Niño de 10 años, atención y FUA sin ML |
| E2E-10003 | Prueba, Rosa Mayor | Adulta mayor de 72 años |
| E2E-10004 | Prueba, Elena Gestante | Gestante con datos maternos de ejemplo y FUA |
| E2E-10005 | Prueba, Ana Puérpera | Puérpera con fecha de parto de ejemplo y FUA |

Cada caso tiene una atención ficticia inicial. Las fechas se calculan al iniciar
el servidor de demostración. Estos registros no se insertan en la base del puerto
8000. `test_categoria_paciente.py` comprueba el ciclo completo, las instantáneas,
los permisos, la migración y que estos datos no entren en las nueve variables ML.
