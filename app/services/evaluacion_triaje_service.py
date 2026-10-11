"""
evaluacion_triaje_service.py — SERVICIO DE REGLAS CLÍNICAS (TRIAGE)

Traduce el resultado probabilístico del modelo ML en información clínica
estructurada y accionable para médicos y enfermeros.

¿POR QUÉ EXISTE?
  Un doctor NO lee "0.459" o "moderado" y sabe qué hacer. Necesita:
    1. NIVEL DE ALERTA → qué tan rápido actuar
    2. CÓDIGO DE COLOR  → semáforo visual (verde/amarillo/rojo)
    3. FACTORES DE RIESGO → por qué dio ese riesgo
    4. FACTORES PROTECTORES → qué se está haciendo bien
    5. ACCIÓN SUGERIDA + RECOMENDACIONES → próximos pasos clínicos

DISEÑO:
  - 100% DETERMINISTA: mismos inputs → mismo triaje (fácil de testear)
  - SIN dependencias externas: no toca BD, no toca ML, no toca FastAPI
  - Sin HTML ni estilos: el renderizado (colores, tarjetas) lo hace el frontend
"""
from typing import Dict, List


def _normalizar_clasificacion(clasificacion) -> str:
    """Acepta 'bajo' como str o como ClasificacionEnum y devuelve str."""
    return getattr(clasificacion, "value", clasificacion)


def _factores_de_riesgo(data: dict) -> List[str]:
    """
    Identifica los factores de riesgo PRESENTES en los inputs del paciente.

    Solo se listan los que están activos (True), así el médico ve de un
    vistazo QUÉ disparó el riesgo.
    """
    factores = []

    if data.get("presion_alta"):
        factores.append("Hipertensión Arterial")
    if data.get("colesterol_alto"):
        factores.append("Dislipidemia (Colesterol Alto)")
    if data.get("diabetes"):
        factores.append("Diabetes Mellitus")
    if data.get("tabaquismo"):
        factores.append("Consumo de Tabaco Activo")
    if data.get("antecedente_acv"):
        factores.append("Antecedente de Accidente Cerebrovascular (ACV)")
    if data.get("dificultad_para_caminar"):
        factores.append("Dificultad para Caminar (Movilidad Reducida)")
    if data.get("salud_general", 3) >= 4:
        # salud_general: 1=excelente ... 5=mala. 4-5 = regular/mala
        factores.append("Percepción de Salud General Regular o Mala")

    return factores


def _factores_protectores(data: dict) -> List[str]:
    """
    Identifica hábitos que REDUCEN el riesgo cardiovascular.
    Refuerzan lo que el paciente debe seguir haciendo.
    """
    protectores = []

    if data.get("actividad_fisica"):
        protectores.append("Realiza Actividad Física Regular")
    if not data.get("tabaquismo"):
        protectores.append("No Fumador")

    return protectores


def _nivel_de_alerta(clasificacion: str) -> dict:
    """
    Define nivel_alerta, codigo_color, accion_sugerida y recomendaciones
    según la clasificación de riesgo del modelo ML.

    codigo_color es SEMÁNTICO ("verde"/"amarillo"/"rojo"), no un hex.
    El frontend decide cómo pintarlo (card, chip, badge...).
    """
    if clasificacion == "alto":
        return {
            "nivel_alerta": "ALTA PRIORIDAD - RIESGO ELEVADO",
            "codigo_color": "rojo",
            "accion_sugerida": (
                "Priorizar atención médica. Evaluación por Cardiología requerida."
            ),
            "recomendaciones_medicas": [
                "Realizar Electrocardiograma (ECG) de base de inmediato.",
                "Solicitar perfil lipídico completo, HbA1c y función renal (Creatinina/Urea).",
                "Evaluar inicio o ajuste de tratamiento antihipertensivo/hipolipemiante.",
            ],
        }
    elif clasificacion == "moderado":
        return {
            "nivel_alerta": "RIESGO MODERADO - SEGUIMIENTO PREVENTIVO",
            "codigo_color": "amarillo",
            "accion_sugerida": (
                "Programar consulta médica de control en los próximos 15 a 30 días."
            ),
            "recomendaciones_medicas": [
                "Solicitar perfil lipídico y examen de glucosa en ayunas.",
                "Monitoreo ambulatorio de presión arterial durante 1 semana.",
                "Reforzar cambios en el estilo de vida (dieta cardioprotectora).",
            ],
        }
    else:  # bajo
        return {
            "nivel_alerta": "BAJO RIESGO - CONTROL DE RUTINA",
            "codigo_color": "verde",
            "accion_sugerida": "Mantener controles anuales de salud preventiva.",
            "recomendaciones_medicas": [
                "Continuar promoviendo la actividad física y hábitos saludables.",
                "Reevaluación de triaje anual o según síntomas.",
            ],
        }


def generar_triaje_clinico(data: dict, probabilidad: float, clasificacion) -> dict:
    """
    Construye la interpretación clínica completa de una evaluación.

    Parámetros:
      data: dict con los inputs del paciente (bools)
            Ej: {"presion_alta": True, "colesterol_alto": True, ...}
      probabilidad: float 0.0-1.0 (reservada como respaldo si la
            clasificación llega con un valor inesperado)
      clasificacion: str o ClasificacionEnum ("bajo", "moderado", "alto")

    Retorna un dict con la estructura triaje_clinico:
      {
        "nivel_alerta": str,
        "codigo_color": "verde"|"amarillo"|"rojo",
        "accion_sugerida": str,
        "factores_riesgo_detectados": [str, ...],
        "factores_protectores": [str, ...],
        "recomendaciones_medicas": [str, ...],
      }
    """
    clasificacion = _normalizar_clasificacion(clasificacion)

    # Respaldo: si la clasificación es desconocida, derivarla de la
    # probabilidad con los mismos umbrales del predictor ML.
    if clasificacion not in ("bajo", "moderado", "alto"):
        if probabilidad < 0.30:
            clasificacion = "bajo"
        elif probabilidad < 0.60:
            clasificacion = "moderado"
        else:
            clasificacion = "alto"

    nivel = _nivel_de_alerta(clasificacion)

    return {
        "nivel_alerta": nivel["nivel_alerta"],
        "codigo_color": nivel["codigo_color"],
        "accion_sugerida": nivel["accion_sugerida"],
        "factores_riesgo_detectados": _factores_de_riesgo(data),
        "factores_protectores": _factores_protectores(data),
        "recomendaciones_medicas": nivel["recomendaciones_medicas"],
    }