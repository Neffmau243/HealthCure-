"""
reporte_service.py — SERVICIO: GENERACIÓN DE PDF (FORMATO ÚNICO DE ATENCIÓN)

Genera un PDF descargable con el resultado de una evaluación cardíaca,
maquetado siguiendo la estructura del FUA (Formato Único de Atención) del
SIS peruano, para que médicos y enfermeros puedan imprimirlo y archivarlo.

DISEÑO:
  - ReportLab puro → 100% backend, sin frontend ni navegador.
  - Tamaño de papel: OFICIO PERUANO (215 x 330 mm).
  - Todo lo que el sistema conoce (paciente, factores, triaje) se imprime;
    lo que debe llenar el profesional (firma, colegiatura, sello) queda
    como espacio en blanco para completar a mano.
  - Los textos clínicos provienen del MISMO servicio de triaje clínico,
    así el PDF y la API nunca se contradicen.
  - Si el contenido no cabe en una página, se crean páginas adicionales
    automáticamente (con el mismo encabezado institucional).

USO (desde un endpoint):
    pdf_bytes = ReporteService(db).generar_fua(evaluacion_id)
    return Response(content=pdf_bytes, media_type="application/pdf", ...)
"""
from io import BytesIO
from datetime import datetime, date
from typing import Optional, List, Tuple

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from app.models.evaluacion import Evaluacion
from app.models.paciente import Paciente
from app.models.usuario import Usuario
from app.repositories.evaluacion_repository import EvaluacionRepository
from app.mappers.evaluacion_mapper import EvaluacionMapper

# ============================================================
# CONSTANTES DE MAQUETACIÓN (oficio peruano 215 x 330 mm)
# ============================================================
PAGE_W_MM = 215
PAGE_H_MM = 330
MARGEN_MM = 7.0
TOPE_MM = MARGEN_MM + 1.0          # primera línea útil
PIE_MM = PAGE_H_MM - 15.0          # última línea útil (antes del footer)
ANCHO_CONTENIDO = PAGE_W_MM - 2 * MARGEN_MM  # mm útiles por fila

# Colores del semáforo (mismos que usa el frontend por convención)
COLOR_HEX = {
    "verde":    colors.HexColor("#67C23A"),
    "amarillo": colors.HexColor("#E6A23C"),
    "rojo":     colors.HexColor("#F56C6C"),
}

GRIS_LABEL = colors.HexColor("#555555")
GRIS_BANDA = colors.HexColor("#EFEFEF")

# Mapa legible de salud_general (1-5)
SALUD_GENERAL_TEXTO = {
    1: "Excelente",
    2: "Muy buena",
    3: "Buena",
    4: "Regular",
    5: "Mala",
}


def _texto_si_no(valor: bool) -> str:
    return "SI" if valor else "NO"


def _fmt_float(valor) -> str:
    """Convierte Decimal/float a texto limpio (ej: 172.5 → '172.5')."""
    if valor is None:
        return ""
    return f"{float(valor):g}"


# ============================================================
# HELPERS DE DIBUJO (canvas con coordenadas en mm)
# ============================================================
def _salto(c: canvas.Canvas, cy: float, alto_necesario: float) -> float:
    """
    Si no queda espacio suficiente en la página, crea una nueva.
    Devuelve el cy actualizado (arriba de la página nueva si saltó).
    """
    if cy + alto_necesario > PIE_MM:
        _pie_pagina(c, cy)  # pinta footer de la página que se cierra
        c.showPage()
        _cabecera_pagina(c)
        return TOPE_MM
    return cy


def _cabecera_pagina(c: canvas.Canvas) -> None:
    """Pequeña cabecera institucional que se repite en páginas 2+."""
    _texto(c, MARGEN_MM, TOPE_MM, "HealthCure CardioPredict - FUA (Formato Unico de Atencion)",
           size=6.5, color=GRIS_LABEL)


def _pie_pagina(c: canvas.Canvas, cy: float) -> None:
    """Footer estándar de cada página."""
    _texto(c, MARGEN_MM, PAGE_H_MM - 11,
           "Documento generado automaticamente por HealthCure CardioPredict. "
           "El resultado del tamizaje es un apoyo a la decision clinica y no "
           "sustituye el criterio del profesional de salud.", size=6.5, color=GRIS_LABEL)
    _texto(c, MARGEN_MM, PAGE_H_MM - 8.2,
           f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", size=6.5,
           color=GRIS_LABEL)


def _rect(c: canvas.Canvas, x: float, top: float, w: float, h: float,
          fill: Optional[colors.Color] = None, lw: float = 0.5):
    """Dibuja un rectángulo con borde. x/top en mm desde el borde superior."""
    c.setLineWidth(lw)
    c.setStrokeColor(colors.black)
    bottom = (PAGE_H_MM - top - h) * mm
    if fill is not None:
        c.setFillColor(fill)
        c.rect(x * mm, bottom, w * mm, h * mm, stroke=1, fill=1)
    else:
        c.rect(x * mm, bottom, w * mm, h * mm, stroke=1, fill=0)


def _texto(c: canvas.Canvas, x: float, top: float, texto: str, size: float = 9,
           font: str = "Helvetica", color: colors.Color = colors.black):
    """Dibuja texto. top = mm desde el borde superior donde inicia la línea."""
    c.setFont(font, size)
    c.setFillColor(color)
    baseline = (PAGE_H_MM - top) * mm - size * 0.8
    c.drawString(x * mm, baseline, texto)


def _banda_titulo(c: canvas.Canvas, cy: float, titulo: str, h: float = 6.6) -> float:
    """Franja gris de título de sección (con salto de página si no cabe)."""
    cy = _salto(c, cy, h + 1.0)
    _rect(c, MARGEN_MM, cy, ANCHO_CONTENIDO, h, fill=GRIS_BANDA, lw=0.8)
    _texto(c, MARGEN_MM + 2, cy + 0.5, titulo, size=8.5, font="Helvetica-Bold")
    return cy + h + 1.0


def _campo(c: canvas.Canvas, cy: float, x: float, w: float, h: float,
           label: str, valor: str, valor_size: float = 8.5) -> None:
    """Celda tipo formulario: etiqueta pequeña arriba y valor debajo."""
    _rect(c, x, cy, w, h)
    _texto(c, x + 1.5, cy + 1.2, label.upper(), size=5.8, font="Helvetica-Bold",
           color=GRIS_LABEL)
    lineas = simpleSplit(valor, "Helvetica", valor_size, (w - 3) * mm)
    if not lineas:
        lineas = [""]
    y_texto = cy + h - 2.0
    for linea in lineas[:2]:
        _texto(c, x + 1.5, y_texto, linea, size=valor_size)
        y_texto -= 3.4


def _fila_campos(c: canvas.Canvas, cy: float, h: float,
                 campos: List[Tuple[float, float, str, str]]) -> float:
    """
    Dibuja una fila de celdas lado a lado (x, ancho, label, valor).
    Devuelve el cy después de la fila.
    """
    cy = _salto(c, cy, h)
    for x, w, label, valor in campos:
        _campo(c, cy, x, w, h, label, valor)
    return cy + h + 0.7


def _parrafo(c: canvas.Canvas, cy: float, x: float, w: float, texto: str,
             size: float = 8.5, leading: float = 3.4) -> float:
    """Texto con quiebre de línea; devuelve el nuevo cy (con salto de página)."""
    lineas = simpleSplit(texto, "Helvetica", size, w * mm) or [""]
    cy = _salto(c, cy, len(lineas) * leading + 1.0)
    y = cy
    for linea in lineas:
        _texto(c, x, y, linea, size=size)
        y += leading
    return y + 0.5


# ============================================================
# CONSTRUCCIÓN DEL DOCUMENTO
# ============================================================
def _encabezado(c: canvas.Canvas, cy: float, evaluacion: Evaluacion,
                paciente: Paciente, num_fua: str) -> float:
    """Bloque superior: título + N° FUA + IPRESS."""
    alto = 26.0
    _rect(c, MARGEN_MM, cy, ANCHO_CONTENIDO, alto, lw=1.2)

    # Institución
    _texto(c, MARGEN_MM + 3, cy + 3, "MINISTERIO DE SALUD", size=7.5, font="Helvetica-Bold")
    _texto(c, MARGEN_MM + 3, cy + 7.6, "SEGURO INTEGRAL DE SALUD", size=7.5, font="Helvetica-Bold")
    _texto(c, MARGEN_MM + 3, cy + 12.2, "SIS - CardioPredict", size=7, color=GRIS_LABEL)

    # Título central
    _texto(c, MARGEN_MM + 38, cy + 5, "FORMATO UNICO DE ATENCION", size=14, font="Helvetica-Bold")
    _texto(c, MARGEN_MM + 38, cy + 11.5, "FUA - Tamizaje de Riesgo Cardiovascular", size=9, color=GRIS_LABEL)
    _texto(c, MARGEN_MM + 38, cy + 17.5,
           f"N° de Historia Clinica: {paciente.numero_historia_clinica or '-----------'}",
           size=7.5, color=GRIS_LABEL)

    # N° FUA (esquina superior derecha)
    _rect(c, PAGE_W_MM - MARGEN_MM - 52, cy + 2, 49, 11)
    _texto(c, PAGE_W_MM - MARGEN_MM - 51 + 1.5, cy + 3.2, "N° FUA", size=6,
           font="Helvetica-Bold", color=GRIS_LABEL)
    _texto(c, PAGE_W_MM - MARGEN_MM - 51 + 1.5, cy + 7.4, num_fua, size=9,
           font="Helvetica-Bold")

    # Fila: fecha de atención
    _rect(c, PAGE_W_MM - MARGEN_MM - 52, cy + 14.5, 49, 9)
    fecha = evaluacion.created_at
    fecha_txt = fecha.strftime("%d/%m/%Y %H:%M") if isinstance(fecha, datetime) else str(fecha or "")
    _texto(c, PAGE_W_MM - MARGEN_MM - 51 + 1.5, cy + 15.7, "FECHA DE ATENCION", size=6,
           font="Helvetica-Bold", color=GRIS_LABEL)
    _texto(c, PAGE_W_MM - MARGEN_MM - 51 + 1.5, cy + 19.4, fecha_txt, size=8)

    ipress = getattr(paciente, "distrito", None)
    ipress_nombre = getattr(ipress, "nombre", "") if ipress else ""
    _texto(c, MARGEN_MM + 3, cy + 21, f"IPRESS: {ipress_nombre or 'CardioPredict'}"
           f"    |    RENAES: -------------------", size=7, color=GRIS_LABEL)

    return cy + alto + 2.0


def _datos_paciente(c: canvas.Canvas, cy: float, evaluacion: Evaluacion,
                    paciente: Paciente) -> float:
    """Bloque 1: datos del asegurado / paciente."""
    cy = _banda_titulo(c, cy, "1. DATOS DEL PACIENTE (ASEGURADO)")

    apellidos = " ".join(p for p in [paciente.apellido_paterno, paciente.apellido_materno] if p)

    # Fila 1: documentos
    cy = _fila_campos(c, cy, 12, [
        (MARGEN_MM, 32, "Tipo Doc.", paciente.tipo_documento),
        (MARGEN_MM + 33, 48, "N° Documento", paciente.documento_identidad),
        (MARGEN_MM + 82, 60, "Código Filiación Seguro",
         paciente.codigo_afiliacion_seguro or ""),
        (MARGEN_MM + 143, ANCHO_CONTENIDO - 143, "Tipo Seguro", paciente.tipo_seguro),
    ])

    # Fila 2: nombres completos
    cy = _fila_campos(c, cy, 12, [
        (MARGEN_MM, ANCHO_CONTENIDO, "Apellidos y Nombres", f"{apellidos}, {paciente.nombres}"),
    ])

    # Fila 3: nacimiento / edad / sexo / dirección
    fnac = paciente.fecha_nacimiento
    fnac_txt = fnac.strftime("%d/%m/%Y") if isinstance(fnac, date) else str(fnac or "")
    cy = _fila_campos(c, cy, 12, [
        (MARGEN_MM, 60, "Fecha de Nacimiento", fnac_txt),
        (MARGEN_MM + 61, 35, "Edad", f"{evaluacion.edad} años"),
        (MARGEN_MM + 97, 30, "Sexo",
         "Masculino" if paciente.sexo == "M" else "Femenino"),
        (MARGEN_MM + 128, ANCHO_CONTENIDO - 128, "Dirección", paciente.direccion or ""),
    ])
    return cy


def _datos_atencion(c: canvas.Canvas, cy: float, evaluacion: Evaluacion,
                    usuario: Usuario) -> float:
    """Bloque 2: datos de la atención."""
    cy = _banda_titulo(c, cy, "2. DATOS DE LA ATENCION")

    cy = _fila_campos(c, cy, 11, [
        (MARGEN_MM, 90, "Tipo de Atención", "Evaluación preventiva (tamizaje)"),
        (MARGEN_MM + 91, ANCHO_CONTENIDO - 91, "Profesional Responsable", usuario.nombre),
    ])
    cy = _fila_campos(c, cy, 11, [
        (MARGEN_MM, ANCHO_CONTENIDO, "Concepto / Finalidad",
         "Detección de riesgo cardiovascular con apoyo de modelo ML"),
    ])
    return cy


def _variables(c: canvas.Canvas, cy: float, evaluacion: Evaluacion,
               paciente: Paciente) -> float:
    """Bloque 3: mediciones físicas + variables evaluadas (Sí/No)."""
    cy = _banda_titulo(c, cy, "3. ACTIVIDADES PREVENTIVAS Y FACTORES DE RIESGO")

    cy = _fila_campos(c, cy, 11, [
        (MARGEN_MM, 45, "Peso (kg)", _fmt_float(paciente.peso_kg)),
        (MARGEN_MM + 46, 45, "Talla (cm)", _fmt_float(paciente.talla_cm)),
        (MARGEN_MM + 92, ANCHO_CONTENIDO - 92, "Estado General (1-5)",
         f"{evaluacion.salud_general} - {SALUD_GENERAL_TEXTO.get(evaluacion.salud_general, '')}"),
    ])

    factores = [
        ("Presión arterial alta", evaluacion.presion_alta),
        ("Colesterol alto", evaluacion.colesterol_alto),
        ("Tabaquismo", evaluacion.tabaquismo),
        ("Actividad física", evaluacion.actividad_fisica),
        ("Antecedente de ACV", evaluacion.antecedente_acv),
        ("Diabetes", evaluacion.diabetes),
        ("Dificultad para caminar", evaluacion.dificultad_para_caminar),
    ]
    ancho_col = ANCHO_CONTENIDO / 2
    for i in range(0, len(factores), 2):
        par = factores[i:i + 2]
        campos = []
        for j, (label, valor) in enumerate(par):
            x = MARGEN_MM + j * ancho_col
            campos.append((x, ancho_col - 1, label, _texto_si_no(valor)))
        cy = _fila_campos(c, cy, 10, campos)
    return cy


def _resultado(c: canvas.Canvas, cy: float, evaluacion: Evaluacion) -> float:
    """Bloque 4: resultado ML + triaje clínico (semáforo)."""
    cy = _banda_titulo(c, cy, "4. RESULTADO DEL TAMIZAJE")

    # Usa el mapper para obtener el triaje (persistido o recalculado)
    response = EvaluacionMapper.to_response(evaluacion)
    triaje = response.triaje_clinico

    clasificacion = response.clasificacion
    nombre_color = clasificacion.value if hasattr(clasificacion, "value") else str(clasificacion)

    # Franja de color según clasificación
    cy = _salto(c, cy, 15)
    color_fondo = COLOR_HEX.get(nombre_color, colors.white)
    _rect(c, MARGEN_MM, cy, ANCHO_CONTENIDO, 14, fill=color_fondo)
    _texto(c, MARGEN_MM + 2, cy + 2.5,
           f"NIVEL DE RIESGO: {nombre_color.upper()}  |  {triaje.nivel_alerta}",
           size=10, font="Helvetica-Bold")
    _texto(c, MARGEN_MM + 2, cy + 8.5,
           f"Probabilidad: {response.probabilidad * 100:.2f}%    Modelo: {response.modelo_version or 'N/D'}",
           size=8)
    cy += 15.2

    # Acción sugerida
    cy = _salto(c, cy, 6)
    _texto(c, MARGEN_MM + 2, cy, "ACCION SUGERIDA:", size=7.5, font="Helvetica-Bold",
           color=GRIS_LABEL)
    cy = _parrafo(c, cy + 3.5, MARGEN_MM + 2, ANCHO_CONTENIDO - 4,
                  triaje.accion_sugerida, size=8.5)
    cy += 1.5
    return cy


def _factores(c: canvas.Canvas, cy: float, evaluacion: Evaluacion) -> float:
    """Bloque 5: factores detectados, protectores y recomendaciones."""
    response = EvaluacionMapper.to_response(evaluacion)
    triaje = response.triaje_clinico

    cy = _banda_titulo(c, cy, "5. FACTORES DE RIESGO Y RECOMENDACIONES")

    cy = _salto(c, cy, 5)
    _texto(c, MARGEN_MM + 2, cy, "FACTORES DE RIESGO DETECTADOS:", size=7.5,
           font="Helvetica-Bold", color=GRIS_LABEL)
    cy += 3.5
    lista = triaje.factores_riesgo_detectados or []
    if not lista:
        lista = ["Ninguno"]
    for f in lista:
        cy = _parrafo(c, cy, MARGEN_MM + 5, ANCHO_CONTENIDO - 6, f"- {f}", size=8.5)
    cy += 1.5

    cy = _salto(c, cy, 5)
    _texto(c, MARGEN_MM + 2, cy, "FACTORES PROTECTORES:", size=7.5,
           font="Helvetica-Bold", color=GRIS_LABEL)
    cy += 3.5
    lista = triaje.factores_protectores or []
    if not lista:
        lista = ["Ninguno"]
    for f in lista:
        cy = _parrafo(c, cy, MARGEN_MM + 5, ANCHO_CONTENIDO - 6, f"- {f}", size=8.5)
    cy += 1.5

    cy = _salto(c, cy, 5)
    _texto(c, MARGEN_MM + 2, cy, "EXAMENES / CONTROLES SUGERIDOS:", size=7.5,
           font="Helvetica-Bold", color=GRIS_LABEL)
    cy += 3.5
    for r in (triaje.recomendaciones_medicas or []):
        cy = _parrafo(c, cy, MARGEN_MM + 5, ANCHO_CONTENIDO - 6, f"- {r}", size=8.5)
    cy += 1.5
    return cy


def _firmas(c: canvas.Canvas, cy: float, usuario: Usuario) -> float:
    """Bloque 6: firmas (profesional y paciente/apoderado)."""
    cy = _banda_titulo(c, cy, "6. FIRMAS Y CONFORMIDAD")

    ancho_mitad = (ANCHO_CONTENIDO - 6) / 2
    alto = 38

    # Profesional
    cy = _salto(c, cy, alto + 2)
    x1 = MARGEN_MM
    _rect(c, x1, cy, ancho_mitad, alto)
    _texto(c, x1 + 2, cy + 1.5, "PROFESIONAL DE SALUD RESPONSABLE", size=7,
           font="Helvetica-Bold", color=GRIS_LABEL)
    _texto(c, x1 + 2, cy + 7.5, usuario.nombre, size=8.5, font="Helvetica-Bold")
    _texto(c, x1 + 2, cy + 13, "N° de colegiatura: ____________________", size=7.5)
    _rect(c, x1 + 2, cy + 20, ancho_mitad - 4, 1.0)  # línea de firma
    _texto(c, x1 + 2, cy + 22, "Firma y sello", size=6.5, color=GRIS_LABEL)

    # Paciente / apoderado
    x2 = MARGEN_MM + ancho_mitad + 6
    _rect(c, x2, cy, ancho_mitad, alto)
    _texto(c, x2 + 2, cy + 1.5, "PACIENTE / APODERADO", size=7,
           font="Helvetica-Bold", color=GRIS_LABEL)
    _rect(c, x2 + 2, cy + 9, ancho_mitad - 4, 11)  # recuadro de huella digital
    _texto(c, x2 + 2, cy + 13.8, "Huella digital", size=6.5, color=GRIS_LABEL)
    _rect(c, x2 + 2, cy + 26, ancho_mitad - 4, 1.0)  # línea de firma
    _texto(c, x2 + 2, cy + 28, "Firma", size=6.5, color=GRIS_LABEL)

    cy += alto + 1.5
    return cy


def generar_fua_pdf(evaluacion: Evaluacion) -> bytes:
    """
    Genera el PDF del FUA para una evaluación. Recibe el ORM (con relaciones
    paciente/usuario accesibles) y devuelve los bytes del PDF.
    """
    paciente: Paciente = evaluacion.paciente
    usuario: Usuario = evaluacion.usuario

    num_fua = f"FUA-{evaluacion.id:06d}"

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W_MM * mm, PAGE_H_MM * mm))
    c.setTitle(f"FUA {num_fua} - {paciente.nombre_completo}")
    c.setAuthor(usuario.nombre)
    c.setSubject("Formato Unico de Atencion - Tamizaje de Riesgo Cardiovascular")

    cy = _encabezado(c, TOPE_MM, evaluacion, paciente, num_fua)
    cy = _datos_paciente(c, cy, evaluacion, paciente)
    cy = _datos_atencion(c, cy, evaluacion, usuario)
    cy = _variables(c, cy, evaluacion, paciente)
    cy = _resultado(c, cy, evaluacion)
    cy = _factores(c, cy, evaluacion)
    cy = _firmas(c, cy, usuario)

    _pie_pagina(c, cy)
    c.showPage()
    c.save()
    return buf.getvalue()


class ReporteService:
    """
    Service de reportes PDF. Orquesta: Repository (BD) + generador ReportLab.
    """

    def __init__(self, db):
        self.evaluacion_repo = EvaluacionRepository(db)

    def generar_fua(self, evaluacion_id: int) -> Optional[bytes]:
        """
        Genera el PDF del FUA para una evaluación por su ID.

        Retorna:
          - bytes del PDF si la evaluación existe
          - None si no existe (el endpoint responde 404)
        """
        evaluacion = self.evaluacion_repo.get_by_id(evaluacion_id)
        if not evaluacion:
            return None
        return generar_fua_pdf(evaluacion)
