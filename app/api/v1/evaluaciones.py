"""
evaluaciones.py — ENDPOINTS DE EVALUACIONES CARDÍACAS

Estos son los endpoints MÁS IMPORTANTES del sistema.
Aquí es donde el usuario ingresa datos del paciente y obtiene
una predicción de riesgo cardíaca automática.

Rutas:
  POST /api/v1/evaluaciones/                    → Crear evaluación (predicción ML)
  GET  /api/v1/evaluaciones/                    → Listar todas (paginado)
  GET  /api/v1/evaluaciones/by-paciente/{id}    → Historial de un paciente
  GET  /api/v1/evaluaciones/{id}                → Ver una evaluación

⚠️ ORDEN DE RUTAS IMPORTANTE:
  FastAPI procesa rutas en orden. Las rutas ESTÁTICAS (/by-paciente)
  deben ir ANTES de las dinámicas (/{id}), sino FastAPI interpreta
  "by-paciente" como un evaluacion_id y la ruta estática nunca se alcanza.

Autenticación: TODOS requieren token JWT válido.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.evaluacion_service import EvaluacionService
from app.services.reporte_service import ReporteService
from app.schemas.evaluacion import EvaluacionCreate, EvaluacionResponse
from app.exceptions.ml_exceptions import MLException
from app.api.deps import get_current_user

router = APIRouter(prefix="/evaluaciones", tags=["Evaluaciones Cardíacas"])


@router.post("/", response_model=EvaluacionResponse, status_code=status.HTTP_201_CREATED)
def create_evaluacion(
    data: EvaluacionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    REGISTRAR UNA EVALUACIÓN CARDÍACA

    Este es el endpoint principal del sistema.
    Flujo:
      1. Valida que el paciente exista
      2. Ejecuta el modelo de ML con los datos
      3. Guarda el resultado en la BD
      4. Retorna la evaluación con probabilidad y clasificación

    Body JSON:
      {
        "paciente_id": 1,
        "edad": 55,
        "presion_alta": true,
        "colesterol_alto": true,
        "tabaquismo": false,
        "actividad_fisica": true,
        "antecedente_acv": false,
        "diabetes": true,
        "salud_general": 3,
        "dificultad_para_caminar": false
      }

    Retorna 201 con la evaluación completa + predicción ML.
    Retorna 400 si el paciente no existe.
    Retorna 500 si hay error en el modelo ML.
    """
    service = EvaluacionService(db)
    try:
        return service.evaluate(data, current_user["id"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except MLException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error ML: {e}")


@router.get("/", response_model=list[EvaluacionResponse])
def list_evaluaciones(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Listar evaluaciones paginadas (todas, de todos los pacientes).

    Query params:
      - limit: cuántas retornar (default 50)
      - offset: cuántas saltar (para paginación)

    Ejemplo: GET /api/v1/evaluaciones/?limit=10&offset=20
    Retorna las evaluaciones 21-30.
    """
    service = EvaluacionService(db)
    return service.list_all(limit=limit, offset=offset)


# ⚠️ RUTAS ESTÁTICAS ANTES DE LAS DINÁMICAS
# /by-paciente DEBE ir ANTES de /{evaluacion_id}
# Si no, FastAPI interpreta "by-paciente" como un ID y nunca llega aquí.

@router.get("/by-paciente/{paciente_id}", response_model=list[EvaluacionResponse])
def get_evaluaciones_by_paciente(
    paciente_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Obtener HISTORIAL de evaluaciones de un paciente.
    Retorna todas las evaluaciones ordenadas de más reciente a más antigua.

    Útil para ver cómo ha cambiado el riesgo cardíaco del paciente
    a lo largo del tiempo.
    """
    service = EvaluacionService(db)
    return service.get_by_paciente(paciente_id)


@router.get("/{evaluacion_id}", response_model=EvaluacionResponse)
def get_evaluacion(
    evaluacion_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Obtener una evaluación por su ID.
    Retorna 404 si no existe.
    """
    service = EvaluacionService(db)
    evaluacion = service.get_by_id(evaluacion_id)
    if not evaluacion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluación no encontrada")
    return evaluacion


@router.get("/{evaluacion_id}/fua", response_class=Response)
def get_evaluacion_fua_pdf(
    evaluacion_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    DESCARGAR PDF (FORMATO ÚNICO DE ATENCIÓN) DE UNA EVALUACIÓN

    Genera un PDF descargable en tamaño oficio peruano (215x330mm) con:
      - Datos del paciente
      - Datos de la atención y profesional
      - Variables preventivas y factores de riesgo
      - Resultado del modelo + triaje clínico (semáforo de color)
      - Factores detectados, protectores y recomendaciones
      - Sección de firmas para completar a mano

    Respuesta:
      200 → application/pdf (adjunto descargable)
      404 → si la evaluación no existe

    Ejemplo: GET /api/v1/evaluaciones/8/fua
    """
    service = ReporteService(db)
    pdf = service.generar_fua(evaluacion_id)
    if pdf is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluación no encontrada")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="fua_{evaluacion_id}.pdf"'
        },
    )
