"""
ARCHIVO 04 de 09 | Elegimos los datos que entrarán al modelo.
Vienes de: app/services/evaluacion_service.py (archivo 03).
Empieza por request_to_model_input: selecciona las nueve respuestas.
Después abre: app/ml/model_loader.py (archivo 05).
Al terminar el recorrido puedes volver a create_to_model y to_response
para mostrar cómo se reúne lo que se guarda y lo que vuelve a la pantalla.

Aquí traducimos los datos entre la pantalla, el modelo y la base de datos.

Al modelo le damos solo las nueve respuestas que necesita.
Para guardar, reunimos esas respuestas, el resultado y quién hizo la evaluación.
Para responder a la pantalla, acomodamos la evaluación guardada.
Eso significa mapper: pasar información de una forma a otra.
"""
from typing import Optional
from app.schemas.evaluacion import (
    EvaluacionCreate, EvaluacionResponse, PredictionResult, TriajeClinico
)
from app.models.evaluacion import Evaluacion
from app.services.evaluacion_triaje_service import generar_triaje_clinico
from app.services.alerta_clinica_service import evaluar_alertas, aplicar_alerta_a_triaje


class EvaluacionMapper:
    """
    Agrupa las funciones que acomodan los datos para cada paso.
    Se usan directamente, por ejemplo EvaluacionMapper.request_to_model_input(data).
    """

    # EXPO-ML 07 | Elegimos las nueve respuestas; el nombre y el DNI no entran.
    # True/False pasan a 1/0. La edad sigue en años hasta EXPO-ML 09.
    # Después el servicio llama al predictor para recuperar el modelo (08).
    @staticmethod
    def request_to_model_input(data: EvaluacionCreate) -> dict:
        """
        Se queda con las nueve respuestas que utilizará el modelo.
        Convierte sí (True) en 1 y no (False) en 0. Deja fuera el identificador del
        paciente. La edad sigue en años; preprocessor.py la convertirá a su grupo.
        """
        return {
            "edad":                    data.edad,
            "presion_alta":            int(data.presion_alta),
            "colesterol_alto":         int(data.colesterol_alto),
            "tabaquismo":              int(data.tabaquismo),
            "actividad_fisica":        int(data.actividad_fisica),
            "antecedente_acv":         int(data.antecedente_acv),
            "diabetes":                int(data.diabetes),
            "salud_general":           data.salud_general,
            "dificultad_para_caminar": int(data.dificultad_para_caminar),
        }

    # EXPO-ML 14 | Preparamos lo que vuelve a la pantalla con el resultado guardado.
    # Después se muestra en TriajePage.jsx, EXPO-ML 15.
    @staticmethod
    def to_response(evaluacion: Evaluacion) -> EvaluacionResponse:
        """
        Prepara la evaluación guardada para enviarla a la pantalla.
        Incluye respuestas, puntaje, nivel, versión, fecha y textos del triaje.
        Aquí se lee el resultado existente; no se vuelve a pedir una predicción.
        """
        return EvaluacionResponse(
            id=evaluacion.id,
            paciente_id=evaluacion.paciente_id,
            usuario_id=evaluacion.usuario_id,

            edad=evaluacion.edad,
            presion_alta=evaluacion.presion_alta,
            colesterol_alto=evaluacion.colesterol_alto,
            tabaquismo=evaluacion.tabaquismo,
            actividad_fisica=evaluacion.actividad_fisica,
            antecedente_acv=evaluacion.antecedente_acv,
            diabetes=evaluacion.diabetes,
            salud_general=evaluacion.salud_general,
            dificultad_para_caminar=evaluacion.dificultad_para_caminar,

            probabilidad=float(evaluacion.probabilidad),
            clasificacion=evaluacion.clasificacion,
            modelo_version=evaluacion.modelo_version,
            triaje_clinico=EvaluacionMapper._triaje_clinico(evaluacion),
            created_at=evaluacion.created_at,
            observaciones_clinicas=evaluacion.observaciones_clinicas,
            alerta_clinica=evaluacion.alerta_clinica,
        )

    @staticmethod
    def _triaje_clinico(evaluacion: Evaluacion) -> Optional[TriajeClinico]:
        """
        Recupera los textos y colores guardados con la evaluación.
        Si es un registro antiguo sin esos textos, los arma con las reglas actuales.
        Eso no recupera las recomendaciones de la versión antigua ni vuelve a ejecutar
        el modelo: usa el nivel que ya estaba guardado.
        """
        if evaluacion.nivel_alerta is not None:
            return TriajeClinico(
                nivel_alerta=evaluacion.nivel_alerta,
                codigo_color=evaluacion.codigo_color,
                accion_sugerida=evaluacion.accion_sugerida,
                factores_riesgo_detectados=evaluacion.factores_riesgo_detectados or [],
                factores_protectores=evaluacion.factores_protectores or [],
                recomendaciones_medicas=evaluacion.recomendaciones_medicas or [],
            )

        # Este registro antiguo no tiene textos guardados: los armamos con las reglas
        # actuales y su nivel existente. No volvemos a calcular el puntaje.
        triaje = generar_triaje_clinico(
            data={
                "presion_alta": evaluacion.presion_alta,
                "colesterol_alto": evaluacion.colesterol_alto,
                "tabaquismo": evaluacion.tabaquismo,
                "actividad_fisica": evaluacion.actividad_fisica,
                "antecedente_acv": evaluacion.antecedente_acv,
                "diabetes": evaluacion.diabetes,
                "salud_general": evaluacion.salud_general,
                "dificultad_para_caminar": evaluacion.dificultad_para_caminar,
            },
            probabilidad=float(evaluacion.probabilidad),
            clasificacion=evaluacion.clasificacion,
        )
        return TriajeClinico(**triaje)

    @staticmethod
    def create_to_model(
        data: EvaluacionCreate,
        prediction: PredictionResult,
        usuario_id: int,
        edad_actual: int | None = None,
        sexo: str | None = None,
    ) -> dict:
        """
        Reúne lo necesario para guardar una nueva evaluación.
        Junta respuestas, puntaje, nivel, versión y el usuario que la hizo.
        También pide los textos del triaje a evaluacion_triaje_service.py.
        Devuelve estos datos juntos; el repositorio se encarga de guardarlos.
        """

        # EXPO-ML 12a | Pedimos los textos a evaluacion_triaje_service.py (paso 12).
        # Los juntaremos con las respuestas y el resultado para guardarlos.
        triaje = generar_triaje_clinico(
            data={
                "presion_alta":            data.presion_alta,
                "colesterol_alto":         data.colesterol_alto,
                "tabaquismo":              data.tabaquismo,
                "actividad_fisica":        data.actividad_fisica,
                "antecedente_acv":         data.antecedente_acv,
                "diabetes":                data.diabetes,
                "salud_general":           data.salud_general,
                "dificultad_para_caminar": data.dificultad_para_caminar,
            },
            probabilidad=prediction.probabilidad,
            clasificacion=prediction.clasificacion,
        )

        alerta = evaluar_alertas(data.observaciones_clinicas, edad_actual if edad_actual is not None else data.edad, sexo=sexo)
        triaje = aplicar_alerta_a_triaje(triaje, alerta)
        return {
            "paciente_id":             data.paciente_id,
            "usuario_id":              usuario_id,
            "observaciones_clinicas": data.observaciones_clinicas.model_dump(mode="json") if data.observaciones_clinicas else None,
            "alerta_clinica": alerta,

            # Conservamos la edad original en años para el historial; el grupo de edad
            # se utilizó solo al calcular. Aquí también guardamos las otras ocho respuestas.
            "edad":                    data.edad,
            "presion_alta":            data.presion_alta,
            "colesterol_alto":         data.colesterol_alto,
            "tabaquismo":              data.tabaquismo,
            "actividad_fisica":        data.actividad_fisica,
            "antecedente_acv":         data.antecedente_acv,
            "diabetes":                data.diabetes,
            "salud_general":           data.salud_general,
            "dificultad_para_caminar": data.dificultad_para_caminar,

            "probabilidad":            prediction.probabilidad,
            "clasificacion":           prediction.clasificacion,
            "modelo_version":          prediction.modelo_version,

            "nivel_alerta":            triaje["nivel_alerta"],
            "codigo_color":            triaje["codigo_color"],
            "accion_sugerida":         triaje["accion_sugerida"],
            "factores_riesgo_detectados": triaje["factores_riesgo_detectados"],
            "factores_protectores":    triaje["factores_protectores"],
            "recomendaciones_medicas": triaje["recomendaciones_medicas"],
        }
