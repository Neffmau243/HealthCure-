"""Datos de la atención independientes del modelo de riesgo cardiovascular."""
from datetime import date
from enum import Enum


class TipoAtencion(str, Enum):
    ambulatoria = "ambulatoria"
    emergencia = "emergencia"


class GrupoEtario(str, Enum):
    nino = "nino"
    adulto = "adulto"
    adulto_mayor = "adulto_mayor"


class CondicionMaterna(str, Enum):
    ninguna = "ninguna"
    gestante = "gestante"
    puerpera = "puerpera"


TIPOS_ATENCION = {"ambulatoria": "Ambulatoria", "emergencia": "Emergencia"}
GRUPOS_ETARIOS = {
    "nino": "Niño/a",
    "adulto": "Adulto/a", "adulto_mayor": "Adulto/a mayor",
}
CONDICIONES_MATERNAS = {
    "ninguna": "Ninguna", "gestante": "Gestante", "puerpera": "Puérpera",
}


def calcular_edad(nacimiento: date, fecha: date | None = None) -> int:
    fecha = fecha or date.today()
    if nacimiento > fecha:
        raise ValueError("La fecha de nacimiento no puede ser futura")
    return fecha.year - nacimiento.year - (
        (fecha.month, fecha.day) < (nacimiento.month, nacimiento.day)
    )


def grupo_por_edad(edad: int) -> GrupoEtario:
    if edad < 0:
        raise ValueError("La edad no puede ser negativa")
    if edad < 18:
        return GrupoEtario.nino
    if edad < 60:
        return GrupoEtario.adulto
    return GrupoEtario.adulto_mayor


def calcular_edad_meses(nacimiento: date, fecha: date | None = None) -> int:
    fecha = fecha or date.today()
    if nacimiento > fecha:
        raise ValueError("La fecha de nacimiento no puede ser futura")
    return (fecha.year - nacimiento.year) * 12 + fecha.month - nacimiento.month - (fecha.day < nacimiento.day)
