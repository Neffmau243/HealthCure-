"""
analitica_service.py — SERVICIO: DASHBOARD ANALÍTICO Y REPORTES DE EVALUACIONES

(No confundir con reporte_service.py, que genera el PDF del FUA.)

Convierte los agregados SQL del repositorio en las estructuras que dibuja el
frontend: rellena con ceros los días sin evaluaciones (para que el gráfico de
tendencia no "salte" fechas), calcula porcentajes y arma la exportación CSV.
"""
import csv
import io
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.reporte_repository import FACTORES, ReporteRepository
from app.schemas.reporte import (
    ConteoBandas, DashboardReporte, FilaEvaluacion, ItemDistrito, ItemFactor,
    ItemGrupoEdad, KpisReporte, PaginaEvaluaciones, PuntoDiario,
)

PERIODOS_PERMITIDOS = (7, 14, 30, 90, 180, 365)
MAX_FILAS_EXPORTACION = 50_000


def _porcentaje(parte: int, total: int) -> float:
    return round(parte * 100 / total, 1) if total else 0.0


def _celda_segura(valor) -> str:
    """Evita 'inyección de fórmulas' en Excel: texto que empieza con = + - @ se neutraliza."""
    texto = "" if valor is None else str(valor)
    return "'" + texto if texto[:1] in ("=", "+", "-", "@", "\t", "\r") else texto


class AnaliticaService:
    def __init__(self, db: Session):
        self.repo = ReporteRepository(db)

    # ── Dashboard ─────────────────────────────────────────────────────────
    def dashboard(self, dias: int = 30, hoy: Optional[date] = None) -> DashboardReporte:
        if dias not in PERIODOS_PERMITIDOS:
            raise ValueError(f"El periodo debe ser uno de: {', '.join(map(str, PERIODOS_PERMITIDOS))} días")
        hoy = hoy or date.today()
        desde = hoy - timedelta(days=dias - 1)

        bandas = self.repo.distribucion(desde, hoy)
        distribucion = ConteoBandas(bajo=bandas.get("bajo", 0), moderado=bandas.get("moderado", 0),
                                    alto=bandas.get("alto", 0))
        agregados = self.repo.kpis(desde, hoy)
        total = agregados["evaluaciones"]

        por_dia = self.repo.serie_diaria(desde, hoy)
        serie = []
        for i in range(dias):                              # un punto por día, aunque esté vacío
            d = desde + timedelta(days=i)
            c = por_dia.get(d.isoformat(), {})
            serie.append(PuntoDiario(fecha=d, total=sum(c.values()), bajo=c.get("bajo", 0),
                                     moderado=c.get("moderado", 0), alto=c.get("alto", 0)))

        factores_bd = self.repo.factores(desde, hoy)
        factores = sorted(
            (ItemFactor(clave=k, etiqueta=e, cantidad=factores_bd[k], porcentaje=_porcentaje(factores_bd[k], total))
             for k, e, _p in FACTORES),
            key=lambda f: f.cantidad, reverse=True,
        )

        return DashboardReporte(
            periodo_dias=dias, desde=desde, hasta=hoy,
            kpis=KpisReporte(
                pacientes_registrados=self.repo.pacientes_activos(),
                evaluaciones=total,
                evaluaciones_hoy=self.repo.contar_hoy(hoy),
                pacientes_evaluados=agregados["pacientes_evaluados"],
                riesgo_alto=distribucion.alto, riesgo_moderado=distribucion.moderado,
                riesgo_bajo=distribucion.bajo,
                porcentaje_alto=_porcentaje(distribucion.alto, total),
                indice_promedio=round(agregados["indice_promedio"], 1),
            ),
            serie_diaria=serie,
            distribucion=distribucion,
            por_distrito=[ItemDistrito(**d) for d in self.repo.por_distrito(desde, hoy)],
            factores=factores,
            por_grupo_edad=[ItemGrupoEdad(**g) for g in self.repo.por_grupo_edad(desde, hoy)],
            generado_en=datetime.now(),
        )

    # ── Tabla filtrable ───────────────────────────────────────────────────
    @staticmethod
    def _validar_rango(desde: Optional[date], hasta: Optional[date]) -> None:
        if desde and hasta and desde > hasta:
            raise ValueError("La fecha inicial no puede ser posterior a la final")

    def listar(self, desde=None, hasta=None, clasificacion=None, distrito_id=None, busqueda=None,
               limit: int = 20, offset: int = 0) -> PaginaEvaluaciones:
        self._validar_rango(desde, hasta)
        total, filas = self.repo.listar(desde, hasta, clasificacion, distrito_id, busqueda, limit, offset)
        items = []
        for e in filas:
            p = e.paciente
            alerta = e.alerta_clinica.get("titulo") if isinstance(e.alerta_clinica, dict) else None
            items.append(FilaEvaluacion(
                id=e.id, fecha=e.created_at, paciente_id=p.id, paciente=p.nombre_completo,
                documento=p.documento_identidad, edad=e.edad,
                distrito=p.distrito.nombre if p.distrito else None,
                clasificacion=str(e.clasificacion), indice=round(float(e.probabilidad) * 100, 1),
                alerta=alerta,
            ))
        return PaginaEvaluaciones(total=total, limit=limit, offset=offset, items=items)

    # ── Exportación CSV (sin datos personales) ───────────────────────────
    def exportar_csv(self, desde=None, hasta=None, clasificacion=None, distrito_id=None, busqueda=None) -> str:
        """
        CSV para análisis externo. NO incluye nombre, documento ni teléfono del
        paciente: solo un identificador de evaluación y variables clínicas/demográficas.
        Lleva BOM UTF-8 para que Excel respete las tildes.
        """
        self._validar_rango(desde, hasta)
        filas = self.repo.para_exportar(desde, hasta, clasificacion, distrito_id, busqueda, MAX_FILAS_EXPORTACION)
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\r\n")
        w.writerow(["id_evaluacion", "fecha", "edad", "sexo", "distrito", "banda_modelo", "indice_0_100",
                    "presion_alta", "colesterol_alto", "tabaquismo", "actividad_fisica", "antecedente_acv",
                    "diabetes", "dificultad_para_caminar", "salud_general_1_5", "nivel_alerta_clinica"])
        si_no = lambda v: "si" if v else "no"   # noqa: E731
        for e in filas:
            p = e.paciente
            nivel = e.alerta_clinica.get("nivel") if isinstance(e.alerta_clinica, dict) else ""
            w.writerow([
                e.id, e.created_at.strftime("%Y-%m-%d %H:%M"), e.edad, p.sexo or "",
                _celda_segura(p.distrito.nombre if p.distrito else ""), e.clasificacion,
                f"{float(e.probabilidad) * 100:.1f}", si_no(e.presion_alta), si_no(e.colesterol_alto),
                si_no(e.tabaquismo), si_no(e.actividad_fisica), si_no(e.antecedente_acv),
                si_no(e.diabetes), si_no(e.dificultad_para_caminar), e.salud_general,
                _celda_segura(nivel),
            ])
        return "﻿" + buf.getvalue()
