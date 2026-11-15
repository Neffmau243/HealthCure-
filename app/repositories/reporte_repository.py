"""
reporte_repository.py — REPOSITORY: CONSULTAS AGREGADAS PARA REPORTES

Todo se resuelve con GROUP BY / COUNT / SUM en la base de datos: nunca se traen
miles de filas al servidor para contarlas en Python. Las fechas se filtran con
rangos semiabiertos [desde, hasta+1) sobre created_at, que usa el índice
ix_evaluaciones_created_at. Las funciones usadas (date, count, sum, case, avg)
son estándar y funcionan igual en MySQL (producción) y SQLite (tests).
"""
from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy import Integer, and_, case, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.distrito import Distrito
from app.models.evaluacion import Evaluacion
from app.models.paciente import Paciente

# Bandas de edad del reporte (años cumplidos al momento de la evaluación).
GRUPOS_EDAD = (
    ("0-17", 0, 17),
    ("18-39", 18, 39),
    ("40-59", 40, 59),
    ("60+", 60, 200),
)

# Factores que se resumen: clave en BD → (etiqueta, True si el factor es "valor verdadero").
# Sedentarismo es la ausencia de actividad física.
FACTORES = (
    ("presion_alta", "Presión alta", True),
    ("colesterol_alto", "Colesterol alto", True),
    ("tabaquismo", "Tabaquismo", True),
    ("diabetes", "Diabetes", True),
    ("antecedente_acv", "Antecedente de ACV", True),
    ("dificultad_para_caminar", "Dificultad para caminar", True),
    ("actividad_fisica", "Sedentarismo", False),
)


def _rango(desde: date, hasta: date) -> tuple[datetime, datetime]:
    """[desde 00:00, hasta+1 00:00) para filtrar created_at."""
    return datetime.combine(desde, time.min), datetime.combine(hasta + timedelta(days=1), time.min)


class ReporteRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Filtros compartidos ────────────────────────────────────────────────
    @staticmethod
    def _condiciones(desde: Optional[date], hasta: Optional[date], clasificacion: Optional[str] = None,
                     distrito_id: Optional[int] = None, busqueda: Optional[str] = None) -> list:
        cond = []
        if desde:
            cond.append(Evaluacion.created_at >= datetime.combine(desde, time.min))
        if hasta:
            cond.append(Evaluacion.created_at < datetime.combine(hasta + timedelta(days=1), time.min))
        if clasificacion:
            cond.append(Evaluacion.clasificacion == clasificacion)
        if distrito_id:
            cond.append(Paciente.distrito_id == distrito_id)
        if busqueda:
            patron = f"%{busqueda.strip().lower()}%"
            cond.append(or_(
                func.lower(Paciente.nombres).like(patron),
                func.lower(Paciente.apellido_paterno).like(patron),
                func.lower(Paciente.apellido_materno).like(patron),
                Paciente.documento_identidad.like(f"%{busqueda.strip()}%"),
            ))
        return cond

    # ── Agregados del dashboard ───────────────────────────────────────────
    def pacientes_activos(self) -> int:
        return int(self.db.query(func.count(Paciente.id)).filter(Paciente.activo.is_(True)).scalar() or 0)

    def kpis(self, desde: date, hasta: date) -> dict:
        ini, fin = _rango(desde, hasta)
        total, pacientes, promedio = self.db.query(
            func.count(Evaluacion.id),
            func.count(func.distinct(Evaluacion.paciente_id)),
            func.avg(Evaluacion.probabilidad),
        ).filter(Evaluacion.created_at >= ini, Evaluacion.created_at < fin).one()
        return {
            "evaluaciones": int(total or 0),
            "pacientes_evaluados": int(pacientes or 0),
            "indice_promedio": float(promedio or 0) * 100,
        }

    def contar_hoy(self, hoy: date) -> int:
        ini, fin = _rango(hoy, hoy)
        return int(self.db.query(func.count(Evaluacion.id))
                   .filter(Evaluacion.created_at >= ini, Evaluacion.created_at < fin).scalar() or 0)

    def serie_diaria(self, desde: date, hasta: date) -> dict[str, dict[str, int]]:
        """{'2026-11-03': {'bajo': n, 'moderado': n, 'alto': n}, ...} solo días con datos."""
        ini, fin = _rango(desde, hasta)
        dia = func.date(Evaluacion.created_at)
        filas = (
            self.db.query(dia, Evaluacion.clasificacion, func.count(Evaluacion.id))
            .filter(Evaluacion.created_at >= ini, Evaluacion.created_at < fin)
            .group_by(dia, Evaluacion.clasificacion)
            .all()
        )
        salida: dict[str, dict[str, int]] = {}
        for fecha, banda, n in filas:
            salida.setdefault(str(fecha)[:10], {})[str(banda)] = int(n)
        return salida

    def distribucion(self, desde: date, hasta: date) -> dict[str, int]:
        ini, fin = _rango(desde, hasta)
        filas = (
            self.db.query(Evaluacion.clasificacion, func.count(Evaluacion.id))
            .filter(Evaluacion.created_at >= ini, Evaluacion.created_at < fin)
            .group_by(Evaluacion.clasificacion).all()
        )
        return {str(b): int(n) for b, n in filas}

    def por_distrito(self, desde: date, hasta: date, limite: int = 8) -> list[dict]:
        """Evaluaciones, pacientes distintos y casos de banda alta por distrito (top N)."""
        ini, fin = _rango(desde, hasta)
        # Se agrupa por columnas reales (no por una expresión con parámetros) para que
        # MySQL con ONLY_FULL_GROUP_BY lo acepte; el nombre "Sin distrito" se pone en Python.
        evaluaciones = func.count(Evaluacion.id)
        filas = (
            self.db.query(
                Distrito.nombre,
                evaluaciones,
                func.count(func.distinct(Evaluacion.paciente_id)),
                func.sum(case((Evaluacion.clasificacion == "alto", 1), else_=0)),
            )
            .select_from(Evaluacion)
            .join(Paciente, Paciente.id == Evaluacion.paciente_id)
            .outerjoin(Distrito, Distrito.id == Paciente.distrito_id)
            .filter(Evaluacion.created_at >= ini, Evaluacion.created_at < fin)
            .group_by(Distrito.id, Distrito.nombre)
            .order_by(evaluaciones.desc(), Distrito.nombre.asc())
            .limit(limite)
            .all()
        )
        return [{"distrito": d or "Sin distrito", "evaluaciones": int(e), "pacientes": int(p), "alto": int(a or 0)}
                for d, e, p, a in filas]

    def factores(self, desde: date, hasta: date) -> dict[str, int]:
        """Cuántas evaluaciones del periodo tienen cada factor (una sola consulta)."""
        ini, fin = _rango(desde, hasta)
        columnas = []
        for clave, _etiqueta, presente_si_verdadero in FACTORES:
            col = getattr(Evaluacion, clave)
            columnas.append(func.sum(case((col.is_(presente_si_verdadero), 1), else_=0)))
        fila = (self.db.query(*columnas)
                .filter(Evaluacion.created_at >= ini, Evaluacion.created_at < fin).one())
        return {clave: int(v or 0) for (clave, _e, _p), v in zip(FACTORES, fila)}

    def por_grupo_edad(self, desde: date, hasta: date) -> list[dict]:
        ini, fin = _rango(desde, hasta)
        salida = []
        for nombre, minimo, maximo in GRUPOS_EDAD:
            en_grupo = and_(Evaluacion.edad >= minimo, Evaluacion.edad <= maximo)
            fila = (
                self.db.query(
                    func.count(Evaluacion.id),
                    func.sum(case((Evaluacion.clasificacion == "bajo", 1), else_=0)),
                    func.sum(case((Evaluacion.clasificacion == "moderado", 1), else_=0)),
                    func.sum(case((Evaluacion.clasificacion == "alto", 1), else_=0)),
                )
                .filter(Evaluacion.created_at >= ini, Evaluacion.created_at < fin, en_grupo).one()
            )
            salida.append({"grupo": nombre, "total": int(fila[0] or 0), "bajo": int(fila[1] or 0),
                           "moderado": int(fila[2] or 0), "alto": int(fila[3] or 0)})
        return salida

    # ── Tabla filtrable / exportación ────────────────────────────────────
    def _consulta_filas(self, desde, hasta, clasificacion, distrito_id, busqueda):
        q = (self.db.query(Evaluacion)
             .join(Paciente, Paciente.id == Evaluacion.paciente_id)
             .options(joinedload(Evaluacion.paciente).joinedload(Paciente.distrito)))
        for c in self._condiciones(desde, hasta, clasificacion, distrito_id, busqueda):
            q = q.filter(c)
        return q

    def listar(self, desde, hasta, clasificacion, distrito_id, busqueda, limit: int, offset: int):
        q = self._consulta_filas(desde, hasta, clasificacion, distrito_id, busqueda)
        total = q.with_entities(func.count(Evaluacion.id)).order_by(None).scalar() or 0
        filas = (q.order_by(Evaluacion.created_at.desc(), Evaluacion.id.desc())
                 .limit(limit).offset(offset).all())
        return int(total), filas

    def para_exportar(self, desde, hasta, clasificacion, distrito_id, busqueda, maximo: int):
        q = self._consulta_filas(desde, hasta, clasificacion, distrito_id, busqueda)
        return q.order_by(Evaluacion.created_at.desc(), Evaluacion.id.desc()).limit(maximo).all()
