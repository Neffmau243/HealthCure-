import { miles } from '../../utils/reportes';

/**
 * Lista de barras horizontales (HTML/CSS: accesible, selecciona texto y se adapta solo).
 * items: [{ id, etiqueta, valor, extra?, destacado? }]
 *   - `valor` es lo que mide la barra; `destacado` (≤ valor) se pinta en rojo dentro de la barra.
 *   - `escalaMax` fija el 100 % (p. ej. 100 si los valores son porcentajes).
 */
export default function BarrasHorizontales({ items, formato = miles, escalaMax, color = '#2b6f8a', colorDestacado = '#c53030', vacio = 'Sin datos en este periodo.' }) {
  const max = escalaMax ?? Math.max(1, ...items.map((i) => i.valor));
  if (!items.length || items.every((i) => !i.valor)) {
    return <p className="text-sm text-slate-500 py-6 text-center">{vacio}</p>;
  }
  return (
    <ul className="space-y-3.5">
      {items.map((i) => (
        <li key={i.id ?? i.etiqueta}>
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="text-slate-800 truncate" title={i.etiqueta}>{i.etiqueta}</span>
            <span className="tabular-nums text-slate-900 shrink-0">
              <b className="font-medium">{formato(i.valor)}</b>
              {i.extra && <span className="text-slate-500 text-xs ml-1.5">{i.extra}</span>}
            </span>
          </div>
          <div className="report-bar-track mt-1.5" role="img" aria-label={`${i.etiqueta}: ${formato(i.valor)}`}>
            <div className="report-bar" style={{ width: `${(i.valor / max) * 100}%`, background: color }}>
              {i.destacado > 0 && (
                <div className="report-bar-hl" style={{ width: `${Math.min(100, (i.destacado / i.valor) * 100)}%`, background: colorDestacado }} />
              )}
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
