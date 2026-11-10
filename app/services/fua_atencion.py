"""FUA final por visita, disponible con o sin evaluación cardiovascular."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether,
)

from app.core.clinica import TIPOS_ATENCION, GRUPOS_ETARIOS, CONDICIONES_MATERNAS
from app.mappers.evaluacion_mapper import EvaluacionMapper
from app.services.alerta_clinica_service import SIGNOS, SINTOMAS


def generar_fua_atencion_pdf(atencion) -> bytes:
    """Los campos de contexto provienen de la visita, nunca de la edad actual."""
    paciente, usuario = atencion.paciente, atencion.usuario
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=(215 * mm, 330 * mm),
        rightMargin=14 * mm, leftMargin=14 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title=f"FUA-AT-{atencion.id:06d}", author=usuario.nombre,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="DatoFua", fontName="Helvetica", fontSize=9, leading=13))
    styles.add(ParagraphStyle(name="NotaFua", fontSize=8, leading=11, textColor=colors.HexColor("#475569")))
    styles["Heading2"].fontSize = 11
    styles["Heading2"].spaceBefore = 12
    styles["Heading2"].spaceAfter = 7

    def texto(value, style="DatoFua"):
        value = "No registrado" if value is None else str(value)
        return Paragraph(escape(value).replace("\n", "<br/>"), styles[style])

    def tabla(filas):
        table = Table([[texto(k), texto(v)] for k, v in filas], colWidths=[51 * mm, 136 * mm], hAlign="LEFT")
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return table

    story = [
        texto("FORMATO ÚNICO DE ATENCIÓN", "Title"),
        texto(f"HealthCure CardioPredict · FUA-AT-{atencion.id:06d}", "NotaFua"),
        Spacer(1, 5 * mm),
        texto("Datos del paciente", "Heading2"),
        tabla([
            ("Paciente", paciente.nombre_completo),
            ("Documento", f"{paciente.tipo_documento} {paciente.documento_identidad}"),
            ("Historia clínica", paciente.numero_historia_clinica),
            ("Seguro", paciente.tipo_seguro),
            ("Sexo registrado", "Femenino" if paciente.sexo == "F" else "Masculino"),
        ]),
        texto("Datos de esta atención", "Heading2"),
        tabla([
            ("Fecha de atención", atencion.created_at.strftime("%d/%m/%Y %H:%M")),
            ("Tipo de atención", TIPOS_ATENCION.get(atencion.tipo_atencion)),
            ("Edad al atender", f"{atencion.edad_al_atender} años" if atencion.edad_al_atender is not None else None),
            ("Grupo etario al atender", GRUPOS_ETARIOS.get(atencion.grupo_etario)),
            ("Condición materna", CONDICIONES_MATERNAS.get(atencion.condicion_materna)),
            ("Profesional responsable", usuario.nombre),
        ]),
    ]
    if atencion.grupo_etario is None:
        story.append(texto("Atención antigua: el contexto no se capturó; no se deduce del estado actual del paciente.", "NotaFua"))
    def bloque_clinico(observaciones, alerta, titulo):
        bloques = [texto(titulo, "Heading2")]
        if alerta:
            aviso = Table([[texto(alerta["titulo"]), texto(alerta["accion"])]], colWidths=[65 * mm,122 * mm])
            fondo = "#ffe4e6" if alerta["nivel"] == "inmediata" else "#fef3c7" if alerta["nivel"] == "prioritaria" else "#f1f5f9"
            aviso.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor(fondo)),("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
            bloques.append(aviso)
            bloques.extend(texto(f"- {motivo}") for motivo in alerta["motivos"])
            if alerta.get("datos_faltantes"):
                bloques.append(texto("Sin registrar: " + ", ".join(alerta["datos_faltantes"]), "NotaFua"))
            bloques.append(texto(f"Reglas: {alerta['version_reglas']}. Aviso de apoyo: no diagnostica ni sustituye el protocolo local.", "NotaFua"))
            if alerta.get("origen_evaluacion_id"):
                bloques.append(texto(f"Mediciones verificadas de evaluación #{alerta['origen_evaluacion_id']} para esta visita.", "NotaFua"))
        else:
            bloques.append(texto("Sin revisión de urgencia registrada. No puede deducirse estabilidad de este registro.", "NotaFua"))
        if observaciones:
            unidades = {"presion_sistolica":"mmHg","presion_diastolica":"mmHg","frecuencia_cardiaca":"lpm","frecuencia_respiratoria":"rpm","saturacion_o2":"%","temperatura_c":"°C","peso_kg":"kg","talla_cm":"cm"}
            bloques.append(tabla([(label, f"{observaciones[campo]:g} {unidades[campo]}" if observaciones.get(campo) is not None else None)
                                  for campo,label in {**SIGNOS,"peso_kg":"Peso","talla_cm":"Talla"}.items()]))
            sintomas = observaciones.get("sintomas")
            bloques.append(texto("Síntomas: " + ("No revisados" if sintomas is None else "; ".join(SINTOMAS[s] for s in sintomas) if sintomas else "Ausencia de los síntomas listados confirmada")))
        return bloques

    story.extend(bloque_clinico(atencion.observaciones_clinicas, atencion.alerta_clinica, "Observaciones y alertas de esta atención"))
    story.extend([
        texto("Acto médico", "Heading2"),
    ])
    # Párrafos independientes permiten paginar incluso textos del máximo permitido.
    for titulo, contenido in [("Diagnóstico", atencion.diagnostico), ("Tratamiento", atencion.tratamiento), ("Indicaciones", atencion.indicaciones)]:
        story.extend([texto(titulo, "Heading3"), texto(contenido)])

    if atencion.evaluacion is not None:
        evaluacion = EvaluacionMapper.to_response(atencion.evaluacion)
        story.extend([
            texto("Evaluación cardiovascular asociada", "Heading2"),
            tabla([
                ("Evaluación", f"#{evaluacion.id} · {evaluacion.created_at.strftime('%d/%m/%Y %H:%M')}"),
                ("Clasificación", evaluacion.clasificacion.value.capitalize()),
                ("Índice de riesgo (0 a 100)", f"{evaluacion.probabilidad * 100:.2f}"),
                ("Versión del modelo", evaluacion.modelo_version),
            ]),
            texto("El índice es un apoyo al profesional; no es una probabilidad clínica ni determina si la atención es de emergencia.", "NotaFua"),
        ])
        triaje = evaluacion.triaje_clinico
        story.extend(bloque_clinico(atencion.evaluacion.observaciones_clinicas, atencion.evaluacion.alerta_clinica, "Revisión registrada en la evaluación asociada"))
        if triaje and evaluacion.alerta_clinica and evaluacion.alerta_clinica.nivel == "sin_criterios_detectados":
            story.extend([texto("Acción sugerida por el tamizaje", "Heading3"), texto(triaje.accion_sugerida)])
            for titulo, valores in [("Factores registrados", triaje.factores_riesgo_detectados), ("Factores protectores", triaje.factores_protectores), ("Recomendaciones del tamizaje", triaje.recomendaciones_medicas)]:
                story.append(texto(titulo, "Heading3"))
                story.extend(texto(f"- {valor}") for valor in (valores or ["Ninguno registrado"]))
    else:
        story.extend([
            texto("Evaluación cardiovascular", "Heading2"),
            texto("Sin evaluación ML asociada. No se ha calculado ni asignado un nivel de riesgo cardiovascular."),
        ])
    story.append(KeepTogether([
        texto("Firmas y conformidad", "Heading2"),
        Spacer(1, 12 * mm),
        tabla([("Profesional de salud", "Firma y sello: __________________________"),
               ("Paciente / apoderado", "Firma: _______________________________")]),
    ]))

    def pie(c, document):
        c.saveState()
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#475569"))
        c.drawString(14 * mm, 11 * mm, f"HealthCure · FUA-AT-{atencion.id:06d}")
        c.drawRightString(201 * mm, 11 * mm, f"Página {document.page}")
        c.restoreState()

    doc.build(story, onFirstPage=pie, onLaterPages=pie)
    return buf.getvalue()
