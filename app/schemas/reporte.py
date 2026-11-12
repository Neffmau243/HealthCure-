"""
reporte.py — SCHEMAS: RESPUESTAS DE LOS REPORTES Y EL DASHBOARD ANALÍTICO

Son solo contratos de salida (Pydantic): el backend calcula los agregados con SQL
y el frontend los dibuja. Ninguno de estos esquemas devuelve datos de contacto
de pacientes; la tabla de evaluaciones muestra el nombre porque el personal de
salud ya puede verlo en /evaluaciones, y la exportación CSV NO lo incluye.
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class KpisReporte(BaseModel):
    """Cifras clave del periodo consultado."""
    pacientes_registrados: int = Field(description="Pacientes activos (total, sin filtro de fechas)")
    evaluaciones: int = Field(description="Evaluaciones dentro del periodo")
    evaluaciones_hoy: int
    pacientes_evaluados: int = Field(description="Pacientes distintos evaluados en el periodo")
    riesgo_alto: int
    riesgo_moderado: int
    riesgo_bajo: int
    porcentaje_alto: float = Field(description="% de evaluaciones con banda alta (0-100)")
    indice_promedio: float = Field(description="Promedio del índice del modelo (0-100)")


class PuntoDiario(BaseModel):
    """Evaluaciones de un día, separadas por banda del modelo."""
    fecha: date
    total: int
    bajo: int
    moderado: int
    alto: int


class ConteoBandas(BaseModel):
    bajo: int = 0
    moderado: int = 0
    alto: int = 0


class ItemDistrito(BaseModel):
    distrito: str
    evaluaciones: int
    pacientes: int
    alto: int


class ItemFactor(BaseModel):
    """Cuántas evaluaciones del periodo registran este factor."""
    clave: str
    etiqueta: str
    cantidad: int
    porcentaje: float


class ItemGrupoEdad(BaseModel):
    grupo: str
    total: int
    bajo: int
    moderado: int
    alto: int


class DashboardReporte(BaseModel):
    periodo_dias: int
    desde: date
    hasta: date
    kpis: KpisReporte
    serie_diaria: list[PuntoDiario]
    distribucion: ConteoBandas
    por_distrito: list[ItemDistrito]
    factores: list[ItemFactor]
    por_grupo_edad: list[ItemGrupoEdad]
    generado_en: datetime


class FilaEvaluacion(BaseModel):
    id: int
    fecha: datetime
    paciente_id: int
    paciente: str
    documento: str
    edad: int
    distrito: Optional[str] = None
    clasificacion: str
    indice: float = Field(description="Índice del modelo, 0-100 (no es probabilidad de enfermedad)")
    alerta: Optional[str] = Field(default=None, description="Título de la alerta clínica, si se revisó")


class PaginaEvaluaciones(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[FilaEvaluacion]
