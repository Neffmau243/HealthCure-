/** Indicador numérico con título y una línea de contexto. */
export default function TarjetaKpi({ titulo, valor, detalle, icono: Icono }) {
  return (
    <div className="report-kpi">
      <div className="report-kpi-label">
        {Icono && <Icono className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />}
        <span>{titulo}</span>
      </div>
      <p className="report-kpi-value">{valor}</p>
      {detalle && <p className="text-xs text-slate-500 mt-1.5">{detalle}</p>}
    </div>
  );
}
