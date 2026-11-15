# HealthCure — CardioPredict: Representación del Proyecto con Agile Scrum

> Documento de apoyo para diapositivas de presentación. Contenido por diapositiva listo para exponer.

---

## 📍 Diapositiva 01 — Portada

**HealthCure — CardioPredict**
*Sistema web de triaje cardíaco con predicción automática usando Machine Learning, desarrollado bajo metodología Ágil con Scrum*

- Tema: Predicción de riesgo cardíaco + Triaje clínico automático
- Tecnologías: Python · FastAPI · MySQL · Random Forest / XGBoost
- Equipo de desarrollo colaborativo · Ciclo de 4 sprints

---

## 📍 Diapositiva 02 — El Proyecto en una Línea

**¿Qué construimos y por qué?**

- Un médico/técnico de salud ingresa los datos clínicos de un paciente
- El sistema predice el **riesgo cardíaco** con un modelo de ML (Random Forest)
- Y genera automáticamente un **triaje clínico**: nivel de alerta, semáforo de color, factores de riesgo/protectores y recomendaciones médicas
- Se emite un **reporte PDF tipo FUA** (Formato Único de Atención, SIS peruano) listo para imprimir y archivar

```
Paciente → Datos clínicos → Modelo ML → Probabilidad + Clasificación → TRIAJE CLÍNICO → PDF FUA
```

**¿Por qué Scrum?** Porque el proyecto es incremental (backend → seguridad → ML → triaje), tiene requisitos que evolucionan y necesita entregas funcionales cortas.

---

## 📍 Diapositiva 03 — Equipo Scrum

| Miembro | Rol en Scrum | Responsabilidad principal |
|---------|--------------|---------------------------|
| Stakeholder / Clínico | **Product Owner** | Define qué es valioso (triaje accionable para médicos), prioriza el Product Backlog |
| Líder técnico | **Scrum Master** | Garantiza que el marco Scrum funcione, elimina impedimentos |
| Desarrollador Backend | **Developer** | API REST (FastAPI), autenticación, pacientes, evaluaciones, administración |
| Especialista ML | **Developer** | Entrenamiento del modelo, pipeline de predicción, métricas |
| QA / Tester | **Developer** | Pruebas automatizadas (pytest), validación de permisos y de datos |

**Nota clave:** El equipo es **autoorganizado**: cada developer decide *cómo* convertir los ítems del backlog en incrementos.

---

## 📍 Diapositiva 04 — Roles de Scrum

**1. Product Owner (1 persona)**
- Maximiza el valor del producto
- Único responsable del **Product Backlog** y su priorización
- Traduce necesidades clínicas en historias de usuario (ej.: *"como medico, quiero ver el nivel de alerta para saber qué tan urgente es la atención"*)

**2. Scrum Master (1 persona)**
- Facilita las ceremonias (planning, daily, review, retro)
- Elimina bloqueos y protege al equipo de interrupciones
- No es jefe: es un facilitador del proceso ágil

**3. Development Team (grupo autoorganizado)**
- Único responsable de construir el incremento
- Sin sub-roles impositivos: todos contribuyen al mismo objetivo del sprint
- Tamaño típico: 3–9 personas (aquí: 4 developers)

---

## 📍 Diapositiva 05 — Plan de Sprints

**Definición de Sprint:** iteración de producción de 1 a 4 semanas → *incremento de producto potencialmente utilizable*.

| Sprint | Duración | Foco | Entregable al cierre |
|--------|----------|------|----------------------|
| **Sprint 1 — Fundaciones** | 29 ago – 02 sep 2026 | Base del backend, autenticación, pacientes | API REST base funcional |
| **Sprint 2 — Administración y Seguridad** | 02 – 04 sep 2026 | Roles, permisos granulares, catálogos, tests | Módulo admin seguro |
| **Sprint 3 — Machine Learning** | 04 – 05 sep 2026 | Entrenar modelo y exponer predicciones | Predicción de riesgo operativa |
| **Sprint 4 — Triaje Clínico y Reportes** | 05 sep 2026 | Motor de triaje + PDF FUA | Incremento más completo |

Cronología real registrada en el repositorio: `29 ago (init) → 02 sep (admin) → 04 sep (ML) → 05 sep (triaje + FUA)`.

---

## 📍 Diapositiva 06 — Product Backlog (priorizado)

Historias de usuario ordenadas de mayor a menor valor para el negocio clínico:

| ID | Historia de Usuario | Prioridad | Sprint |
|----|----------------------|-----------|--------|
| **HU1** | Como técnico de salud, quiero registrarme e iniciar sesión para usar el sistema | Alta | S1 |
| **HU2** | Como técnico, quiero registrar y buscar pacientes | Alta | S1 |
| **HU3** | Como admin, quiero gestionar usuarios, distritos y localidades | Alta | S2 |
| **HU4** | Como técnico, quiero que solo yo (o el admin) edite mis pacientes | Alta | S2 |
| **HU5** | Como médico, quiero predecir el riesgo cardíaco de un paciente con ML | **Máxima** | S3 |
| **HU6** | Como médico, quiero un triaje automático (alerta, semáforo, recomendaciones) | **Máxima** | S4 |
| **HU7** | Como médico, quiero descargar el reporte PDF en formato FUA | Alta | S4 |
| HU8 | Como usuario, quiero una interfaz web (frontend React) | Media | **Fuera de alcance** (Fase 2) |

> Los ítems HU5 y HU6 son el **corazón diferenciador** del proyecto: pasar de "0.459 → moderado" a "RIESGO MODERADO — SEGUIMIENTO PREVENTIVO (🟡)".

---

## 📍 Diapositiva 07 — Backlog por Sprint (Sprint Backlog)

**Sprint 1** — Fundaciones
- Base de datos MySQL + modelos ORM
- Autenticación JWT + bcrypt
- CRUD de pacientes y endpoints de catálogos
- Swagger UI automático

**Sprint 2** — Administración y Seguridad
- Endpoints de administración de usuarios
- Catálogos gestionables (distritos/localidades)
- Permisos granulares y guards anti-lockout
- Suite de tests con pytest (SQLite en memoria)

**Sprint 3** — Machine Learning
- Entrenar modelo Random Forest (dataset CDC/BRFSS 2015)
- Pipeline preprocessor → model_loader → predictor
- Endpoint `POST /evaluaciones/` con probabilidad + clasificación

**Sprint 4** — Triaje Clínico y Reportes
- Motor determinista de triaje (verde 🟢 / amarillo 🟡 / rojo 🔴)
- Reglas clínicas, factores de riesgo y recomendaciones
- Reporte PDF tipo FUA (oficio peruano)
- Migración SQL y documentación final

---

## 📍 Diapositiva 08 — Reuniones de Scrum

| Ceremonia | Frecuencia | Duración | Qué pasa en HealthCure |
|-----------|------------|----------|------------------------|
| **Sprint Planning** | Inicio de cada sprint | 2–4 h | El equipo selecciona las HU del backlog y define su objetivo de sprint |
| **Daily Scrum** | Diaria | 15 min | ¿Qué hice ayer? ¿Qué haré hoy? ¿Tengo bloqueos? (ej.: dataset pesado de 22 MB, modelo 15.7 MB) |
| **Sprint Review** | Fin de cada sprint | 1–2 h | Demo del incremento al Product Owner (¿se acepta la HU?) |
| **Sprint Retrospective** | Fin de cada sprint | 1 h | Qué funcionó, qué mejorar (ej.: decidir separar rama `ML` de `develop`) |

> Ejemplo real de mejora surgida en retro: crear una **rama dedicada `ML1.2`** para el trabajo de ML y triaje sin romper la rama `develop`. Se ve en el historial de commits del repositorio.

---

## 📍 Diapositiva 09 — Incremento 1 (Sprint 1)

**✅ Incremento 1 — API REST base con Autenticación y Pacientes**

*"Potencialmente utilizable":* ya se podía consumir la API y gestionar pacientes.

| Entregable | Evidencia |
|------------|-----------|
| Backend FastAPI con arquitectura por capas (controller → service → repository) | 30 endpoints en Swagger |
| Registro y login con **JWT + bcrypt** | Token con expiración de 60 min |
| CRUD de pacientes con búsqueda por documento | `GET /pacientes/search` |
| Catálogos base (distritos/localidades) | Dropdowns para formularios |

`GET /health → {"status": "ok", "app": "HealthCure - CardioPredict", "version": "1.0.0"}`

---

## 📍 Diapositiva 10 — Incremento 2 (Sprint 2)

**✅ Incremento 2 — Módulo de Administración con Seguridad Granular**

| Entregable | Evidencia |
|------------|-----------|
| Gestión de usuarios (crear, activar, desactivar) — solo admin | Rollo: `admin` vs `usuario` |
| Gestión de catálogos distritos/localidades | CRUD exclusivo de admin |
| **Guards anti-lockout** | Un admin no puede desactivarse ni degradarse a sí mismo; nadie puede tocar al último admin activo |
| Permisos de edición de pacientes | Solo el creador o un admin edita |
| Suite de pruebas automatizadas | `pytest app/tests` con SQLite en memoria |
| Seed automático de datos de prueba | 3 usuarios, 5 distritos, 15 localidades, 5 pacientes |

Este incremento hizo al sistema **seguro y auditable** — premisa para exponer datos de salud.

---

## 📍 Diapositiva 11 — Incremento 3 (Sprint 3)

**✅ Incremento 3 — Predicción de Riesgo Cardíaco con Machine Learning**

| Entregable | Evidencia |
|------------|-----------|
| Modelo **XGBoost** (comparado con Random Forest vía validación cruzada) | `app/resources/modelo_cardiaco.joblib` + ficha técnica JSON |
| Dataset real **CDC/BRFSS 2015** — 253,680 filas | Indicadores de salud de EE.UU. |
| Métricas del modelo (v2.0.0) | **ROC AUC 84.03% · Recall 81.92% · F1 35.88% · PR AUC 35.37%** |
| Endpoint de evaluación con predicción | `POST /api/v1/evaluaciones/` → probabilidad (0.459) + clasificación ("moderado") |
| Pipeline robusto | preprocessor (valida y ordena columnas) → model_loader (singleton en RAM) → predictor |

**Valor:** el sistema pasa de *gestionar datos* a *predecir el riesgo* con evidencia estadística.

---

## 📍 Diapositiva 12 — Incremento 4 (Sprint 4) ⭐

**✅ Incremento 4 — Triaje Clínico Automático + Reporte PDF (FUA)**

| Entregable | Evidencia |
|------------|-----------|
| **Motor de triaje determinista** — mismos inputs → mismo triaje | `evaluacion_triaje_service.py` |
| Semáforo clínico | 🟢 Bajo · 🟡 Moderado · 🔴 Alto |
| Acciones y recomendaciones médicas | Consulta en 15–30 días, perfil lipídico, monitoreo ambulatorio… |
| **Reporte PDF formato FUA** (oficio peruano 215×330 mm) | Imprimible y archivable |
| Migración SQL para columnas de triaje | `001_triaje_clinico.sql` |

**Ejemplo en vivo:** paciente con presión + colesterol + diabetes → probabilidad 0.459 → `RIESGO MODERADO (🟡) → Programar consulta médica de control en los próximos 15 a 30 días`.

> Con este incremento se cumple la definición de "Done" global: **la predicción ML se convierte en decisión accionable para el personal de salud.**

---

## 📍 Diapositiva 13 — Resumen de los 3+ Incrementos

| # | Incremento | Sprint | Estado |
|---|------------|--------|--------|
| 1 | API REST con autenticación y gestión de pacientes | S1 | ✅ Utilizable |
| 2 | Administración, roles, permisos y tests | S2 | ✅ Utilizable |
| 3 | **Predicción ML** de riesgo cardíaco | S3 | ✅ Utilizable |
| 4 | **Triaje clínico** + **reporte PDF FUA** | S4 | ✅ Utilizable |

Todos los incrementos son **potencialmente utilizables**: cada uno deja funcionalidad probada y desplegable, no prototipos descartables.

---

## 📍 Diapositiva 14 — Conclusiones

1. **Scrum entregó valor incremental:** cada sprint produjo un incremento funcional, probado y utilizable (API → seguridad → ML → triaje clínico).
2. **El MVP quedó operativo:** 30 endpoints, autenticación con roles, permisos granulares, modelo entrenado y motor de triaje determinista.
3. **La priorización del backlog marcó la diferencia:** las historias de mayor valor clínico (ML y triaje) se construyeron al final, cuando la base ya era estable y segura.
4. **Las ceremonias funcionaron en la práctica:** la daily destapó bloqueos (tamaño del dataset, peso del modelo) y la retro impulsó mejoras de proceso como las ramas `ML` y `ML1.2`.
5. **Definición de "Done" bien entendida:** no basta la predicción ML; el producto útil es el **triaje accionable + reporte imprimible** para el personal de salud.
6. **Pendientes futuros (nuevo backlog):** frontend React (Fase 2), Docker/CI-CD, credenciales seguras para producción y análisis de imágenes médicas.

---

## 📍 Diapositiva 15 — Preguntas / Cierre

**"HealthCure — CardioPredict: de la probabilidad estadística a la decisión clínica"**

- ¿Cómo convertir un modelo ML en algo que un enfermero pueda usar? → **Triaje clínico**.
- ¿Cómo mantener la seguridad en datos de salud? → **Roles JWT + guards anti-lockout**.
- ¿Cómo entregar valor rápido en solo una semana? → **Scrum con 4 sprints e incrementos utilizables**.

*Fin de la presentación.*