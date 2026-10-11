# HealthCure — CardioPredict: Reporte PDF (Formato Único de Atención)

> Documento de referencia: cómo el backend genera el PDF tipo FUA con el
> resultado de una evaluación cardíaca. Generado a partir del código fuente
> actual del proyecto.

---

## Tabla de Contenidos

1. [¿Qué genera?](#1-qué-genera)
2. [¿Por qué en el backend?](#2-por-qué-en-el-backend)
3. [Arquitectura](#3-arquitectura)
4. [Endpoint](#4-endpoint)
5. [Estructura del documento](#5-estructura-del-documento)
6. [Cómo se llenan los datos](#6-cómo-se-llenan-los-datos)
7. [Manejo de páginas](#7-manejo-de-páginas)
8. [Dependencias](#8-dependencias)
9. [Ejemplo de uso (Postman)](#9-ejemplo-de-uso-postman)
10. [Tests](#10-tests)

---

## 1. ¿Qué genera?

Un **PDF descargable** con el resultado de una evaluación cardíaca, maquetado
siguiendo la estructura del **FUA (Formato Único de Atención)** del SIS
peruano. Sirve para que médicos y enfermeros **impriman y archiven** la
atención de tamizaje de riesgo cardiovascular.

El documento incluye:

- **Encabezado**: Ministerio de Salud / SIS, N° de FUA, IPRESS, fecha.
- **1. Datos del paciente (asegurado)**: documento, filiación al seguro,
  apellidos y nombres, fecha de nacimiento, edad, sexo, dirección.
- **2. Datos de la atención**: tipo, profesional responsable, finalidad.
- **3. Actividades preventivas y factores de riesgo**: peso, talla, estado
  general y las variables evaluadas (presión, colesterol, tabaquismo, etc.)
  marcadas SI/NO.
- **4. Resultado del tamizaje**: franja de color (verde/amarillo/rojo),
  nivel de alerta, probabilidad, modelo y acción sugerida.
- **5. Factores de riesgo y recomendaciones**: detectados, protectores y
  exámenes/controles sugeridos.
- **6. Firmas y conformidad**: espacio para firma/sello del profesional y
  firma/huella del paciente.

Formato de papel: **oficio peruano (215 x 330 mm)**.

---

## 2. ¿Por qué en el backend?

- No hay frontend todavía (está en "fase 2"), así que el PDF debe poder
  generarse y descargarse sin interfaz.
- El backend ya tiene **todos los datos** (paciente, evaluación, triaje
  clínico): el PDF solo formatea lo que la API ya produce.
- El resultado queda reproducible, testeable y disponible para cualquier
  cliente (Postman, frontend futuro, generador de reportes).

---

## 3. Arquitectura

```
┌──────────────────────────────────────────────────────────────────────┐
│  API ROUTE  app/api/v1/evaluaciones.py                                │
│  GET /api/v1/evaluaciones/{id}/fua → Response(application/pdf)        │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  SERVICE  app/services/reporte_service.py                             │
│  ReporteService(db).generar_fua(evaluacion_id)                        │
│    ├── EvaluacionRepository.get_by_id()   → ORM (con relaciones)      │
│    └── generar_fua_pdf(evaluacion)        → bytes del PDF             │
│         └── EvaluacionMapper.to_response() → triaje (persistido o     │
│              recalculado para evaluaciones antiguas)                  │
└──────────────────────────────────────────────────────────────────────┘
```

**Punto clave:** el PDF usa el **mismo `EvaluacionMapper`** que la API para
obtener el triaje clínico. Así el documento impreso y el JSON de la API
nunca se contradicen, incluso para evaluaciones creadas antes de la feature
de triaje (el mapper recalcula el triaje on-the-fly si las columnas son NULL).

---

## 4. Endpoint

### `GET /api/v1/evaluaciones/{evaluacion_id}/fua`

Requiere **token JWT** (header `Authorization: Bearer <token>`).

| Respuesta | Descripción |
|-----------|-------------|
| **200** | `application/pdf` con `Content-Disposition: attachment; filename="fua_{id}.pdf"` |
| **404** | La evaluación no existe |

Ejemplo:

```bash
curl -H "Authorization: Bearer {{token}}" \
     -o fua.pdf \
     http://localhost:8000/api/v1/evaluaciones/8/fua
```

---

## 5. Estructura del documento

La construcción está en `app/services/reporte_service.py` y se dibuja con
`reportlab.pdfgen.canvas` en coordenadas milimétricas (mm). Los bloques se
maquetan con funciones que reciben un cursor vertical (`cy`) y devuelven el
nuevo cursor, de arriba hacia abajo:

| Función | Bloque |
|---------|--------|
| `_encabezado()` | Título, N° FUA, IPRESS, fecha de atención |
| `_datos_paciente()` | Sección 1 (asegurado) |
| `_datos_atencion()` | Sección 2 (atención + profesional) |
| `_variables()` | Sección 3 (peso, talla, factores SI/NO) |
| `_resultado()` | Sección 4 (franja de color + probabilidad + acción) |
| `_factores()` | Sección 5 (detectados, protectores, exámenes) |
| `_firmas()` | Sección 6 (firma profesional y del paciente) |

Helpers de dibujo reutilizables:

- `_rect()` — rectángulo con borde (opcional con relleno).
- `_texto()` — texto en una posición.
- `_banda_titulo()` — franja gris con el título de cada sección.
- `_campo()` — celda tipo formulario (etiqueta pequeña arriba + valor).
- `_fila_campos()` — una fila de celdas lado a lado.
- `_parrafo()` — texto con quiebre de línea automático (wrap).

---

## 6. Cómo se llenan los datos

| Dato en el PDF | Fuente |
|----------------|--------|
| N° FUA | `FUA-{evaluacion.id:06d}` |
| Nombres / documento / filiación / seguro / dirección | `evaluacion.paciente` (relación ORM) |
| Fecha de atención | `evaluacion.created_at` |
| Profesional responsable | `evaluacion.usuario.nombre` |
| Peso / talla | `paciente.peso_kg`, `paciente.talla_cm` |
| Variables SI/NO | campos bool de la evaluación (`presion_alta`, `diabetes`, ...) |
| Franja de color | `triaje_clinico.codigo_color` → mapa `COLOR_HEX` (verde #67C23A, amarillo #E6A23C, rojo #F56C6C) |
| Nivel de alerta / acción / factores / exámenes | `EvaluacionMapper.to_response(evaluacion).triaje_clinico` |

Los campos que el sistema **no conoce** (colegiatura, sello, huella) quedan
en blanco, como espacios para completar a mano — igual que un FUA físico.

---

## 7. Manejo de páginas

Cada función de dibujo llama a `_salto()` antes de dibujar: si el contenido
no cabe en la página actual (cursor `cy` supera `PIE_MM`), se:

1. Pinta el footer de la página actual.
2. Cierra la página (`showPage()`).
3. Dibuja una cabecera institucional pequeña.
4. Continúa en la página siguiente desde arriba.

Resultado: una evaluación típica (riesgo bajo/moderado) cabe en **1 página**;
una evaluación con muchos factores o recomendaciones largas fluye
automáticamente a **2+ páginas** sin cortarse.

---

## 8. Dependencias

Añadida a `requirements.txt`:

```
reportlab>=4.0.0
```

Se instaló localmente con `pip install "reportlab>=4.0.0"` (versión 5.0.1 en
la máquina de desarrollo).

---

## 9. Ejemplo de uso (Postman)

En la colección `postman/HealthCure_API.postman_collection.json` se agregó el
request **"Descargar FUA en PDF"** (dentro de la carpeta Evaluaciones):

1. Ejecuta "Login Medico" (o Admin) para obtener el token.
2. Ajusta la variable de colección `evaluacion_id` (ej: `1`, `8`, ...).
3. Ejecuta "Descargar FUA en PDF".
4. El test verifica: `200` + `content-type: application/pdf` + header
   `content-disposition: attachment`.

---

## 10. Tests

Cobertura en `app/tests/test_reporte_fua.py`:

| Test | Qué cubre |
|------|-----------|
| `test_genera_pdf_valido` | Header `%PDF-`, tamaño mínimo |
| `test_genera_pdf_para_riesgo_bajo` | Clasificación "bajo" (verde) |
| `test_genera_pdf_para_riesgo_alto` | Clasificación "alto" (rojo) |
| `test_genera_pdf_sin_factores_persistidos` | Evaluación legacy → triaje recalculado |
| `test_endpoint_fua_devuelve_pdf` | API completa: 200 + `application/pdf` |
| `test_endpoint_fua_404_si_no_existe` | 404 para ID inexistente |

Correr:

```bash
python -m pytest app/tests -v
```

---

## Notas

- Los nombres de instituciones (MINSA, SIS) y la estructura del FUA son para
  fines académicos/demo: el proyecto es un MVP y el documento debe validarse
  con el formato oficial vigente antes de uso en producción.
- Si se quiere agregar código CIE-10 o medicamentos reales, se haría en el
  mismo flujo: los datos entrarían por la API y el reporte los formatearía
  sin cambios de arquitectura.