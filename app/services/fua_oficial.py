"""
fua_oficial.py — RELLENADO DEL FUA OFICIAL (Anexo 1, Directiva SIS 001-2021)

En lugar de DIBUJAR el formulario con ReportLab (rectángulos, líneas y títulos),
este módulo usa como FONDO el PDF del formulario oficial
(app/resources/fua_plantilla.pdf) y escribe ENCIMA solo los datos.

Cómo funciona:
  1. ReportLab crea una hoja transparente con los textos/aspas en las
     coordenadas de cada casilla del formulario (diccionario de abajo).
  2. pypdf pega esa hoja sobre la plantilla oficial.
  3. La página resultante se escala y centra en papel OFICIO (215 x 330 mm),
     el mismo tamaño que usan las páginas de anexo del reporte.

Las coordenadas están en PUNTOS sobre la página original del PDF de la
Directiva (612 x 792 pt, origen ARRIBA-izquierda para escribirlas más fácil).
Si el SIS cambia el formato: se genera otra plantilla con
scripts/crear_plantilla_fua.py y se recalibra SOLO este archivo.

Nada de lo que no conoce el sistema se inventa: RENAES, UPS, códigos de
prestación, CIE-10, firma y colegiatura quedan en blanco para llenarse a mano.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

# ============================================================
# PLANTILLA Y TAMAÑOS
# ============================================================
RUTA_PLANTILLA = Path(__file__).resolve().parents[1] / "resources" / "fua_plantilla.pdf"

PAGINA_ORIGEN_H = 792.0          # alto de la página original del PDF de la Directiva
PAGE_W = 215 * mm                # oficio peruano
PAGE_H = 330 * mm
# Recuadro recortado de la plantilla (mismo que scripts/crear_plantilla_fua.py)
CAJA_X0, CAJA_Y0, CAJA_X1, CAJA_Y1 = 82.5, 76.0, 519.0, 708.5
MARGEN_PT = 14.0

# Datos de la IPRESS: configurables por variable de entorno (el sistema no los guarda en BD)
IPRESS_NOMBRE = os.getenv("FUA_IPRESS_NOMBRE", "HealthCure CardioPredict")
IPRESS_RENAES = os.getenv("FUA_IPRESS_RENAES", "")        # código RENAES (si la IPRESS lo tiene)
IPRESS_RENIPRESS = os.getenv("FUA_IPRESS_RENIPRESS", "")  # 8 dígitos para el N° de formato

# ============================================================
# COORDENADAS DE LAS CASILLAS  (x0, x1, top, bottom)  — puntos, origen arriba-izq
# ============================================================
# --- Cabecera ---
NUM_RENIPRESS = (192.1, 219.2, 118.7, 130.6)
NUM_LOTE = (219.2, 252.2, 118.7, 130.6)
NUM_CORRELATIVO = (252.2, 323.7, 118.7, 130.6)
IPRESS_COD = (84.8, 201.7, 150.7, 162.0)
IPRESS_NOM = (201.7, 514.9, 150.7, 162.0)

# --- Personal que atiende / lugar / atención (casillas de aspa: x, y centro) ---
ASPA_PERSONAL_IPRESS = (134.8, 177.5)
ASPA_LUGAR_INTRAMURAL = (247.5, 177.5)
ASPA_ATENCION_AMBULATORIA = (299.2, 177.5)
ASPA_ATENCION_REFERENCIA = (299.2, 186.4)
ASPA_ATENCION_EMERGENCIA = (299.2, 194.5)

# --- Asegurado / usuario ---
TDI = (84.8, 111.6, 221.0, 230.5)
DOC_NUMERO = (111.6, 182.1, 221.0, 230.5)
SIS_DIRESA = (185.1, 212.1, 221.0, 230.5)     # 3 dígitos: DIRESA
SIS_PLAN = (212.1, 239.2, 221.0, 230.5)       # 1 dígito/letra: tipo de plan (2 = subsidiado con DNI)
SIS_NUMERO = (241.4, 293.7, 221.0, 230.5)     # número de DNI / CE
OTRA_IAFAS_INST = (333.7, 514.9, 211.5, 221.0)
OTRA_IAFAS_COD = (333.7, 514.9, 221.0, 230.5)
APE_PATERNO = (84.8, 293.7, 237.0, 248.5)
APE_MATERNO = (296.7, 514.9, 237.0, 248.5)
NOM_PRIMER = (84.8, 293.7, 254.5, 267.2)
NOM_OTROS = (296.7, 514.9, 254.5, 267.2)
ASPA_SEXO_M = (131.5, 277.5)
ASPA_SEXO_F = (131.5, 284.7)
HISTORIA_CLINICA = (336.3, 417.9, 274.0, 288.7)
# Fecha de nacimiento: una celda por dígito  (DD MM AAAA)
NAC_FILA = (288.7, 303.4)
NAC_DD = [(192.1, 210.3), (210.3, 226.6)]
NAC_MM = [(226.6, 241.4), (241.4, 258.1)]
NAC_AAAA = [(258.1, 276.3), (276.3, 296.7), (296.7, 315.9), (315.9, 333.7)]

# --- De la atención ---
ATE_FILA = (346.9, 357.6)
ATE_DD = [(84.8, 97.5), (97.5, 111.6)]
ATE_MM = [(111.6, 121.7), (121.7, 134.6)]
ATE_AAAA = [(134.6, 147.6), (147.6, 166.1), (166.1, 182.1), (182.1, 196.9)]
ATE_HORA_HH = (201.7, 219.2, 346.9, 357.6)
ATE_HORA_MM = (226.6, 239.2, 346.9, 357.6)

# --- Concepto prestacional ---
ASPA_ATENCION_DIRECTA = (128.2, 393.0)

# --- Actividades preventivas y otros ---
PESO = (142.4, 173.6, 461.3, 470.8)
TALLA = (226.6, 253.7, 461.3, 470.8)
PRESION = (314.8, 347.6, 461.3, 470.8)
IMC = (300.0, 347.6, 532.5, 548.3)

# --- Diagnósticos (5 filas): descripción y CIE-10 de ingreso ---
DX_FILAS = [(567.7, 576.9), (576.9, 586.1), (586.1, 595.3), (595.3, 604.5), (604.5, 613.5)]
DX_DESC_X = (97.5, 315.9)
DX_CIE_INGRESO_X = (365.6, 417.9)

# --- Responsable de la atención ---
RESP_DNI = (84.8, 173.6, 621.4, 629.7)
RESP_NOMBRE = (173.6, 423.5, 621.4, 629.7)
RESP_COLEGIATURA = (423.5, 514.9, 621.4, 629.7)


# ============================================================
# DATOS A IMPRIMIR
# ============================================================
@dataclass
class FuaDatos:
    """Todo lo que el sistema sabe y se imprime en el formulario (todo opcional)."""
    correlativo: Optional[int] = None            # N° correlativo de la atención
    # Asegurado
    tipo_documento: str = ""                     # "DNI" | "CE" | "Pasaporte"
    documento: str = ""
    tipo_seguro: str = ""                        # "SIS" | "EsSalud" | "Privado" | "Otro"
    codigo_seguro: str = ""
    apellido_paterno: str = ""
    apellido_materno: str = ""
    nombres: str = ""
    sexo: str = ""                               # "M" | "F"
    historia_clinica: str = ""
    fecha_nacimiento: Optional[date] = None
    # Atención
    fecha_atencion: Optional[datetime] = None
    emergencia: bool = False
    # Mediciones
    peso_kg: Optional[float] = None
    talla_cm: Optional[float] = None
    presion_sistolica: Optional[float] = None
    presion_diastolica: Optional[float] = None
    # Diagnósticos: (descripción, CIE-10 o "")
    diagnosticos: List[Tuple[str, str]] = field(default_factory=list)
    # Profesional que atiende
    profesional: str = ""
    # Nota al pie (fuera del formulario) con el origen del documento
    nota_pie: str = ""


# ============================================================
# HELPERS DE DIBUJO
# ============================================================
def _y(top: float) -> float:
    """Convierte 'top' (desde arriba) a coordenada PDF (desde abajo)."""
    return PAGINA_ORIGEN_H - top


def _fmt_num(valor) -> str:
    return "" if valor is None else f"{float(valor):g}"


def _texto_en_celda(c: canvas.Canvas, celda, texto: str, size: float = 8.5,
                    align: str = "left", font: str = "Helvetica", pad: float = 2.0) -> None:
    """Escribe 'texto' dentro de la celda (x0, x1, top, bottom), centrado en vertical.
    Reduce la letra (hasta 5 pt) si el texto no cabe en el ancho."""
    if not texto:
        return
    x0, x1, top, bottom = celda
    ancho = (x1 - x0) - 2 * pad
    while size > 5 and stringWidth(texto, font, size) > ancho:
        size -= 0.5
    while texto and stringWidth(texto, font, size) > ancho:   # último recurso: recortar
        texto = texto[:-1]
    c.setFont(font, size)
    base = _y((top + bottom) / 2) - size * 0.35
    if align == "center":
        c.drawCentredString((x0 + x1) / 2, base, texto)
    elif align == "right":
        c.drawRightString(x1 - pad, base, texto)
    else:
        c.drawString(x0 + pad, base, texto)


def _digitos(c: canvas.Canvas, celdas_x: Sequence[Tuple[float, float]],
             fila: Tuple[float, float], texto: str, size: float = 8.5) -> None:
    """Escribe un dígito por celda (se alinea a la derecha si sobran celdas)."""
    texto = texto[-len(celdas_x):]
    celdas = celdas_x[len(celdas_x) - len(texto):]
    for (x0, x1), ch in zip(celdas, texto):
        _texto_en_celda(c, (x0, x1, fila[0], fila[1]), ch, size=size, align="center", font="Helvetica-Bold")


def _aspa(c: canvas.Canvas, centro: Tuple[float, float], medio: float = 3.2) -> None:
    """Dibuja una X (aspa) centrada en (x, top)."""
    x, top = centro
    y = _y(top)
    c.setLineWidth(1.3)
    c.line(x - medio, y - medio, x + medio, y + medio)
    c.line(x - medio, y + medio, x + medio, y - medio)


def _codigo_tdi(tipo_documento: str) -> str:
    """Directiva (Anexo 2, 1.3.a): 2 = DNI, 3 = Carné de extranjería. Pasaporte no tiene código."""
    return {"DNI": "2", "CE": "3"}.get(tipo_documento or "", "")


def _dibujar_datos(c: canvas.Canvas, d: FuaDatos) -> None:
    c.setFillColorRGB(0, 0, 0.55)       # tinta azul oscuro: se distingue del formulario impreso
    c.setStrokeColorRGB(0, 0, 0.55)

    # --- Número de formato: RENIPRESS (8) | lote (2) | correlativo (8) ---
    _texto_en_celda(c, NUM_RENIPRESS, IPRESS_RENIPRESS, size=7, align="center")
    if d.fecha_atencion:
        _texto_en_celda(c, NUM_LOTE, f"{d.fecha_atencion.year % 100:02d}", size=9, align="center")
    if d.correlativo is not None:
        _texto_en_celda(c, NUM_CORRELATIVO, f"{d.correlativo:08d}", size=9, align="center", font="Helvetica-Bold")

    # --- IPRESS ---
    _texto_en_celda(c, IPRESS_COD, IPRESS_RENAES, size=9, align="center")
    _texto_en_celda(c, IPRESS_NOM, IPRESS_NOMBRE.upper(), size=8.5, align="center", font="Helvetica-Bold")
    _aspa(c, ASPA_PERSONAL_IPRESS)
    _aspa(c, ASPA_LUGAR_INTRAMURAL)
    _aspa(c, ASPA_ATENCION_EMERGENCIA if d.emergencia else ASPA_ATENCION_AMBULATORIA)

    # --- Asegurado: documento y seguro ---
    _texto_en_celda(c, TDI, _codigo_tdi(d.tipo_documento), size=9, align="center", font="Helvetica-Bold")
    _texto_en_celda(c, DOC_NUMERO, d.documento, size=8.5, align="center", font="Helvetica-Bold")
    if d.tipo_seguro == "SIS":
        partes = [p for p in (d.codigo_seguro or "").split("-") if p]
        if len(partes) == 3:                              # ej. 040-2-1032456789 → DIRESA | plan | DNI
            _texto_en_celda(c, SIS_DIRESA, partes[0], size=8, align="center")
            _texto_en_celda(c, SIS_PLAN, partes[1], size=8, align="center")
            _texto_en_celda(c, SIS_NUMERO, partes[2], size=8, align="center")
        else:                                             # formato distinto: se imprime completo
            _texto_en_celda(c, SIS_NUMERO, d.codigo_seguro, size=8, align="center")
    elif d.tipo_seguro:
        # Otra IAFAS: 1 = EsSalud, 4 = Otros (la Directiva no tiene código propio para "Privado")
        inst = {"EsSalud": "1", "Otro": "4", "Privado": "4"}.get(d.tipo_seguro, "")
        _texto_en_celda(c, OTRA_IAFAS_INST, inst, size=9, align="center")
        _texto_en_celda(c, OTRA_IAFAS_COD, d.codigo_seguro, size=9, align="center")

    _texto_en_celda(c, APE_PATERNO, d.apellido_paterno.upper(), size=8.5, align="center", font="Helvetica-Bold")
    _texto_en_celda(c, APE_MATERNO, d.apellido_materno.upper(), size=8.5, align="center", font="Helvetica-Bold")
    primer, _, otros = d.nombres.strip().partition(" ")      # "José Manuel" → José | Manuel
    _texto_en_celda(c, NOM_PRIMER, primer.upper(), size=8.5, align="center", font="Helvetica-Bold")
    _texto_en_celda(c, NOM_OTROS, otros.upper(), size=8.5, align="center", font="Helvetica-Bold")

    if d.sexo == "M":
        _aspa(c, ASPA_SEXO_M)
    elif d.sexo == "F":
        _aspa(c, ASPA_SEXO_F)
    _texto_en_celda(c, HISTORIA_CLINICA, d.historia_clinica, size=8.5, align="center", font="Helvetica-Bold")
    if d.fecha_nacimiento:
        f = d.fecha_nacimiento
        _digitos(c, NAC_DD, NAC_FILA, f"{f.day:02d}")
        _digitos(c, NAC_MM, NAC_FILA, f"{f.month:02d}")
        _digitos(c, NAC_AAAA, NAC_FILA, f"{f.year:04d}")

    # --- De la atención ---
    if d.fecha_atencion:
        f = d.fecha_atencion
        _digitos(c, ATE_DD, ATE_FILA, f"{f.day:02d}")
        _digitos(c, ATE_MM, ATE_FILA, f"{f.month:02d}")
        _digitos(c, ATE_AAAA, ATE_FILA, f"{f.year:04d}")
        _texto_en_celda(c, ATE_HORA_HH, f"{f.hour:02d}", size=8.5, align="center", font="Helvetica-Bold")
        _texto_en_celda(c, ATE_HORA_MM, f"{f.minute:02d}", size=8.5, align="center", font="Helvetica-Bold")
    _aspa(c, ASPA_ATENCION_DIRECTA)

    # --- Actividades preventivas: peso, talla, presión arterial, IMC ---
    _texto_en_celda(c, PESO, _fmt_num(d.peso_kg), size=8.5, align="center", font="Helvetica-Bold")
    _texto_en_celda(c, TALLA, _fmt_num(d.talla_cm), size=8.5, align="center", font="Helvetica-Bold")
    if d.presion_sistolica is not None and d.presion_diastolica is not None:
        _texto_en_celda(c, PRESION, f"{d.presion_sistolica:g}/{d.presion_diastolica:g}",
                        size=9, align="center", font="Helvetica-Bold")
    if d.peso_kg and d.talla_cm:
        imc = float(d.peso_kg) / ((float(d.talla_cm) / 100) ** 2)
        _texto_en_celda(c, IMC, f"{imc:.1f}", size=8.5, align="center", font="Helvetica-Bold")

    # --- Diagnósticos (máx. 5) ---
    for i, (descripcion, cie10) in enumerate(d.diagnosticos[:len(DX_FILAS)]):
        top, bottom = DX_FILAS[i]
        _texto_en_celda(c, (DX_DESC_X[0], DX_DESC_X[1], top, bottom), descripcion, size=7)
        _texto_en_celda(c, (DX_CIE_INGRESO_X[0], DX_CIE_INGRESO_X[1], top, bottom), cie10,
                        size=8, align="center")

    # --- Responsable de la atención (DNI, colegiatura y firma: a mano) ---
    _texto_en_celda(c, RESP_NOMBRE, d.profesional.upper(), size=8, align="center", font="Helvetica-Bold")


# ============================================================
# CONSTRUCCIÓN DE LOS DATOS A PARTIR DEL PACIENTE / USUARIO
# ============================================================
def _primero(*valores):
    """Primer valor que no sea None (las mediciones de la visita mandan sobre las del paciente)."""
    return next((v for v in valores if v is not None), None)


def resumir(texto: Optional[str], maximo: int = 78) -> str:
    """Una sola línea para la casilla de diagnóstico; el texto completo va en el anexo."""
    linea = " ".join((texto or "").split())
    return linea if len(linea) <= maximo else linea[:maximo - 1].rstrip() + "…"


def construir_datos(paciente, usuario, observaciones: Optional[dict], fecha: Optional[datetime],
                    correlativo: Optional[int], emergencia: bool = False,
                    diagnosticos: Optional[List[Tuple[str, str]]] = None,
                    nota_pie: str = "") -> FuaDatos:
    """Arma FuaDatos con lo que ya conoce el sistema (sirve para evaluación y para atención)."""
    obs = observaciones or {}
    return FuaDatos(
        correlativo=correlativo,
        tipo_documento=paciente.tipo_documento or "",
        documento=paciente.documento_identidad or "",
        tipo_seguro=paciente.tipo_seguro or "",
        codigo_seguro=paciente.codigo_afiliacion_seguro or "",
        apellido_paterno=paciente.apellido_paterno or "",
        apellido_materno=paciente.apellido_materno or "",
        nombres=paciente.nombres or "",
        sexo=paciente.sexo or "",
        historia_clinica=paciente.numero_historia_clinica or "",
        fecha_nacimiento=paciente.fecha_nacimiento if isinstance(paciente.fecha_nacimiento, date) else None,
        fecha_atencion=fecha if isinstance(fecha, datetime) else None,
        emergencia=emergencia,
        peso_kg=_primero(obs.get("peso_kg"), paciente.peso_kg),
        talla_cm=_primero(obs.get("talla_cm"), paciente.talla_cm),
        presion_sistolica=obs.get("presion_sistolica"),
        presion_diastolica=obs.get("presion_diastolica"),
        diagnosticos=diagnosticos or [],
        profesional=usuario.nombre if usuario else "",
        nota_pie=nota_pie or NOTA_PIE,
    )


NOTA_PIE = ("Formato oficial FUA (Anexo 1, Directiva Administrativa N° 001-2021-SIS/GREP V.01). "
            "Generado por HealthCure CardioPredict: lo que el sistema no registra queda en blanco "
            "para completarse a mano. El N° de formato es interno y no reemplaza el asignado por el SIS.")


# ============================================================
# API PÚBLICA
# ============================================================
def _hoja_de_datos(d: FuaDatos) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(612, PAGINA_ORIGEN_H))
    _dibujar_datos(c, d)
    c.showPage()
    c.save()
    return buf.getvalue()


def pagina_fua_oficial(datos: FuaDatos) -> bytes:
    """
    Devuelve un PDF de 1 página: el formulario FUA oficial con los datos escritos
    encima, escalado y centrado en papel oficio (215 x 330 mm).
    """
    plantilla = PdfReader(str(RUTA_PLANTILLA)).pages[0]
    overlay = PdfReader(BytesIO(_hoja_de_datos(datos))).pages[0]

    ancho, alto = CAJA_X1 - CAJA_X0, CAJA_Y1 - CAJA_Y0
    escala = min((PAGE_W - 2 * MARGEN_PT) / ancho, (PAGE_H - 2 * MARGEN_PT - 40) / alto)
    tx = (PAGE_W - ancho * escala) / 2 - CAJA_X0 * escala
    ty = (PAGE_H - alto * escala) / 2 + 8 - CAJA_Y0 * escala     # un poco más arriba: deja pie
    transformacion = Transformation().scale(escala).translate(tx, ty)

    out = PdfWriter()
    hoja = out.add_blank_page(width=PAGE_W, height=PAGE_H)
    hoja.merge_transformed_page(plantilla, transformacion)       # formulario oficial de fondo
    hoja.merge_transformed_page(overlay, transformacion)         # datos encima (mismas coordenadas)

    if datos.nota_pie:
        pie = BytesIO()
        c = canvas.Canvas(pie, pagesize=(PAGE_W, PAGE_H))
        c.setFont("Helvetica", 6.5)
        c.setFillGray(0.35)
        lineas = simpleSplit(datos.nota_pie, "Helvetica", 6.5, PAGE_W - 2 * MARGEN_PT)
        for i, linea in enumerate(lineas):
            c.drawString(MARGEN_PT, 12 * mm - i * 8, linea)
        c.showPage()
        c.save()
        hoja.merge_page(PdfReader(BytesIO(pie.getvalue())).pages[0])

    buf = BytesIO()
    out.write(buf)
    return buf.getvalue()


def unir_pdfs(*pdfs: bytes, titulo: str = "", autor: str = "") -> bytes:
    """Une varios PDF (bytes) en uno solo, en el orden recibido."""
    out = PdfWriter()
    for pdf in pdfs:
        for pagina in PdfReader(BytesIO(pdf)).pages:
            out.add_page(pagina)
    meta = {}
    if titulo:
        meta["/Title"] = titulo
    if autor:
        meta["/Author"] = autor
    if meta:
        out.add_metadata(meta)
    buf = BytesIO()
    out.write(buf)
    return buf.getvalue()
