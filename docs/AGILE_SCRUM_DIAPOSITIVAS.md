# Guion de presentación académica con Scrum

Propuesta de organización y exposición, actualizada al 15/10/2026. No es evidencia de que hayan ocurrido ceremonias o sprints con determinadas fechas. El relato anterior está en [histórico](historico/AGILE_SCRUM_DIAPOSITIVAS.md).

## 1. Problema y objetivo

HealthCure integra registro de pacientes, un clasificador de perfiles asociados con antecedentes declarados de enfermedad coronaria/infarto y reglas experimentales de priorización. Su propósito es académico, sin validación clínica.

## 2. Alcance funcional demostrado

API FastAPI/MySQL, JWT y roles, pacientes/catálogos, XGBoost v2.0.0, frontend React integrado, historial de evaluaciones y atenciones, resumen diario y PDF académico. El resultado es un índice sin calibrar, no pronóstico ni diagnóstico.

## 3. Incrementos propuestos para organizar el trabajo

| Incremento | Contenido | Evidencia a adjuntar |
|---|---|---|
| Base | Autenticación y pacientes | Demo API y pruebas |
| Gestión | Permisos, catálogos y usuarios | Pruebas de autorización |
| ML | Entrenamiento, comparación y artefactos | Metadata, curvas y código |
| Integración | Formulario, historial, consulta y PDF | Demo del recorrido completo |
| Alineación | Contrato adulto, datos originales y lenguaje académico | Pruebas de regresión y migración |

No asignar fechas o asistentes reales sin registros del equipo. Una secuencia de commits no demuestra por sí misma que se siguió Scrum.

## 4. Roles y eventos que el equipo debe documentar

Identificar Product Owner, Scrum Master y Developers según la organización real. Aportar backlog priorizado, objetivos y duración de sprints, actas de planificación, seguimiento, review y retrospectiva si se afirma haberlos realizado. Si no existe esa evidencia, presentar este apartado como propuesta de aplicación del marco.

## 5. Evidencia del ML

Explicar etiqueta y población; distinguir split, CV y test; consultar métricas en [MODELO_ML](MODELO_ML.md). Distinguir el óptimo F1 exploratorio del artefacto v2 de la [segunda etapa ejecutada](SEGUNDA_ETAPA_EXPERIMENTAL.md), que elige umbrales en validation, evalúa calibración, duplicados, incertidumbre y subgrupos. Mostrar también el recall bajo en jóvenes y los límites de reutilizar el mismo CSV.

## 6. Criterio de terminado para la demo

Recorrido formulario → validación → predicción → persistencia → historial → PDF; backend y pruebas del formulario en verde, lint y build correctos; migración aplicada sin reescribir historial; terminología coherente en interfaz, reporte y documentación.

## 7. Trabajo futuro

Integrar un candidato con bandas/versionado coherentes, estudiar estabilidad y diferencias entre subgrupos; evaluar datos locales y validar profesionalmente las reglas antes de cualquier uso asistencial. El frontend ya está implementado: no presentarlo como fase pendiente.
