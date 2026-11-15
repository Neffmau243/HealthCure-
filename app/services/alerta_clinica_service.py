"""Avisos de seguridad: nunca sustituyen una valoración ni diagnostican urgencias.

Referencias y alcance en docs/ALERTAS_CLINICAS.md. No calcula NEWS2, sepsis,
probabilidades, tratamientos ni reclasifica el resultado aprendido por XGBoost.
"""
from app.schemas.clinica import ObservacionesClinicas, AlertaClinica

VERSION_REGLAS = "alertas-1.0.0"
SINTOMAS = {
    "dolor_toracico": "Dolor torácico actual",
    "dificultad_respiratoria": "Dificultad respiratoria actual en reposo",
    "alteracion_conciencia": "Confusión nueva, desmayo o alteración de conciencia",
    "convulsiones": "Convulsiones actuales o recientes sin recuperación completa",
    "deficit_neurologico": "Debilidad súbita, dificultad para hablar o asimetría facial",
    "sangrado_abundante": "Sangrado abundante actual",
    "cefalea_intensa": "Cefalea intensa nueva o persistente",
    "alteraciones_visuales": "Alteraciones visuales nuevas",
    "dolor_abdominal_intenso": "Dolor abdominal intenso persistente",
    "movimientos_fetales_disminuidos": "Disminución de movimientos fetales referida",
    "incapacidad_beber": "Incapacidad para beber o alimentarse",
}
SIGNOS = {
    "presion_sistolica": "Presión sistólica", "presion_diastolica": "Presión diastólica",
    "frecuencia_cardiaca": "Frecuencia cardíaca", "frecuencia_respiratoria": "Frecuencia respiratoria",
    "saturacion_o2": "Saturación de oxígeno", "temperatura_c": "Temperatura",
}


def evaluar_alertas(observaciones: ObservacionesClinicas | None, edad: int,
                    condicion_materna: str | None = None, sexo: str | None = None,
                    edad_meses: int | None = None) -> dict:
    obs = observaciones or ObservacionesClinicas()
    materna = condicion_materna or obs.condicion_materna
    materna = getattr(materna, "value", materna)
    especial = edad < 18 or materna in ("gestante", "puerpera")
    inmediatos, prioritarios = [], []
    faltantes = [label for campo, label in SIGNOS.items() if getattr(obs, campo) is None]
    if obs.sintomas is None:
        faltantes.append("Revisión de síntomas de alarma")
    if sexo == "F" and materna is None:
        faltantes.append("Condición materna")

    for sintoma in dict.fromkeys(obs.sintomas or []):
        clave = getattr(sintoma, "value", sintoma)
        if clave in ("dolor_toracico", "dificultad_respiratoria", "alteracion_conciencia", "convulsiones", "deficit_neurologico", "sangrado_abundante"):
            inmediatos.append(SINTOMAS[clave])
        elif materna in ("gestante", "puerpera") and clave in ("cefalea_intensa", "alteraciones_visuales", "dolor_abdominal_intenso", "movimientos_fetales_disminuidos"):
            inmediatos.append(SINTOMAS[clave])
        elif edad < 18 and clave == "incapacidad_beber":
            inmediatos.append(SINTOMAS[clave])
        else:
            prioritarios.append(SINTOMAS[clave])

    sat, pulso, fr = obs.saturacion_o2, obs.frecuencia_cardiaca, obs.frecuencia_respiratoria
    sist, diast, temp = obs.presion_sistolica, obs.presion_diastolica, obs.temperatura_c
    # Umbral conservador pediátrico de hipoxemia; no se aplican tablas adultas a niños.
    if sat is not None and (sat < 90 if edad < 18 else sat <= 91):
        inmediatos.append(f"Saturación de oxígeno baja: {sat:g}%")
    elif edad >= 18 and sat is not None and sat <= 95:
        prioritarios.append(f"Saturación de oxígeno a revisar: {sat:g}%")
    if pulso == 0 or fr == 0:
        inmediatos.append("Pulso o respiración registrado en cero: confirmar de inmediato y valorar al paciente")
    if edad < 18 and edad_meses is not None and edad_meses < 3 and temp is not None and temp >= 38:
        inmediatos.append(f"Fiebre en lactante menor de 3 meses: {temp:g} °C")

    if edad >= 18:
        if pulso is not None and (pulso <= 40 or pulso > 130):
            inmediatos.append(f"Frecuencia cardíaca extrema: {pulso:g} lpm")
        elif pulso is not None and (pulso <= 50 or pulso >= (100 if materna == "gestante" else 111)):
            prioritarios.append(f"Frecuencia cardíaca a revisar: {pulso:g} lpm")
        if fr is not None and (fr <= 8 or fr >= 25):
            inmediatos.append(f"Frecuencia respiratoria extrema: {fr:g} rpm")
        elif fr is not None and (fr <= 11 or fr >= 21):
            prioritarios.append(f"Frecuencia respiratoria a revisar: {fr:g} rpm")
        if sist is not None and sist <= 90:
            inmediatos.append(f"Presión sistólica baja: {sist:g} mmHg")
        if materna in ("gestante", "puerpera") and sist is not None and (sist >= 160 or diast >= 110):
            inmediatos.append(f"Presión elevada en gestación/puerperio: {sist:g}/{diast:g} mmHg")
        elif sist is not None and (sist >= 180 or diast >= 120):
            sintomas_presion = {"cefalea_intensa", "alteraciones_visuales", "dolor_abdominal_intenso"}
            if sintomas_presion.intersection(obs.sintomas or []):
                inmediatos.append(f"Presión muy elevada con síntomas de alarma: {sist:g}/{diast:g} mmHg")
            else:
                prioritarios.append(f"Presión muy elevada: {sist:g}/{diast:g} mmHg; confirmar y valorar sin demora")
        elif materna in ("gestante", "puerpera") and sist is not None and (sist >= 140 or diast >= 90):
            prioritarios.append(f"Presión elevada en contexto materno: {sist:g}/{diast:g} mmHg")
        if temp is not None and temp <= 35:
            inmediatos.append(f"Temperatura muy baja: {temp:g} °C")
        elif materna in ("gestante", "puerpera") and temp is not None and temp >= 38:
            inmediatos.append(f"Fiebre en gestación/puerperio: {temp:g} °C")
        elif temp is not None and (temp < 36 or temp >= 38.1):
            prioritarios.append(f"Temperatura a revisar: {temp:g} °C")

    if inmediatos:
        nivel, titulo = "inmediata", "Signos de alarma: valoración inmediata"
        accion = "Los datos registrados muestran signos de alarma. Solicitar valoración presencial inmediata y activar el protocolo asistencial local. La atención no debe esperar al resultado del modelo ni aplazarse a un control rutinario."
    elif prioritarios:
        nivel, titulo = "prioritaria", "Hallazgos que requieren valoración prioritaria"
        accion = "Solicitar revisión clínica sin demora y confirmar las mediciones. El profesional debe determinar la prioridad de atención; el índice cardiovascular no justifica aplazarla a una consulta rutinaria."
    elif especial:
        nivel, titulo = "valoracion_especifica", "Requiere valoración pediátrica u obstétrica"
        accion = "Continuar la valoración con el protocolo correspondiente a la edad o condición materna. Los datos disponibles no permiten concluir que el paciente esté estable."
    elif faltantes:
        nivel, titulo = "datos_insuficientes", "Faltan datos para valorar la urgencia"
        accion = "Completar las mediciones y revisar los síntomas de esta visita para apoyar la valoración clínica. La ausencia de datos no permite concluir que el paciente esté estable."
    else:
        nivel, titulo = "sin_criterios_detectados", "Sin señales de alarma en los datos registrados"
        accion = "Continuar la valoración del paciente. Esta revisión de apoyo no descarta enfermedad ni otras urgencias."
    limites = ["Aviso de apoyo; no es un diagnóstico ni un protocolo de triaje validado.",
               "Interpretar oximetría según objetivo prescrito, altitud, calidad de la medición y contexto clínico."]
    if especial:
        limites.append("No se calcula una escala adulta de urgencia para niños, gestantes o puérperas.")
    return AlertaClinica(nivel=nivel, titulo=titulo, accion=accion,
                         motivos=inmediatos + prioritarios, datos_faltantes=faltantes,
                         limitaciones=limites, version_reglas=VERSION_REGLAS).model_dump(mode="json")


def aplicar_alerta_a_triaje(triaje: dict, alerta: dict) -> dict:
    if alerta["nivel"] not in ("inmediata", "prioritaria"):
        return triaje
    return {**triaje, "nivel_alerta": alerta["titulo"],
            "codigo_color": "rojo" if alerta["nivel"] == "inmediata" else "amarillo",
            "accion_sugerida": alerta["accion"], "recomendaciones_medicas": [alerta["accion"], *alerta["motivos"]]}
