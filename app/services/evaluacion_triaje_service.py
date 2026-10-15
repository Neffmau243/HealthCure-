"""
evaluacion_triaje_service.py — SERVICIO DE REGLAS CLÍNICAS (TRIAGE)

Traduce el índice no calibrado del modelo ML en información experimental
estructurada y accionable para médicos y enfermeros.

¿POR QUÉ EXISTE?
  Un doctor NO lee "0.459" o "moderado" y sabe qué hacer. Necesita:
    1. NIVEL DE ALERTA → qué tan rápido actuar
    2. CÓDIGO DE COLOR  → semáforo visual (verde/amarillo/rojo)
    3. FACTORES DE RIESGO → antecedentes presentes en los inputs
    4. FACTORES PROTECTORES → qué se está haciendo bien
    5. ACCIÓN SUGERIDA + RECOMENDACIONES → próximos pasos clínicos

DISEÑO:
  - 100% DETERMINISTA: mismos inputs → mismo triaje (fácil de testear)
  - SIN dependencias externas: no toca BD, no toca ML, no toca FastAPI
  - Sin HTML ni estilos: el renderizado (colores, tarjetas) lo hace el frontend
"""
from typing import List


def _normalizar_clasificacion(clasificacion) -> str:
    """Acepta 'bajo' como str o como ClasificacionEnum y devuelve str."""
    return getattr(clasificacion, "value", clasificacion)


def _factores_de_riesgo(data: dict) -> List[str]:
    """
    Identifica los factores de riesgo PRESENTES en los inputs del paciente.

    Solo se listan los que están activos (True), así el médico ve de un
    vistazo qué antecedentes se registraron, sin atribuciones del modelo.
    """
    factores = []

    if data.get("presion_alta"):
        factores.append("Hipertensión Arterial")
    if data.get("colesterol_alto"):
        factores.append("Dislipidemia (Colesterol Alto)")
    if data.get("diabetes"):
        factores.append(etiqueta_diabetes(data.get("estado_diabetes"), True))
    if data.get("tabaquismo"):
        factores.append("Antecedente de haber fumado al menos 100 cigarrillos en la vida")
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
        protectores.append("Actividad física declarada en los últimos 30 días")
    if data.get("tabaquismo") is not None and not data["tabaquismo"]:
        protectores.append("No declara haber fumado 100 cigarrillos en la vida")

    return protectores


def etiqueta_diabetes(estado, agrupado: bool) -> str:
    """No infiere un diagnóstico específico de un booleano histórico."""
    estado = getattr(estado, "value", estado)
    return {
        "ninguna": "Sin prediabetes ni diabetes declarada",
        "prediabetes": "Prediabetes declarada",
        "diabetes": "Diabetes declarada",
    }.get(estado, "Prediabetes o diabetes (sin detalle registrado)" if agrupado
          else "Sin prediabetes ni diabetes declarada")


def _nivel_de_alerta(clasificacion: str, politica=None) -> dict:
    """Bandas experimentales del prototipo; no son un protocolo clínico."""
    niveles = {
        "alto": ("ALTA PRIORIDAD - RIESGO ELEVADO", "rojo",
                 "Revisar el perfil con el profesional responsable; prioridad experimental alta."),
        "moderado": ("RIESGO MODERADO - SEGUIMIENTO PREVENTIVO", "amarillo",
                     "Revisar los antecedentes durante la consulta; prioridad experimental moderada."),
        "bajo": ("BAJO RIESGO - CONTROL DE RUTINA", "verde",
                 "Continuar la evaluación profesional; una banda baja no descarta enfermedad."),
    }
    nivel, color, accion = niveles[clasificacion]
    if politica and politica.get("reglas_version") == "bandas-academicas-3.0.0":
        nivel = {"bajo": "BANDA BAJA - REVISION EXPERIMENTAL",
                 "moderado": "BANDA INTERMEDIA - REVISION EXPERIMENTAL",
                 "alto": "BANDA ALTA - REVISION EXPERIMENTAL"}[clasificacion]
        accion = {
            "bajo": "Revisar los antecedentes; una banda baja no descarta enfermedad.",
            "moderado": "Confirmar los antecedentes y revisar el perfil con el profesional responsable.",
            "alto": "Revisar el perfil y los antecedentes con el profesional; la banda no establece urgencia.",
        }[clasificacion]
    return {
        "nivel_alerta": nivel,
        "codigo_color": color,
        "accion_sugerida": accion,
        "recomendaciones_medicas": [
            "Verificar que los antecedentes registrados estén completos y actualizados.",
            "El profesional determina los estudios, el seguimiento y cualquier tratamiento.",
            "Regla académica sin validación clínica; no determina urgencia ni diagnóstico.",
            *(["El rendimiento varía por edad y sexo; una banda no reemplaza la evaluación profesional."]
              if politica else []),
        ],
    }


def generar_triaje_clinico(data: dict, probabilidad: float, clasificacion, politica=None) -> dict:
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
        # Fallback histórico: jamás aplicar cortes actuales a un score antiguo.
        umbrales = politica["umbrales"] if politica else {"bajo_max": .30, "moderado_max": .60}
        if probabilidad < umbrales["bajo_max"]:
            clasificacion = "bajo"
        elif probabilidad < umbrales["moderado_max"]:
            clasificacion = "moderado"
        else:
            clasificacion = "alto"

    nivel = _nivel_de_alerta(clasificacion, politica)

    return {
        "nivel_alerta": nivel["nivel_alerta"],
        "codigo_color": nivel["codigo_color"],
        "accion_sugerida": nivel["accion_sugerida"],
        "factores_riesgo_detectados": _factores_de_riesgo(data),
        "factores_protectores": _factores_protectores(data),
        "recomendaciones_medicas": nivel["recomendaciones_medicas"],
    }
