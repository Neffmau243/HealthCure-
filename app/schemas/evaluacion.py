"""
ARCHIVO 02 de 09 | Qué respuestas necesita una evaluación.
Vienes de: entrenar_modelo.py (archivo 01).
Muestra EvaluacionCreate: el número del paciente y las nueve respuestas.
Después abre: app/services/evaluacion_service.py (archivo 03).

Aquí se define qué datos debe tener cada mensaje de una evaluación.

EvaluacionCreate describe lo que recibimos de la pantalla.
PredictionResult reúne lo que devuelve el predictor dentro del servidor.
EvaluacionResponse describe el resultado completo que vuelve a la pantalla.
Pydantic usa estas clases para revisar los tipos y los límites indicados.
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from app.schemas.clinica import ObservacionesClinicas, AlertaClinica


class ClasificacionEnum(str, Enum):
    """
    Los tres nombres permitidos para el nivel: bajo, moderado y alto.
    El predictor elige uno según el puntaje y los límites de la ficha.
    Habitualmente: menos de 0.30 es bajo, de 0.30 a menos de 0.60 moderado
    y desde 0.60 alto. No representan porcentajes clínicos comprobados.
    """
    bajo = "bajo"
    moderado = "moderado"
    alto = "alto"


# EXPO-ML 05a | Revisamos cómo deben llegar los datos desde la pantalla.
# Los campos omitidos pueden recibir valores predeterminados; revisar el formato
# no demuestra que la respuesta describa realmente el estado del paciente.
class EvaluacionCreate(BaseModel):
    """
    Describe los datos que se reciben al pedir una evaluación.
    Incluye el número del paciente y las nueve respuestas para calcular.
    La edad es obligatoria. Si faltan los campos sí/no, se toma False;
    si falta salud_general, se toma 3. Eso no prueba que se hayan respondido.
    """
    paciente_id: int

    # La edad llega en años. Aquí se permiten 1 a 120; este límite no bloquea menores.
    edad: int = Field(..., ge=1, le=120)

    presion_alta: bool = False
    colesterol_alto: bool = False
    tabaquismo: bool = False
    actividad_fisica: bool = False
    antecedente_acv: bool = False
    diabetes: bool = False

    # 1=excelente, 2=muy buena, 3=buena, 4=regular, 5=mala.
    salud_general: int = Field(3, ge=1, le=5)

    dificultad_para_caminar: bool = False
    observaciones_clinicas: Optional[ObservacionesClinicas] = None


class TriajeClinico(BaseModel):
    """
    Reúne los textos, listas y color que se muestran junto al resultado.
    Por ejemplo, codigo_color=amarillo y una lista de recomendaciones.
    Aquí solo se define su forma; los textos se eligen en el servicio de triaje.
    """
    nivel_alerta: str
    codigo_color: str
    accion_sugerida: str
    factores_riesgo_detectados: list[str]
    factores_protectores: list[str]
    recomendaciones_medicas: list[str]


class EvaluacionResponse(BaseModel):
    """
    Describe la evaluación completa que enviamos a la pantalla.
    Contiene quién fue evaluado, quién lo evaluó, las respuestas, el puntaje,
    el nivel, la versión del modelo, los textos del triaje y la fecha.
    """
    id: int
    paciente_id: int
    usuario_id: int

    edad: int
    presion_alta: bool
    colesterol_alto: bool
    tabaquismo: bool
    actividad_fisica: bool
    antecedente_acv: bool
    diabetes: bool
    salud_general: int
    dificultad_para_caminar: bool

    probabilidad: float
    clasificacion: ClasificacionEnum
    modelo_version: Optional[str] = None

    triaje_clinico: Optional[TriajeClinico] = None
    observaciones_clinicas: Optional[ObservacionesClinicas] = None
    alerta_clinica: Optional[AlertaClinica] = None

    created_at: datetime

    # Permite construir la respuesta leyendo los datos de un registro guardado.
    model_config = ConfigDict(from_attributes=True)


class ResumenEvaluaciones(BaseModel):
    """
    Reúne las cantidades que muestran los indicadores de la pantalla.
    Incluye total, total de hoy, cantidad por nivel y pacientes evaluados hoy.
    Los conteos vienen de la base completa, no solo de la página de resultados.
    """
    total_evaluaciones: int
    total_hoy: int

    por_clasificacion: dict[str, int]

    # Números de los pacientes evaluados hoy, para saber quiénes siguen pendientes.
    pacientes_evaluados_hoy: list[int]


class PredictionResult(BaseModel):
    """
    Es el resultado que el predictor pasa a los demás archivos del servidor.
    Contiene puntaje, nivel y versión. Después el mapper lo junta con los datos
    del paciente para guardar y construir la respuesta completa.
    """
    probabilidad: float
    clasificacion: ClasificacionEnum
    modelo_version: str
