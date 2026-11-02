# Guion para exponer el ML, en palabras simples

Este es el documento para preparar lo que vas a decir. Los párrafos entre comillas se pueden leer en voz alta. Debajo de cada uno aparece el archivo que puedes mostrar mientras explicas.

**Para abrir el código en orden:** empieza en `entrenar_modelo.py`, que lleva el título `ARCHIVO 01 de 09`. Al inicio de cada archivo encontrarás su número, qué función mostrar y cuál abrir después. La lista completa está al final de esta guía. Es el orden para explicarlo; los marcadores `EXPO-ML` siguen señalando los pasos concretos del código.

ML significa **aprendizaje automático**: un programa aprende patrones a partir de ejemplos. En nuestro proyecto, primero aprende con datos de una encuesta y después usamos lo aprendido para calcular un puntaje con las respuestas de un paciente.

## 1. Para empezar la exposición

> “Voy a explicar cómo funciona la parte de aprendizaje automático de nuestro sistema. El recorrido es este: registramos al paciente, completamos sus respuestas, el modelo calcula un puntaje y la aplicación muestra y guarda el resultado. Antes de hacer eso, el modelo ya pasó por una etapa de entrenamiento.”

Puedes seguir este orden:

**Aprender con ejemplos → guardar el modelo → recibir las respuestas del paciente → calcular un puntaje → mostrar y guardar el resultado.**

## 2. ¿Cómo aprendió el modelo?

> “Para enseñarle al modelo usamos una tabla con 253 680 registros. Cada registro contiene información de una persona y señala si declaró antecedentes de enfermedad coronaria o infarto. De esa tabla seleccionamos nueve datos, como edad, presión alta y colesterol alto. El programa busca relaciones entre esos datos y la respuesta conocida.”

> “Separamos los registros en dos grupos: 80% para entrenar y 20% para probar el resultado. Comparamos dos métodos, Random Forest y XGBoost. Durante la comparación también hicimos pruebas dentro del grupo de entrenamiento. Según la medida utilizada para elegir, ganó XGBoost, que es el que usa esta entrega.”

> “XGBoost combina muchos árboles de decisión. Podemos imaginar cada árbol como una serie de preguntas sobre los datos. Durante el entrenamiento, el programa aprende qué preguntas y combinaciones le sirven para distinguir los ejemplos. Luego guarda lo aprendido en un archivo.”

**Dónde mostrarlo:** [entrenar_modelo.py](../entrenar_modelo.py), función `main`, comentarios `EXPO-ML E1` a `E6`.

Las líneas clave son:

```python
model.fit(X_train, y_train)
joblib.dump(model, OUTPUT_PATH)
```

`fit` es la orden para aprender con los ejemplos. `joblib.dump` guarda el modelo entrenado. Los nombres `X` e `y` solo son abreviaturas: `X` contiene los nueve datos de entrada e `y` contiene la respuesta conocida.

Este entrenamiento se hace aparte. **Registrar a un paciente no vuelve a entrenar el modelo.** Durante la exposición basta con mostrar el script: ejecutarlo reemplaza el modelo y su ficha guardados.

## 3. Primero registramos al paciente

> “En la aplicación empezamos registrando al paciente: nombre, documento, fecha de nacimiento y los demás datos de su ficha. En este momento solo estamos creando su registro; todavía no se calcula ningún puntaje. Después seleccionamos al paciente y abrimos el formulario de evaluación.”

> “El modelo usa nueve datos: edad, presión alta, colesterol alto, tabaquismo, actividad física, antecedente de ACV, diabetes, percepción de salud general y dificultad para caminar. El nombre y el DNI sirven para identificar a la persona, pero no entran al cálculo.”

**Dónde mostrarlo:** [PacientesPage.jsx](../frontend/src/pages/PacientesPage.jsx) y [ModalTriaje.jsx](../frontend/src/components/triaje/ModalTriaje.jsx). Corresponde a `EXPO-ML 01` y `02`.

Si te preguntan por otros campos: temperatura y saturación aparecen en el formulario, pero no se envían entre las nueve entradas del modelo actual.

## 4. Mandamos las respuestas para que el servidor las procese

> “Cuando presionamos evaluar, la pantalla reúne esas nueve respuestas y el número que identifica al paciente. Envía esa información al servidor, que es la parte del sistema donde trabaja Python. La pantalla espera a que el servidor le devuelva el resultado.”

> “Antes de calcular, el servidor comprueba que el usuario esté autenticado, que los datos tengan el formato permitido y que exista el paciente. Luego un servicio organiza los siguientes pasos: preparar los datos, pedir la predicción y guardar la evaluación.”

**Dónde mostrarlo:**

- [triaje.js](../frontend/src/utils/triaje.js), `construirPayloadEvaluacion`: reúne las respuestas (`03`).
- [evaluaciones.js](../frontend/src/services/evaluaciones.js), `crear`: las envía (`04`).
- [evaluaciones.py](../app/api/v1/evaluaciones.py), `create_evaluacion`: recibe la solicitud (`05`).
- [evaluacion_service.py](../app/services/evaluacion_service.py), `evaluate`: coordina el trabajo (`06`).

Si ves la palabra **API**, aquí significa el punto por el que la pantalla le pide trabajo al servidor. **Payload** es simplemente el paquete de datos que se envía.

## 5. Acomodamos los datos como el modelo los aprendió

> “Las respuestas todavía necesitan una pequeña preparación. Los sí y no se convierten en uno y cero. También se separa el identificador del paciente, porque ese número no sirve para calcular el puntaje.”

> “La edad tiene una conversión especial. El modelo aprendió con grupos de edad, no con los años directamente. Por ejemplo, 55 años pertenecen al grupo de 55 a 59, que está representado con el número 8. Después colocamos los nueve datos en el mismo orden que se usó al entrenar.”

**Dónde mostrarlo:** [evaluacion_mapper.py](../app/mappers/evaluacion_mapper.py), `request_to_model_input` (`07`), y [preprocessor.py](../app/ml/preprocessor.py), `mapear_edad_cdc` y `preprocess` (`09`).

**Mapper** significa que traduce los datos de una forma a otra. **Preprocesar** significa prepararlos antes del cálculo. El resultado es una tabla con una fila y nueve columnas; en el código esa tabla se llama `DataFrame`.

## 6. Recuperamos el modelo que ya estaba entrenado

> “El servidor abre el archivo donde se guardó el modelo y lo deja listo en memoria. Así puede usarlo para calcular. En las siguientes evaluaciones reutiliza el modelo que ya tiene cargado.”

> “También existe una ficha del modelo. Ahí se anota su versión, cómo se entrenó, sus resultados de evaluación y los límites que usamos para separar los niveles bajo, moderado y alto.”

**Dónde mostrarlo:** [model_loader.py](../app/ml/model_loader.py), `load_model` (`08`), y [metadata.py](../app/ml/metadata.py).

El archivo `.joblib` contiene el modelo entrenado. El archivo `_metadata.json` es su ficha. **Metadata** significa información sobre el modelo. Si ves **caché**, aquí solo quiere decir que se conserva lo cargado para reutilizarlo.

En el código real se carga el modelo antes de llamar a `preprocess`; el paso anterior explica la preparación por separado para que se entienda mejor.

## 7. Aquí ocurre el cálculo del modelo

> “Con los datos preparados, ejecutamos el modelo. Este utiliza lo que aprendió durante el entrenamiento y devuelve un puntaje entre cero y uno. En esta parte se hace una predicción; no se vuelve a aprender desde cero.”

**Dónde mostrarlo:** [predictor.py](../app/ml/predictor.py), función `predict`, comentario `EXPO-ML 10`.

La línea principal es:

```python
probabilidad = float(model.predict_proba(df)[0][1])
```

Para explicar esa línea puedes decir:

> “Le entregamos la fila de datos al modelo y tomamos el valor que devuelve para la respuesta positiva, que en los ejemplos de entrenamiento representa haber declarado ese antecedente cardiovascular.”

`[0]` elige la primera fila y `[1]` el valor de la clase positiva. **Inferencia** es el nombre técnico de usar un modelo ya entrenado para calcular un resultado nuevo.

Aunque el campo se llama `probabilidad`, en esta versión lo explicamos como **puntaje o índice**. Un resultado de `0.51` no permite afirmar que esa persona tenga 51% de probabilidad de enfermedad: la escala del modelo actual no está ajustada para esa interpretación clínica.

## 8. Convertimos el puntaje en bajo, moderado o alto

> “Después del cálculo aplicamos una regla para que el número sea más fácil de leer. Si está por debajo de 0.30, lo colocamos en bajo. Desde 0.30 hasta antes de 0.60 es moderado. Desde 0.60 es alto. Estos límites están configurados en la ficha del modelo.”

**Dónde mostrarlo:** [predictor.py](../app/ml/predictor.py), función `_classify` (`11`).

| Puntaje | Nivel que muestra la aplicación |
|---|---|
| Menor de 0.30 | Bajo |
| Desde 0.30 hasta menos de 0.60 | Moderado |
| Desde 0.60 | Alto |

Una precisión para la exposición: el modelo aprendió a distinguir dos respuestas del conjunto de ejemplos. **Los tres niveles los obtiene la aplicación al separar el puntaje con estos límites.**

## 9. Añadimos el color y los textos

> “Una vez obtenido el nivel, el sistema añade el color y las recomendaciones que le corresponden. Esos textos ya están escritos en el código. Por ejemplo, al nivel moderado se le asigna amarillo.”

> “También se muestran las respuestas registradas como factores. Esa lista ayuda a revisar lo ingresado, pero no calcula cuánto aportó cada dato al puntaje.”

**Dónde mostrarlo:** [evaluacion_triaje_service.py](../app/services/evaluacion_triaje_service.py), `generar_triaje_clinico` (`12`).

Para recordarlo: **el modelo calcula el puntaje; las reglas del sistema añaden los textos y colores**. Las recomendaciones y los plazos que aparecen en ellas todavía requieren validación clínica.

## 10. Guardamos la evaluación y mostramos el resultado

> “Finalmente guardamos las respuestas usadas, el puntaje, el nivel, la versión del modelo, la fecha y el usuario que hizo la evaluación. Después el servidor devuelve esa información y la pantalla muestra la tarjeta del resultado.”

> “La evaluación queda en el historial del paciente y se puede generar su reporte en PDF. Si evaluamos otra vez al paciente, se crea otro registro. Guardar esas evaluaciones no modifica automáticamente el modelo.”

**Dónde mostrarlo:**

- [evaluacion_mapper.py](../app/mappers/evaluacion_mapper.py), `create_to_model`: reúne lo que se guardará (`12a`).
- [evaluacion_repository.py](../app/repositories/evaluacion_repository.py), `create`: guarda la evaluación (`13`).
- [evaluacion_mapper.py](../app/mappers/evaluacion_mapper.py), `to_response`: prepara lo que vuelve a la pantalla (`14`).
- [TriajePage.jsx](../frontend/src/pages/TriajePage.jsx) y [TarjetaTriaje.jsx](../frontend/src/components/triaje/TarjetaTriaje.jsx): muestran el resultado (`15`).

La edad se guarda en años; el grupo de edad se utiliza al hacer el cálculo. Consultar el historial o descargar el reporte utiliza la evaluación guardada, sin volver a predecir.

## Un ejemplo para contar mientras haces la demostración

> “Supongamos que evaluamos a una persona de 55 años, con presión alta, colesterol alto y diabetes. Registramos que realiza actividad física, no tiene antecedente de ACV, no registra tabaquismo, señala salud general buena y no tiene dificultad para caminar.”

> “El sistema convierte los 55 años en el grupo 8 y acomoda las nueve respuestas. Con el modelo de esta entrega, ese ejemplo devuelve aproximadamente 0.513. Como está entre 0.30 y 0.60, queda en moderado. Las reglas le asignan amarillo y se guarda la evaluación.”

Si quieres mostrar cómo llegan los datos al cálculo:

```text
Datos en orden: [8, 1, 1, 0, 1, 0, 1, 3, 0]
Puntaje del modelo v2.0.0: 0.513150
Nivel: moderado
Color: amarillo
```

> “Ese número es el índice que calcula el modelo. No significa que hayamos confirmado una enfermedad ni que exista exactamente un 51.3% de probabilidad de tenerla.”

## Si te hacen preguntas

**¿Qué aprendió a reconocer?**

Relaciones entre las nueve características y haber declarado antecedentes de enfermedad coronaria o infarto en la encuesta. No se entrenó para indicar cuándo ocurrirá un infarto.

**¿Por qué eligieron XGBoost?**

Porque obtuvo el mejor resultado en la medida usada para comparar los candidatos durante el entrenamiento. La diferencia con Random Forest fue pequeña.

**¿Qué significa ROC AUC de 0.8403?**

Es una medida de qué tan bien el modelo coloca los ejemplos con antecedente por encima de los que no lo tienen al asignar puntajes. Un valor de 1 sería una separación perfecta y 0.5 corresponde al nivel del azar. **0.8403 no significa 84.03% de aciertos.**

**¿Qué es validación cruzada?**

Es dividir el grupo de entrenamiento en partes para entrenar con unas y comprobar con otra, alternándolas. Ayuda a comparar opciones antes de elegir el modelo.

**¿Aprende con cada paciente nuevo?**

No. La aplicación usa el modelo ya guardado. Para actualizarlo hay que hacer otro entrenamiento, revisarlo y cargar una nueva versión.

**¿El modelo inventa las recomendaciones?**

No. Los textos están escritos en el código y se eligen según el nivel obtenido.

**¿Qué significa el corte F1 que aparece en la ficha?**

Es otro límite que el entrenamiento explora para una decisión de dos opciones. No es el que usamos para los tres colores. El script actual lo elige con los mismos datos de prueba donde luego lo mide; queda pendiente usar datos separados para elegirlo y evaluarlo.

**¿Qué falta mejorar?**

Comprobar mejor las respuestas de entrada, ajustar y evaluar la interpretación del puntaje, revisar los límites de clasificación y validar el sistema con la población donde se quiere utilizar.

## Para cerrar la exposición

> “Este avance muestra que ya podemos conectar el registro del paciente con un modelo entrenado, calcular un índice y conservar el resultado en su historial. Lo presentamos como un prototipo académico de apoyo a la revisión profesional. Todavía necesita validación clínica antes de utilizar sus niveles y recomendaciones para tomar decisiones de atención.”

## Cómo ubicarte en el código

Busca `EXPO-ML` con **Ctrl + Shift + F**. Los marcadores `E1` a `E6` son el entrenamiento; los números `01` a `15` siguen el recorrido dentro de la aplicación. Si un paso lleva una letra, como `12a`, amplía ese mismo paso.

Este es el orden de los nueve archivos que tienen comentarios para la exposición. Encontrarás estos mismos números al inicio de cada uno:

| Orden | Archivo | Qué dices al abrirlo |
|---|---|---|
| 01 | [entrenar_modelo.py](../entrenar_modelo.py) | “Empezamos aquí: el modelo aprende con ejemplos y se guarda.” |
| 02 | [evaluacion.py](../app/schemas/evaluacion.py) | “Aquí definimos qué respuestas debe traer una evaluación.” |
| 03 | [evaluacion_service.py](../app/services/evaluacion_service.py) | “Aquí se organiza todo: comprobar el paciente, calcular y guardar.” |
| 04 | [evaluacion_mapper.py](../app/mappers/evaluacion_mapper.py) | “Aquí elegimos las nueve respuestas que necesita el modelo.” |
| 05 | [model_loader.py](../app/ml/model_loader.py) | “Aquí recuperamos el modelo que ya estaba entrenado.” |
| 06 | [preprocessor.py](../app/ml/preprocessor.py) | “Aquí acomodamos los datos como el modelo los espera.” |
| 07 | [predictor.py](../app/ml/predictor.py) | “Aquí calcula el puntaje y se asigna el nivel.” |
| 08 | [metadata.py](../app/ml/metadata.py) | “Aquí vemos de dónde salen la versión y los límites para cada nivel.” |
| 09 | [evaluacion_triaje_service.py](../app/services/evaluacion_triaje_service.py) | “Aquí se añaden el color y los textos escritos por el equipo.” |

Para terminar, vuelve a `create_to_model` en el archivo 04 y a `evaluate` en el archivo 03: ahí puedes mostrar cómo se reúne el resultado y se pide guardarlo. Después enseña la tarjeta del resultado en la aplicación.
