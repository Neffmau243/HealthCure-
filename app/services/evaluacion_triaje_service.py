"""
ARCHIVO 09 de 09 | AQUÍ SE GENERAN LOS COLORES, LAS RECOMENDACIONES Y LOS FACTORES DE RIESGO
Vienes de: app/ml/metadata.py (archivo 08).
Muestra generar_triaje_clinico y los mensajes de _nivel_de_alerta.
Para cerrar, vuelve a create_to_model en el archivo 04 y a evaluate en el 03:
ahí se reúne el resultado, se pide guardarlo y se prepara la respuesta.

¿QUÉ HACE ESTE ARCHIVO?
========================
Toma el resultado del modelo (bajo/moderado/alto) y le agrega:
  - El color correspondiente (verde/amarillo/rojo)
  - El texto de alerta
  - La acción sugerida
  - Los FACTORES DE RIEGO detectados en las respuestas del paciente
  - Los FACTORES PROTECTORES detectados
  - Las recomendaciones médicas según el nivel

Los COLORES y los TEXTOS los elige este archivo según el nivel.
Los FACTORES DE RIEGO se arman leyendo las respuestas del paciente:
  Si dijo "Sí" a presión alta → se agrega "Hipertensión Arterial"
  Si dijo "Sí" a diabetes → se agrega "Diabetes Mellitus"
  Y así sucesivamente...

Los FACTORES PROTECTORES son al revés:
  Si hace actividad física → "Realiza Actividad Física Regular"
  Si NO fuma → "No Fumador"

NOTA IMPORTANTE:
  Los factores listan respuestas del paciente, no miden cuánto influyó
  cada una en el puntaje. Son informativos, no explicativos.
"""
from typing import Dict, List


# ====================================================================
# FUNCIÓN auxILIAR: convierte el nivel a texto
# ====================================================================
# A veces llega como ClasificacionEnum.bajo y necesitamos "bajo".
# Esto normaliza el valor para poder compararlo con strings.
def _normalizar_clasificacion(clasificacion) -> str:
    """
    Deja el nivel como texto, por ejemplo bajo, aunque llegue como un Enum.
    """
    return getattr(clasificacion, "value", clasificacion)


# ====================================================================
# FUNCIÓN PRINCIPAL 1: DETECTA LOS FACTORES DE RIESGO
# ====================================================================
# Esta función revisa las respuestas del paciente y arma una lista
# con todas las condiciones de riesgo que dijo tener.
#
# EJEMPLO:
#   Si el paciente respondió:
#     presion_alta=1, colesterol_alto=1, diabetes=1, salud_general=4
#
#   Entonces devuelve:
#     ["Hipertensión Arterial",
#      "Dislipidemia (Colesterol Alto)",
#      "Diabetes Mellitus",
#      "Percepción de Salud General Regular o Mala"]
#
#   Esto NO calcula cuánto influyó cada factor en el puntaje.
#   Solo lista lo que el paciente declaró.
def _factores_de_riesgo(data: dict) -> List[str]:
    """
    Arma una lista con las condiciones de riesgo que aparecen en las respuestas.

    Recibe el diccionario con las respuestas del paciente y revisa cada factor.
    Si la respuesta indica presencia del factor, lo agrega a la lista.

    Factores que detecta:
    - Presión arterial alta
    - Colesterol alto
    - Diabetes
    - Tabaquismo activo
    - Antecedente de ACV
    - Dificultad para caminar
    - Salud general regular o mala (4 o 5 en escala 1-5)
    """
    factores = []

    # --- Hipertensión ---
    # Si el paciente dijo que tiene presión alta (1/True)
    if data.get("presion_alta"):
        factores.append("Hipertensión Arterial")

    # --- Dislipidemia ---
    # Si el paciente dijo que tiene colesterol alto (1/True)
    if data.get("colesterol_alto"):
        factores.append("Dislipidemia (Colesterol Alto)")

    # --- Diabetes ---
    # Si el paciente dijo que tiene diabetes (1/True)
    if data.get("diabetes"):
        factores.append("Diabetes Mellitus")

    # --- Tabaquismo ---
    # Si el paciente dijo que fuma (1/True)
    if data.get("tabaquismo"):
        factores.append("Consumo de Tabaco Activo")

    # --- Antecedente de ACV ---
    # Si el paciente dijo que tuvo un ACV (1/True)
    if data.get("antecedente_acv"):
        factores.append("Antecedente de Accidente Cerebrovascular (ACV)")

    # --- Dificultad para caminar ---
    # Si el paciente dijo que tiene dificultad para caminar (1/True)
    if data.get("dificultad_para_caminar"):
        factores.append("Dificultad para Caminar (Movilidad Reducida)")

    # --- Salud general regular o mala ---
    # En la escala del modelo: 1 = excelente, 5 = mala
    # Si el paciente respondió 4 o 5, se considera salud general regular o mala
    # El valor por defecto es 3 (neutral) por si no llegó la respuesta
    if data.get("salud_general", 3) >= 4:
        factores.append("Percepción de Salud General Regular o Mala")

    return factores


# ====================================================================
# FUNCIÓN PRINCIPAL 2: DETECTA LOS FACTORES PROTECTORES
# ====================================================================
# Esta función es la contraparte de la anterior.
# Busca las respuestas del paciente que se consideran PROTECTORAS
# para el corazón.
#
# EJEMPLO:
#   Si el paciente respondió:
#     actividad_fisica=1, tabaquismo=0
#
#   Entonces devuelve:
#     ["Realiza Actividad Física Regular", "No Fumador"]
#
#   Nuevamente: no mide cuánto reducen el puntaje, solo lista lo positivo.
def _factores_protectores(data: dict) -> List[str]:
    """
    Lista las respuestas que estas reglas consideran protectoras.

    Revisa si el paciente hace actividad física o no fuma.
    Si cumple alguna de estas condiciones, lo agrega a la lista.

    Factores que detecta:
    - Actividad física regular
    - No fumador
    """
    protectores = []

    # --- Actividad física regular ---
    # Si el paciente dijo que hace actividad física (1/True)
    if data.get("actividad_fisica"):
        protectores.append("Realiza Actividad Física Regular")

    # --- No fumador ---
    # Si el paciente dijo que NO fuma (0/False)
    # Ojo: acá se invierte la lógica — buscamos el valor FALSO
    if not data.get("tabaquismo"):
        protectores.append("No Fumador")

    return protectores


# ====================================================================
# FUNCIÓN PRINCIPAL 3: ELIGE LOS TEXTOS Y EL COLOR SEGÚN EL NIVEL
# ====================================================================
# Esta función toma el nivel (bajo/moderado/alto) y devuelve:
# - El texto de alerta
# - El color correspondiente
# - La acción sugerida
# - Las recomendaciones médicas
#
# Los textos están ESCRITOS POR EL EQUIPO, no los inventa el modelo.
# Cada nivel tiene sus propias recomendaciones médicas.
def _nivel_de_alerta(clasificacion: str) -> dict:
    """
    Elige los textos y el color que corresponden al nivel recibido.

    Recibe:
    - clasificacion: "bajo", "moderado" o "alto"

    Retorna un diccionario con:
    - nivel_alerta: texto descriptivo del nivel
    - codigo_color: "verde", "amarillo" o "rojo"
    - accion_sugerida: qué hacer según el nivel
    - recomendaciones_medicas: lista de recomendaciones específicas
    """

    # ================================================================
    # NIVEL ALTO → ROJO → URGENCIA
    # ================================================================
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

    # ================================================================
    # NIVEL MODERADO → AMARILLO → SEGUIMIENTO
    # ================================================================
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

    # ================================================================
    # NIVEL BAJO → VERDE → CONTROL DE RUTINA
    # ================================================================
    # Este es el caso por defecto (else) — si no es alto ni moderado, es bajo.
    else:
        return {
            "nivel_alerta": "BAJO RIESGO - CONTROL DE RUTINA",
            "codigo_color": "verde",
            "accion_sugerida": (
                "Mantener seguimiento preventivo; acordar con el profesional de salud "
                "la fecha del próximo control."
            ),
            # Estos textos son reglas escritas por el equipo, no resultados que el modelo
            # haya aprendido. Alcance y referencias: docs/TRIAGE_CLINICO.md, sección 6.2.
            # Un índice bajo no decide por sí solo cuándo debe ser el próximo control.
            "recomendaciones_medicas": [
                "Revisar con el profesional de salud los antecedentes y las mediciones "
                "disponibles, aunque el índice se encuentre en la banda baja.",
                "Mantener actividad física regular, adaptada a la capacidad del paciente "
                "y a las indicaciones del profesional de salud.",
                "Favorecer una alimentación variada con frutas y verduras, moderar la sal "
                "y evitar el consumo de tabaco.",
                "Acordar la fecha del próximo control según los antecedentes y la evaluación "
                "clínica; actualizar los datos si cambian los hábitos o el estado de salud.",
                "La banda baja no descarta enfermedad ni evalúa los síntomas actuales. "
                "Si aparecen molestias, solicitar valoración profesional sin esperar "
                "a la siguiente evaluación del sistema.",
            ],
        }


# ====================================================================
# FUNCIÓN PRINCIPAL 4: GENERA EL TRIAJE CLÍNICO COMPLETO
# ====================================================================
# Esta es la función que une TODO:
#   - El nivel (bajo/moderado/alto) que calculó el predictor
#   - Los factores de riesgo del paciente
#   - Los factores protectores del paciente
#   - El color y las recomendaciones según el nivel
#
# Devuelve un diccionario con todo lo que se guarda en MySQL y se muestra
# en el frontend.
def generar_triaje_clinico(data: dict, probabilidad: float, clasificacion) -> dict:
    """
    Junta el color, la acción sugerida, los factores y las recomendaciones.

    Recibe:
    - data: respuestas del paciente (las 9 preguntas)
    - probabilidad: puntaje del modelo (ej: 0.787930)
    - clasificacion: nivel del predictor (bajo/moderado/alto)

    Retorna un diccionario con:
    - nivel_alerta, codigo_color, accion_sugerida
    - factores_riesgo_detectados, factores_protectores
    - recomendaciones_medicas
    """
    # Normalizar el nivel por si llegó como Enum en vez de string
    clasificacion = _normalizar_clasificacion(clasificacion)

    # Si el nivel llegó con un valor desconocido, lo recalculamos del puntaje.
    # Este respaldo usa 0.30/0.60 escritos aquí: cambiar la ficha del modelo
    # no cambia estos dos valores.
    if clasificacion not in ("bajo", "moderado", "alto"):
        if probabilidad < 0.30:
            clasificacion = "bajo"
        elif probabilidad < 0.60:
            clasificacion = "moderado"
        else:
            clasificacion = "alto"

    # Obtener los textos, color y recomendaciones según el nivel
    nivel = _nivel_de_alerta(clasificacion)

    # Armar el resultado final con todo junto
    return {
        # Textos y color según el nivel
        "nivel_alerta": nivel["nivel_alerta"],
        "codigo_color": nivel["codigo_color"],
        "accion_sugerida": nivel["accion_sugerida"],

        # Factores detectados en las respuestas del paciente
        "factores_riesgo_detectados": _factores_de_riesgo(data),
        "factores_protectores": _factores_protectores(data),

        # Recomendaciones médicas según el nivel
        "recomendaciones_medicas": nivel["recomendaciones_medicas"],
    }
