"""
ARCHIVO 03 de 09 | Quién organiza toda la evaluación.
Vienes de: app/schemas/evaluacion.py (archivo 02).
Muestra evaluate(): comprueba el paciente y pide preparar, calcular y guardar.
Después abre: app/mappers/evaluacion_mapper.py (archivo 04).

Aquí se organiza el recorrido completo de una evaluación.

Este servicio comprueba que exista el paciente y pide a cada archivo su parte:
el mapper prepara los datos, el predictor calcula y el repositorio guarda.
Al final prepara el resultado para devolverlo a la pantalla.
"""
from datetime import date
from sqlalchemy.orm import Session
from typing import Optional
from app.repositories.evaluacion_repository import EvaluacionRepository
from app.repositories.paciente_repository import PacienteRepository
from app.schemas.evaluacion import (
    ClasificacionEnum,
    EvaluacionCreate,
    EvaluacionResponse,
    ResumenEvaluaciones,
)
from app.mappers.evaluacion_mapper import EvaluacionMapper
from app.exceptions.ml_exceptions import MLException
from app.core.clinica import calcular_edad


class EvaluacionService:
    """
    Coordina las evaluaciones y las consultas de su historial.
    """

    def __init__(self, db: Session):
        self.evaluacion_repo = EvaluacionRepository(db)
        self.paciente_repo = PacienteRepository(db)

    def evaluate(self, data: EvaluacionCreate, usuario_id: int) -> EvaluacionResponse:
        """
        Hace una evaluación nueva en este orden:
        1. Comprueba que exista el paciente.
        2. Pide al mapper las nueve respuestas para el modelo.
        3. Pide al predictor el puntaje, el nivel y la versión.
        4. Reúne los datos y añade los textos del triaje.
        5. Guarda la evaluación y prepara lo que se enviará a la pantalla.
        """

        # EXPO-ML 06 | Primero comprobamos que el paciente esté registrado.
        # Usamos la edad enviada; aquí no se calcula desde su fecha de nacimiento.
        paciente = self.paciente_repo.get_by_id(data.paciente_id)
        if not paciente:
            raise ValueError("Paciente no encontrado")
        if data.edad < 18 or calcular_edad(paciente.fecha_nacimiento) < 18:
            raise ValueError("El modelo de riesgo solo aplica desde los 18 años. Registra la atención sin evaluación ML.")
        if data.observaciones_clinicas and data.observaciones_clinicas.condicion_materna in ("gestante", "puerpera") and paciente.sexo != "F":
            raise ValueError("La condición materna requiere sexo femenino registrado")

        # Seguimos en request_to_model_input: elegimos las nueve respuestas (EXPO-ML 07).
        model_input = EvaluacionMapper.request_to_model_input(data)

        # Ahora pedimos el cálculo: EXPO-ML 08 a 11.
        # Importamos el predictor cuando se necesita evaluar. El archivo del modelo
        # se abrirá dentro de load_model(). Aquí avisamos si falta una dependencia o
        # si el cálculo reporta un error de ML; otros errores de programación se dejan ver.
        try:
            from app.ml.predictor import predict as ml_predict
            prediction = ml_predict(model_input)
        except (ImportError, MLException) as e:
            raise MLException(f"Modelo ML no disponible: {e}")

        # Si falló el cálculo, el recorrido se detuvo antes de llegar aquí.
        # EXPO-ML 12: reunimos el resultado con los textos y los datos del paciente.
        evaluacion_data = EvaluacionMapper.create_to_model(
            data=data,
            prediction=prediction,
            usuario_id=usuario_id,
            edad_actual=calcular_edad(paciente.fecha_nacimiento),
            sexo=paciente.sexo,
        )

        # EXPO-ML 13 | Pedimos al repositorio que guarde la evaluación.
        evaluacion = self.evaluacion_repo.create(**evaluacion_data)

        # EXPO-ML 14 | Preparamos la respuesta para que la pantalla pueda mostrarla.
        return EvaluacionMapper.to_response(evaluacion)

    def get_by_id(self, evaluacion_id: int) -> Optional[EvaluacionResponse]:
        """
        Busca una evaluación por su número. Devuelve None si no existe.
        """
        evaluacion = self.evaluacion_repo.get_by_id(evaluacion_id)
        if not evaluacion:
            return None
        return EvaluacionMapper.to_response(evaluacion)

    def get_by_paciente(self, paciente_id: int) -> list[EvaluacionResponse]:
        """
        Busca las evaluaciones guardadas de un paciente y prepara su historial.
        """
        evaluaciones = self.evaluacion_repo.get_by_paciente(paciente_id)
        return [EvaluacionMapper.to_response(e) for e in evaluaciones]

    def list_all(self, limit: int = 50, offset: int = 0) -> list[EvaluacionResponse]:
        """
        Trae una parte de la lista de evaluaciones, según el límite y desde dónde seguir.
        """
        evaluaciones = self.evaluacion_repo.list_all(limit=limit, offset=offset)
        return [EvaluacionMapper.to_response(e) for e in evaluaciones]

    def resumen(self) -> ResumenEvaluaciones:
        """
        Cuenta las evaluaciones para los indicadores de la pantalla.
        El conteo se hace sobre los registros de la base, no sobre una lista recortada
        que haya cargado el navegador. Así no se pierden casos al pasar de 200.
        También devuelve los pacientes evaluados hoy para armar la lista de pendientes.
        Un paciente evaluado otro día puede volver a estar pendiente hoy.
        """
        # Contamos los registros de hoy y de cada nivel directamente en la base.
        hoy = date.today().isoformat()
        conteo = self.evaluacion_repo.contar_por_clasificacion()
        return ResumenEvaluaciones(
            total_evaluaciones=self.evaluacion_repo.contar(),
            total_hoy=self.evaluacion_repo.contar_hoy(hoy),

            por_clasificacion={
                nivel.value: conteo.get(nivel.value, 0) for nivel in ClasificacionEnum
            },
            pacientes_evaluados_hoy=self.evaluacion_repo.pacientes_evaluados_hoy(hoy),
        )
