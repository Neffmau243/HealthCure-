"""
crear_plantilla_fua.py — Extrae el FUA oficial (Anexo 1) de la Directiva del SIS.

Fuente: Resolución Jefatural N° 015-2021/SIS/J — Directiva Administrativa
N° 001-2021-SIS/GREP V.01. El Anexo 1 (el formulario FUA) está en la
PÁGINA 11 de ese PDF de 42 páginas.

Qué hace:
  1. Toma esa página 11.
  2. Recorta (clip + cropbox) SOLO el recuadro azul del formulario, para que no
     aparezcan el encabezado "DIRECTIVA ADMINISTRATIVA...", el "Página 11 de 42"
     ni los sellos laterales.
  3. Guarda una página de 1 sola hoja: app/resources/fua_plantilla.pdf

Se ejecuta UNA vez (el resultado ya queda en el repo):
    pip install pypdf
    python scripts/crear_plantilla_fua.py "ruta/FUA_ANEXO_RJ_015-2021....pdf"
"""
import sys
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, ContentStream, FloatObject, RectangleObject

PAGINA_FORMULARIO = 10            # índice base 0 → página 11 del PDF
# Recuadro del formulario en coordenadas PDF (puntos, origen abajo-izquierda)
X0, Y0, X1, Y1 = 82.5, 76.0, 519.0, 708.5

DESTINO = Path(__file__).resolve().parents[1] / "app" / "resources" / "fua_plantilla.pdf"


def _fuera(x: float, y: float) -> bool:
    return x < X0 - 1 or x > X1 + 1 or y < Y0 or y > Y1


def _quitar_contenido_fuera_del_recuadro(operaciones: list) -> list:
    """
    El clip oculta lo que cae fuera del formulario, pero el texto seguiría
    existiendo en el PDF (se vería al copiar/buscar: "DIRECTIVA ADMINISTRATIVA...",
    "Página 11 de 42"). Aquí lo eliminamos de verdad:
      - textos (BT...ET con matriz Tm fuera del recuadro) → se vacían (se conservan
        fuente y color para no alterar el texto siguiente);
      - imágenes (sellos laterales) cuyo 'cm' cae fuera → se omite el 'Do'.
    """
    limpias, fuera_texto, ultimo_cm = [], False, None
    for operandos, op in operaciones:
        if op == b"BT":
            fuera_texto = False
        elif op == b"Tm":
            fuera_texto = _fuera(float(operandos[4]), float(operandos[5]))
        elif op == b"cm":
            ultimo_cm = (float(operandos[4]), float(operandos[5]))
        elif op == b"Do" and ultimo_cm and _fuera(*ultimo_cm):
            continue
        elif op in (b"TJ", b"Tj") and fuera_texto:
            limpias.append(([ArrayObject()], b"TJ"))
            continue
        limpias.append((operandos, op))
    return limpias


def main(origen: str) -> None:
    # Clonamos el PDF dentro de un writer y dejamos SOLO la página del formulario
    writer = PdfWriter(clone_from=origen)
    total = len(writer.pages)
    for i in range(total - 1, -1, -1):
        if i != PAGINA_FORMULARIO:
            del writer.pages[i]
    page = writer.pages[0]

    # Recorte real: q <rect> re W n  ...contenido...  Q
    cs = ContentStream(page.get_contents(), writer)
    cs.operations = _quitar_contenido_fuera_del_recuadro(cs.operations)
    rect = [FloatObject(v) for v in (X0, Y0, X1 - X0, Y1 - Y0)]
    cs.operations.insert(0, ([], b"q"))
    cs.operations.insert(1, (rect, b"re"))
    cs.operations.insert(2, ([], b"W"))
    cs.operations.insert(3, ([], b"n"))
    cs.operations.append(([], b"Q"))
    page.replace_contents(cs)

    caja = RectangleObject([X0, Y0, X1, Y1])
    page.mediabox = caja
    page.cropbox = caja
    page.trimbox = caja

    # Re-escribimos en un PDF nuevo para descartar los objetos de las otras 41 páginas
    # (baja de ~1 MB a ~0.3 MB) y comprimimos el contenido.
    tmp = BytesIO()
    writer.write(tmp)
    limpio = PdfWriter()
    limpio.add_page(PdfReader(BytesIO(tmp.getvalue())).pages[0])
    limpio.pages[0].compress_content_streams()
    limpio.add_metadata({"/Title": "FUA - Formato Único de Atención (Anexo 1, SIS)"})
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    with open(DESTINO, "wb") as f:
        limpio.write(f)
    print("Plantilla creada:", DESTINO)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python scripts/crear_plantilla_fua.py <ruta_al_pdf_de_la_directiva>")
    main(sys.argv[1])
