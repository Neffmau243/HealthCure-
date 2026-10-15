> Auditoría del estado anterior a la implementación. Las correcciones y pruebas posteriores se registran en [AJUSTES_Y_VALIDACION](AJUSTES_Y_VALIDACION.md). Los hallazgos describen el punto de partida.

# Revisión académica de HealthCure / CardioPredict

Fecha: 15 de octubre de 2026. Revisión del estado local del proyecto.

## Dictamen

El proyecto tiene una implementación funcional de ML integrada con una aplicación web. Los documentos explican la instalación, la arquitectura y el flujo de una evaluación, pero no están completamente sincronizados y contienen afirmaciones científicas que deben corregirse antes de una sustentación.

El resultado defendible es un **prototipo académico que clasifica perfiles asociados con antecedentes autodeclarados de enfermedad coronaria o infarto y aplica reglas experimentales de priorización**. La evidencia disponible no permite presentarlo como predictor de eventos futuros, probabilidad clínica individual calibrada ni protocolo de triaje validado.

## Alcance y evidencia ejecutada

Se contrastaron los 11 Markdown existentes con el entrenamiento, el preprocesamiento, el artefacto serializado, la metadata, los contratos de API, los servicios, la persistencia, las rutas y los flujos del frontend, los reportes, el seed y las pruebas. La revisión funcional no equivale a una auditoría exhaustiva de seguridad ni a validación clínica.

| Comprobación | Resultado |
|---|---|
| Suite completa del backend | **76 passed**, 39 advertencias de deprecación de `python-jose`, 21.17 s |
| Modelo real y recorrido HTTP | Incluidos en la suite: predicción, clasificación, persistencia y consulta |
| Frontend: `npm run lint` | Correcto |
| Frontend: `npm run build` | Correcto |
| Modelo incluido | `XGBClassifier`, 400 árboles, profundidad 3, `scale_pos_weight=9.62`, nueve variables |
| Modelo y metadata | Las seis métricas y la matriz de confusión a 0.50 coinciden exactamente a la precisión almacenada |
| Perfil documentado de 55 años | Índice `0.513150`, clasificación `moderado`, versión `2.0.0` |
| Dataset local | 253,680 filas, 22 columnas totales, 23,893 positivos, sin celdas vacías |
| Referencias Markdown a archivos | No se encontraron destinos locales inexistentes en los enlaces revisados; no se verificaron todos los anchors |

No se reentrenó ni sustituyó el modelo. Se reconstruyó la partición con las constantes actuales y se recalcularon las métricas del artefacto existente. No se verificó una instalación limpia ni una base MySQL real; los tests de persistencia usan SQLite en memoria. La comparación RF/XGBoost de CV se revisó en el código y la metadata, sin repetir la búsqueda completa.

La primera comprobación de SciPy encontró un bloqueo transitorio de una DLL por Windows; una ejecución posterior cargó correctamente el modelo. Los tests HTTP se bloquearon dentro del sandbox al crear sockets locales de asyncio y terminaron correctamente al ejecutarlos fuera de esa restricción. No se cambió la configuración de seguridad ni se instalaron paquetes.

## Lo que funciona y está bien planteado

- Separación entre API, servicios, mapper, repositorios y capa ML.
- Uso real del `.joblib`; las nuevas predicciones de la API no son valores simulados.
- Correspondencia del orden y los nombres de las nueve variables entre entrenamiento e inferencia.
- Conversión correcta de años a los 13 códigos CDC para adultos.
- Binarización de diabetes consistente entre entrenamiento y formulario (`>0`).
- Separación explícita entre el clasificador aprendido y los textos deterministas del triaje.
- División estratificada, semilla fija y comparación de dos familias con validación cruzada.
- Métricas apropiadas para estudiar el desbalance, incluyendo average precision, recall, F1 y matrices de confusión.
- Persistencia de inputs, resultado, clasificación y versión; pruebas del modelo real y de permisos.
- Ficha del modelo que reconoce ausencia de calibración y validación local. La tarjeta de resultados y el dashboard ya comunican el valor como índice.

## Hallazgos prioritarios

### 1. La variable objetivo no mide enfermedad futura

**Evidencia:** `docs/MODELO_ML.md:36` dice «tenga o desarrolle enfermedad cardíaca». `entrenar_modelo.py` usa `HeartDiseaseorAttack` de BRFSS 2015. La variable original del CDC registra si la persona declaró antecedentes de enfermedad coronaria o infarto; no proporciona seguimiento temporal ni un horizonte de predicción.

**Implicación:** no se puede defender «riesgo de infarto futuro» o «probabilidad de desarrollar enfermedad» con este experimento. Tampoco cubre cualquier tipo de enfermedad cardíaca.

**Corrección:** definir el objetivo operacional, la etiqueta, la población adulta y la ausencia de horizonte temporal al principio del README y del documento ML. Distinguir clasificación de antecedentes, priorización experimental y pronóstico. [Fuente: codebook CDC 2015, variable `_MICHD`](https://www.cdc.gov/brfss/annual_data/2015/pdf/codebook15_llcp.pdf).

### 2. La API admite evaluaciones fuera de la población prevista y datos incompletos

**Evidencia:** `app/schemas/evaluacion.py:58` permite edades de 1 a 120; siete campos booleanos tienen valor por defecto `False` y salud general tiene valor por defecto 3. `app/ml/preprocessor.py:55` transforma cualquier edad inferior a 25 en el código adulto 18–24.

Se reprodujo `EvaluacionCreate(paciente_id=1, edad=1)` y se obtuvo una predicción `bajo`, índice `0.039937`, sin aportar los demás predictores. Las edades 17 y 18 producen el mismo resultado con esos inputs. La interfaz bloquea menores, pero el backend permite llamadas directas.

**Corrección:** restringir la evaluación ML a adultos en el backend, verificar coherencia con la fecha de nacimiento del paciente y exigir los predictores o representar «desconocido» de forma explícita. No confundir ausencia de respuesta con ausencia de antecedente.

`MODELO_ML.md:180` promete 422 cuando falta una variable: eso no ocurre con los campos opcionales. `MODEL_CARD.md:320` identifica este problema, pero cuenta ocho booleanos; hay siete.

### 3. El score se sigue presentando como probabilidad en parte del producto

**Evidencia:** el Brier recalculado es **0.1714276**, frente a **0.0853211** al predecir siempre la prevalencia del test. En la banda alta, el score medio es **0.7512** y la frecuencia observada de positivos es **0.2716**. Esa diferencia impide interpretar el valor como probabilidad clínica absoluta.

`TarjetaTriaje.jsx` y el dashboard ya muestran «índice de riesgo», pero `app/services/reporte_service.py:326` imprime «Probabilidad: …%» y `frontend/src/pages/ConsultorioPage.jsx:207` muestra el porcentaje. Algunos Markdown también lo presentan como probabilidad de enfermedad.

**Corrección:** unificar la terminología visible como índice o puntuación del modelo, con escala explícita. Si el objetivo académico requiere probabilidades, calibrar con datos separados, reevaluar el Brier y revisar los umbrales. La ponderación de clases puede ser una decisión válida; no valida por sí sola las bandas 0.30/0.60. [Referencia: calibración de probabilidades en scikit-learn](https://scikit-learn.org/stable/modules/calibration.html).

### 4. El umbral óptimo se ajusta sobre el test

**Evidencia:** `entrenar_modelo.py:303` calcula `proba_test`; la línea 304 elige el umbral con `optimizar_umbral(y_test, proba_test)` y la línea 315 evalúa ese umbral sobre el mismo test.

**Implicación:** el F1 óptimo **0.4101** es un resultado exploratorio ajustado a esa muestra, no una evaluación final independiente del umbral. Esto no demuestra que el ROC AUC 0.8403 sea incorrecto: el problema afecta directamente a la selección y evaluación del punto de corte.

**Corrección:** elegir el umbral sobre validación o predicciones fuera de fold del entrenamiento y evaluar una sola vez sobre el test intacto. Maximizar F1 tampoco garantiza una sensibilidad clínica mínima; esa exigencia debe definirse y medirse aparte. [Referencia: evitar decisiones de selección sobre el test](https://scikit-learn.org/stable/common_pitfalls.html).

### 5. Las definiciones de las variables cambian durante el flujo

- **Hipertensión:** el entrenamiento usa antecedente declarado. `frontend/src/utils/triaje.js:101` también activa la variable a partir de una lectura de presión elevada. La variable que llega al modelo cambia de significado respecto de la de entrenamiento. Conviene separar antecedente y medición y documentar cualquier aproximación.
- **Tabaco:** el formulario pregunta correctamente por al menos 100 cigarrillos durante la vida; `evaluacion_triaje_service.py:44` lo convierte en «Consumo de Tabaco Activo». Haber fumado esa cantidad no establece consumo actual. Un valor negativo tampoco demuestra literalmente «No fumador». [Definiciones de tabaco del CDC](https://www.cdc.gov/brfss/annual_data/2015/pdf/codebook15_llcp.pdf).
- **Diabetes:** se agrupan prediabetes y diabetes en un booleano, pero las reglas lo describen como «Diabetes Mellitus». Además, `ModalTriaje.jsx:57` precarga cualquier booleano positivo como diabetes, aunque originalmente se haya seleccionado prediabetes. La agrupación puede servir al modelo, pero no debería cambiar el antecedente clínico mostrado: persistir la respuesta original por separado.

Los comentarios que atribuyen al valor 2 del CSV «prediabetes/embarazo» necesitan contrastarse y corregirse con el diccionario de la versión transformada de Kaggle; no debe confundirse esa codificación con la del cuestionario BRFSS original. La operación `>0` funciona consistentemente en este proyecto, pero pierde las categorías originales.

### 6. Los colores y recomendaciones son reglas experimentales

Los cortes 0.30/0.60 y los textos de acciones se escriben a mano. No hay evidencia de validación de esos cortes o de los plazos y exámenes sugeridos. Que las tres bandas tengan casos no prueba su utilidad clínica.

La model card excluye decisiones de tratamiento o derivación urgente, mientras el servicio genera instrucciones como ECG «de inmediato» y revisión de tratamiento. Para una demo académica deben identificarse como reglas ilustrativas pendientes de validación profesional.

Los factores listados son antecedentes presentes en los inputs, **no explicaciones locales del modelo**. La documentación debe evitar «por qué dio ese riesgo» o «qué disparó el riesgo» como si se hubieran calculado contribuciones por paciente.

### 7. La explicación de la figura de calibración está invertida

**Evidencia:** `scripts/generar_figuras.py:210` y el PNG publicado dicen «Por encima de la diagonal = sobreestima». Con probabilidad predicha en X y fracción observada en Y, la sobreestimación aparece **por debajo** de la diagonal. La curva real está por debajo y los datos son coherentes con sobreestimación.

**Corrección:** arreglar el comentario y el subtítulo y regenerar la figura. No hace falta cambiar el modelo para resolver este error.

### 8. Falta justificar duplicados, independencia y límites de las conclusiones

El CSV local contiene **23,899 filas repetidas completas** respecto de su primera aparición. Al reconstruir el split, **6,405 filas del test** tienen una fila idéntica en train considerando las 22 columnas, incluido el target.

Esto requiere un análisis de sensibilidad con deduplicación o agrupación de perfiles antes de dividir. **No demuestra que sean las mismas personas:** una encuesta discretizada puede contener encuestados distintos con respuestas iguales. Tampoco permite cuantificar cuánto cambia la métrica sin repetir el experimento correspondiente.

Las frases «F1/PR AUC son el techo realista» no se derivan del desbalance. Son resultados de esta configuración, no límites matemáticos demostrados. La pequeña diferencia RF/XGBoost no establece equivalencia estadística; el código elige por ROC AUC, no por parsimonia como afirma la model card.

### 9. Sí se puede hacer parte del análisis por subgrupos

`MODEL_CARD.md:256` y `MODELO_ML.md:571` dicen que no es posible con el contrato actual. Se debe distinguir evaluación offline y monitoreo del despliegue:

- El CSV ya tiene `Sex` y `Age`; pueden usarse para evaluar el test aunque no se incorporen al clasificador.
- La aplicación persiste sexo en pacientes y edad en evaluaciones.
- Las características no disponibles sí requieren recolección adicional.

Como comprobación exploratoria, el ROC AUC fue 0.8152 en códigos de edad 18–39, 0.8399 en 40–59 y 0.7692 en 60+. No constituyen una auditoría formal de equidad; muestran que el cálculo por edad ya es posible. Hacen falta tamaños, prevalencia, sensibilidad, PPV e intervalos por grupo.

### 10. La trazabilidad está iniciada, pero no es completa

La versión se guarda en cada evaluación, lo cual es positivo. Sin embargo, reentrenar sobrescribe los mismos dos archivos, la versión se modifica manualmente y no existe un archivo histórico de artefactos en el flujo. La metadata ausente puede producir silenciosamente versión `1.0.0`.

La frase «toda decisión pasada es reconstruible» de `MODEL_CARD.md:372` es demasiado fuerte. Para sostenerla se necesitan artefactos archivados por versión, hash del modelo y dataset, configuración del split y versión de las reglas. El seed contiene predicciones fijas v1.0.0 y debe identificarse como demo, no como evidencia del modelo actual.

## Métricas verificadas y lectura correcta

| Corte del score | Precision | Recall | F1 | FN | FP |
|---|---:|---:|---:|---:|---:|
| 0.30: moderado o alto | 0.1770 | 0.9188 | 0.2968 | 388 | 20,416 |
| 0.50: referencia binaria | 0.2297 | 0.8192 | 0.3588 | 864 | 13,126 |
| 0.60: banda alta | 0.2716 | 0.7154 | 0.3938 | 1,360 | 9,168 |
| 0.7026: óptimo exploratorio en test | 0.3242 | 0.5581 | 0.4101 | 2,112 | 5,560 |

ROC AUC: **0.8403**. Average precision: **0.3537**, denominada PR AUC en el proyecto; conviene precisar que el código usa `average_precision_score`, no integración trapezoidal de la curva.

La banda baja contiene 388 positivos de 25,929 casos (1.50%); la moderada, 972 de 12,220 (7.95%); la alta, 3,419 de 12,587 (27.16%). Hay señal de discriminación interna. No hay evidencia suficiente para extrapolar esos porcentajes a pacientes locales ni para llamarlos diagnósticos confirmados.

El recall 81.92% corresponde al corte 0.50, **no** al funcionamiento completo del semáforo. Si se interpreta «moderado o alto» como marcado, el recall es 91.88%, con precision 17.70%. La aplicación muestra categorías y recomendaciones; no ejecuta una derivación médica automática.

En `MODEL_CARD.md:70`, «se deja fuera de la banda baja solo al 8.1%» está invertido: el 8.1% de positivos **queda dentro** de la banda baja; el 91.9% queda fuera.

## Evaluación de cada Markdown

| Documento | ¿Cumple su función? | Qué ajustar |
|---|---|---|
| `README.md` | Sí, como puerta de entrada técnica | Incorporar el carácter académico y el objetivo real desde el inicio; unificar índice/probabilidad y aclarar que las reglas no están validadas |
| `frontend/README.md` | Sí | Es claro sobre ejecución y rutas; actualizarlo cuando se corrijan las definiciones clínicas y los límites del formulario |
| `docs/MODELO_ML.md` | Sí, con correcciones científicas importantes | Futuro vs antecedentes, test usado para umbral, 422, techo de métricas, subgrupos, 72 vs 76 tests y lenguaje de probabilidad |
| `docs/MODEL_CARD.md` | Sí, es útil y reconoce límites reales | Corregir selección por parsimonia, equivalencia no demostrada, subgrupos, ocho vs siete booleanos, frase invertida del 8.1% y trazabilidad absoluta |
| `docs/INTEGRACION_ML.md` | Parcialmente | Separar historia de integración y guía vigente; no usar pruebas sintéticas antiguas como evidencia actual; aclarar recarga conjunta de modelo y metadata |
| `docs/TRIAGE_CLINICO.md` | Sí, para explicar el motor de reglas | Mantiene un ejemplo antiguo de score; debe diferenciar antecedentes listados de explicaciones del modelo, y reglas demo de protocolo validado |
| `docs/MAPEO_RUTAS_FRONT_BACK.md` | Parcialmente | Dice Random Forest entrenado y presenta el endpoint de conteo como pendiente aunque `/evaluaciones/resumen` existe y se consume |
| `docs/MAPPEO_BACKEND.md` | Solo como documento histórico | Afirma que el modelo aún no existe, versión 1.0.0; marcar claramente archivo histórico y enlazar documentación vigente |
| `docs/MAPPEO_Y_ESTADO_DEL_PROYECTO.md` | Parcialmente, ya avisa que es histórico | Mezcla datos nuevos con diagramas antiguos, Random Forest, frontend pendiente y tamaño viejo del modelo; evitar presentarlo como estado actual |
| `docs/FUA_PDF.md` | Sí, para la construcción del PDF | Sincronizar etiqueta del score y dependencias; mantener claro que el formato es académico y verificar cualquier afirmación sobre atenciones contra lo que realmente imprime |
| `docs/AGILE_SCRUM_DIAPOSITIVAS.md` | Parcialmente | Contiene Random Forest y frontend en fase futura; separar cronología histórica de estado actual. Los commits no prueban ceremonias, roles o retrospectivas: aportar actas/evidencias o presentarlo como propuesta de organización |

El problema principal de los Markdown es la repetición del estado, algoritmo, métricas y contratos en demasiados lugares. Hay suficiente explicación técnica; falta una fuente de verdad claramente identificada.

## Organización recomendada para la entrega académica

1. **README:** problema, usuarios, alcance académico, recorrido básico, instalación y mapa de lectura.
2. **MODELO_ML:** experimento y evidencia vigente; objetivo, diccionario de datos, particiones, selección, métricas y limitaciones.
3. **MODEL_CARD:** uso previsto, población, interpretaciones permitidas y límites.
4. **Arquitectura/API:** rutas, contratos, permisos y persistencia, evitando repetir métricas.
5. **TRIAGE_CLINICO:** reglas deterministas, origen de cada regla y estado de validación.
6. **Histórico:** mover los relatos de integración y estados anteriores a una sección explícita con fecha.

Para explicar el proyecto como trabajo académico, completar también: pregunta de investigación u objetivo evaluable, justificación de las nueve variables, baseline sencillo, criterios de éxito previos al test, resultados con incertidumbre, bibliografía y relación entre resultados y objetivo. No basta defender el resultado diciendo que el desbalance impide mejorar.

## Orden de corrección sugerido

1. Corregir la definición de la tarea y la terminología del score en documentación, consultorio y PDF.
2. Endurecer edad y presencia de predictores en la API; preservar las categorías clínicas originales.
3. Separar validación y test para el umbral; estudiar duplicados y reportar incertidumbre y subgrupos.
4. Identificar los cortes y recomendaciones como reglas académicas pendientes de validación y corregir la figura de calibración.
5. Sincronizar los Markdown, archivar los históricos y documentar las evidencias académicas.

**Conclusión:** es una base funcional y demostrable para una entrega académica. La implementación del pipeline funciona; la interpretación científica, la calidad del contrato de entrada y la coherencia documental necesitan las correcciones anteriores. No hace falta rehacer todo el proyecto para que su explicación sea rigurosa.
