"""
reportes.py — ENDPOINTS DEL DASHBOARD ANALÍTICO Y REPORTES

Rutas (todas requieren JWT):
  GET /api/v1/reportes/dashboard?dias=30          → KPIs, tendencia, bandas, distritos, factores
  GET /api/v1/reportes/evaluaciones               → tabla filtrable y paginada
  GET /api/v1/reportes/evaluaciones/export        → CSV sin datos personales (solo ADMIN)

Los números salen de consultas agregadas en SQL, no de contar filas en el navegador.
"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.schemas.reporte import DashboardReporte, PaginaEvaluaciones
from app.services.analitica_service import PERIODOS_PERMITIDOS, AnaliticaService

router = APIRouter(prefix="/reportes", tags=["Reportes y Dashboard"])

Banda = Query(default=None, pattern="^(bajo|moderado|alto)$", description="Banda del modelo")


def _bad_request(e: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/dashboard", response_model=DashboardReporte)
def dashboard(
    dias: int = Query(default=30, description=f"Periodo en días: {', '.join(map(str, PERIODOS_PERMITIDOS))}"),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Indicadores y series para los gráficos del periodo (termina hoy)."""
    try:
        return AnaliticaService(db).dashboard(dias)
    except ValueError as e:
        raise _bad_request(e)


@router.get("/evaluaciones", response_model=PaginaEvaluaciones)
def tabla_evaluaciones(
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    clasificacion: Optional[str] = Banda,
    distrito_id: Optional[int] = Query(default=None, ge=1),
    q: Optional[str] = Query(default=None, max_length=80, description="Nombre o documento del paciente"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Evaluaciones filtradas por fechas, banda, distrito o texto, más recientes primero."""
    try:
        return AnaliticaService(db).listar(desde, hasta, clasificacion, distrito_id, q, limit, offset)
    except ValueError as e:
        raise _bad_request(e)


@router.get("/evaluaciones/export")
def exportar_evaluaciones(
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    clasificacion: Optional[str] = Banda,
    distrito_id: Optional[int] = Query(default=None, ge=1),
    q: Optional[str] = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """CSV descargable con los mismos filtros. Solo administradores; sin nombres ni documentos."""
    try:
        contenido = AnaliticaService(db).exportar_csv(desde, hasta, clasificacion, distrito_id, q)
    except ValueError as e:
        raise _bad_request(e)
    nombre = f"evaluaciones_{datetime.now():%Y%m%d_%H%M}.csv"
    return Response(
        content=contenido.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
