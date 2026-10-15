# Integración vigente del modelo

Actualizado el 15/10/2026. Esta es una guía operativa; la narración previa se conserva como [archivo histórico](historico/INTEGRACION_ML.md). Referencias: [MODELO_ML](MODELO_ML.md), [MODEL_CARD](MODEL_CARD.md).

## Preparación

Instalar dependencias y configurar MySQL como indica el [README](../README.md). El modelo v3.0.0 ya se incluye; no es necesario reentrenarlo para usar la demo.

Para bases existentes, antes de iniciar esta versión:

```bash
python scripts/aplicar_migracion_003.py
python scripts/aplicar_migracion_004.py
```

El script comprueba las columnas y puede repetirse. La alternativa `003_datos_originales_evaluacion.sql` se ejecuta una sola vez. Las migraciones 001/002 solo se necesitan si la base aún no tiene esas estructuras. Una base nueva usa el `schema.sql` actualizado.

## Request

Después de login, consultar `GET /api/v1/pacientes/{id}` y calcular su edad actual (America/Lima). **55 es ilustrativo**: debe reemplazarse por la edad real del paciente elegido. La colección Postman hace ese cálculo en un script previo.

```json
{
  "paciente_id": 1,
  "edad": 55,
  "presion_alta": true,
  "colesterol_alto": true,
  "tabaquismo": false,
  "actividad_fisica": true,
  "antecedente_acv": false,
  "diabetes": true,
  "estado_diabetes": "prediabetes",
  "salud_general": 3,
  "dificultad_para_caminar": false,
  "presion_sistolica": 120,
  "presion_diastolica": 80
}
```

Enviar a `POST /api/v1/evaluaciones/` con JWT. Los nueve predictores son obligatorios. El detalle de diabetes y las dos mediciones son campos adicionales, opcionales para clientes antiguos; se conservan fuera de las nueve features. Prediabetes se agrupa con diabetes para ML, pero mantiene su nombre original en el historial.

## Respuesta y recorrido

201 devuelve inputs, datos originales, `probabilidad` (score de calibración interna), `clasificacion`, versión, `politica_modelo` y `triaje_clinico`. Para el perfil ilustrativo de 55 años: score 0.096616, banda moderada, v3.0.0. El score y las bandas corresponden a la política guardada en `politica_modelo`; no comparar con los índices históricos de v2. La API también exige que la edad corresponda al paciente.

GET por ID y por paciente conservan las nuevas columnas. GET `/evaluaciones/{id}/fua` genera un PDF con índice sobre 100 y advertencia académica. Los textos históricos persistidos se mantienen.

422: datos faltantes/rangos/contradicciones. 400: paciente inexistente, fuera de edad adulta o edad discrepante. 401: sin JWT. 500: fallo de ML.

## Comprobaciones

```bash
python -m pytest app/tests -q
python scripts/generar_figuras.py
cd frontend
npm test
npm run lint
npm run build
```

Tras reemplazar un modelo hay que reiniciar el servidor o invocar **ambas** recargas, modelo y metadata. `uvicorn --reload` no garantiza detectar archivos `.joblib`. No cambiar el artefacto actual solo para corregir los textos de la demo.

## Experimentos posteriores

`python entrenar_modelo.py` ejecuta ahora la [segunda etapa offline](SEGUNDA_ETAPA_EXPERIMENTAL.md), en una carpeta nueva dentro de `experimentos_ml/`. No reemplaza el modelo v2 incluido ni altera evaluaciones. La release integrada incorpora bandas 0.051065/0.210469 y reglas `bandas-academicas-3.0.0`; la v2 está archivada. Ver [integración y generalización](INTEGRACION_V3_Y_GENERALIZACION.md).
