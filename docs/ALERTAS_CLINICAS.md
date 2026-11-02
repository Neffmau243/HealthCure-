# Alertas sobre el estado actual: alcance y casos de prueba

El formulario original capturaba pulso, temperatura y saturación, pero no los
enviaba al backend. Una saturación de 75% podía acompañar un índice ML bajo,
porque XGBoost solo recibía los nueve predictores históricos. No es un modelo
entrenado para reconocer deterioro agudo, embarazo o urgencia pediátrica.

## Comportamiento implementado

- El índice ML y su clasificación permanecen intactos. No se agregaron variables
  al estimador ni se reentrenó el artefacto.
- Se guardan `observaciones_clinicas` y `alerta_clinica` en evaluaciones y atenciones.
  Incluyen ambas cifras de presión, pulso, frecuencia respiratoria, saturación,
  temperatura, peso/talla opcionales, condición materna y revisión de síntomas.
- `POST /api/v1/clinica/revisar` revisa una entrada autenticada sin ML ni escritura
  de una consulta. Permite mostrar avisos antes de guardar o esperar al modelo.
- Al guardar, el servidor vuelve a calcular la alerta; no acepta avisos fabricados
  por el cliente. Conserva motivos y versión `alertas-1.0.0` como instantánea.
- Una alerta inmediata o prioritaria sustituye los textos de control rutinario en
  `triaje_clinico`, sin modificar `probabilidad` ni `clasificacion` del modelo.
  Pantalla, historial y ambos PDF muestran los avisos. El FUA final incluye signos,
  síntomas, contexto y acto médico. No propone tratamiento ni dosis desde estas reglas.
- Un campo vacío significa no registrado. Síntomas `null` significa no revisados;
  `[]` significa que el profesional confirmó ausencia de los síntomas listados.
  Sin datos no se emite un mensaje de estabilidad ni se pinta un resultado clínico verde.

## Reglas y fuentes

Son **avisos parciales de seguridad implementados por el proyecto**, no una
implementación de NEWS2, IMCI, un diagnóstico de sepsis ni un protocolo de triaje
clínicamente validado. Las categorías de respuesta son del producto. Su
adecuación al centro, población y objetivos individuales requiere revisión clínica.

| Situación registrada | Aviso del proyecto |
|---|---|
| Dolor torácico actual, dificultad respiratoria en reposo, nueva alteración de conciencia, convulsiones, déficit neurológico súbito o sangrado abundante | Valoración inmediata |
| Adulto: SpO₂ ≤91%, pulso ≤40 o >130, FR ≤8 o ≥25, sistólica ≤90, temperatura ≤35 | Valoración inmediata |
| Adulto: SpO₂ 92–95%, pulso 41–50 o 111–130, FR 9–11 o 21–24, temperatura >35 y <36 o ≥38.1 | Valoración prioritaria, sin demora |
| Adulto: sistólica ≥180 **o** diastólica ≥120, sin síntomas de alarma | Confirmar medición y revisión prioritaria; no se diagnostica emergencia hipertensiva solo por la cifra |
| Presión muy elevada con cefalea intensa nueva, cambios visuales o dolor abdominal intenso | Valoración inmediata |
| Gestante/puérpera: sistólica ≥160 **o** diastólica ≥110; fiebre ≥38; cefalea intensa, cambios visuales, dolor abdominal intenso o disminución de movimientos fetales referida | Valoración inmediata |
| Gestante/puérpera: presión ≥140 sistólica o ≥90 diastólica, sin criterio anterior; pulso 100–130 en gestante | Revisión prioritaria |
| Menor: SpO₂ <90, convulsiones, incapacidad para beber/alimentarse u otro síntoma general de alarma | Valoración inmediata; sin ML |
| Lactante menor de 3 meses con temperatura ≥38 | Valoración inmediata; edad calculada desde el nacimiento en meses completos |
| Pulso o FR registrado en cero | Confirmación y valoración inmediata; cero no se trata como dato ausente |
| Niño o contexto materno sin alarma detectada | Requiere valoración específica; no se aplican tablas adultas para declarar normalidad |
| Adulto con datos incompletos | Datos insuficientes; no se concluye estabilidad |

Las cifras adultas se contrastaron con los parámetros de [RCP NEWS2](https://www.rcp.ac.uk/resources/national-early-warning-score-news-2/).
Las alarmas hipertensivas se contrastaron con [NHLBI](https://www.nhlbi.nih.gov/health/high-blood-pressure/symptoms).
Para contexto materno se consultaron [NICE NG133](https://www.nice.org.uk/guidance/ng133/chapter/recommendations),
[NICE NG255](https://www.nice.org.uk/guidance/ng255) y [CDC Hear Her](https://www.cdc.gov/hearher/maternal-warning-signs/index.html).
Para peligro pediátrico e hipoxemia: [OMS, signos de peligro IMCI](https://www.who.int/publications/i/item/WHO-MCA-19.02),
[OMS, atención del niño crítico](https://www.ncbi.nlm.nih.gov/books/NBK350532/) y
[NICE NG143, fiebre en menores de cinco años](https://www.nice.org.uk/guidance/ng143/chapter/recommendations).

Estas referencias tienen poblaciones y supuestos distintos: reutilizar criterios
como avisos no transfiere la validación de sus protocolos al software. No se calcula
un NEWS2 total ni se agregan puntos de diferentes guías. La lectura de oximetría
requiere considerar calidad del sensor, altitud, oxígeno suplementario y objetivos
prescritos, que este módulo no decide. El embarazo por sí solo no implica urgencia.

## Historia y transferencia entre triaje y consulta

Los valores originales no se reinterpretan al abrir el historial. No se heredan
mediciones de consultas previas como si fueran actuales. Si el profesional marca
que verificó las mediciones de la evaluación asociada para esta visita, puede
reutilizarlas explícitamente; el backend exige que la evaluación sea del mismo
paciente y del día. El aviso guarda `origen_evaluacion_id`. La condición materna de
la atención actual se aplica a esa copia sin reescribir la evaluación original.

Sin reutilización explícita, la atención muestra sus propias mediciones o la falta
de ellas. El FUA identifica aparte la revisión histórica de la evaluación asociada.
Una asociación antigua no sustituye una revisión actual. Los registros previos a
esta migración conservan `NULL`, mostrado como sin revisión de urgencia registrada.

## Casos de regresión

Los tests incluyen datos normales y faltantes; hipoxemia; hipotensión; presión muy
alta con/sin síntomas; taquicardia, bradicardia y ausencia de pulso; FR extrema;
fiebre/hipotermia; síntomas neurológicos; embarazo/puerperio; niño con convulsiones;
lactante febril; datos imposibles; permisos y persistencia. El caso crítico central
usa índice ML bajo con PA 80/50, pulso 160, SpO₂ 75, temperatura 40 y síntomas: debe
mostrar aviso inmediato en pantalla, historial y PDFs, sin consejos de control rutinario.

Las pruebas verifican software y los escenarios declarados; no demuestran
sensibilidad clínica, cobertura de todas las urgencias ni seguridad asistencial.

## Actualización de base existente

```powershell
python -m scripts.migrar_alertas_clinicas
python -m pytest app/tests -q -p no:cacheprovider
```

La migración 004 agrega cuatro columnas JSON opcionales, sin borrar ni clasificar
registros previos. Puede repetirse sin duplicar columnas. Reconstruir frontend y
reiniciar el backend después de actualizar.
