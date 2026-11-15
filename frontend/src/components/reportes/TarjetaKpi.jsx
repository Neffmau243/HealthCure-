/** Indicador numérico con título y una línea de contexto. */
export default function TarjetaKpi({ titulo, valor, detalle, icono: Icono, tono = 'text-sky-700 bg-sky-50' }) {
  return (
    <div className="report-kpi">
      <div className="flex items-center gap-2.5 text-xs text-slate-600">
        {Icono && <span className={`grid place-items-center w-8 h-8 rounded-lg ${tono}`}><Icono className="w-4 h-4" aria-hidden="true" /></span>}
        <span>{titulo}</span>
      </div>
      <p className="report-kpi-value">{valor}</p>
      {detalle && <p className="text-xs text-slate-500 mt-1.5">{detalle}</p>}
    </div>
  );
}
