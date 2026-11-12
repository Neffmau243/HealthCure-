import { miles, segmentosDona, trayectoSector } from '../../utils/reportes';

// Distribución de las evaluaciones por banda del modelo (bajo / moderado / alto).
export default function GraficoDona({ distribucion }) {
  const segmentos = segmentosDona(distribucion);
  const total = segmentos.reduce((s, x) => s + x.valor, 0);

  return (
    <figure className="flex flex-col items-center gap-5 sm:flex-row sm:items-center sm:justify-center xl:flex-col">
      <svg viewBox="0 0 120 120" role="img" className="w-40 h-40 shrink-0"
        aria-label={`Distribución por banda: ${segmentos.map((s) => `${s.etiqueta} ${s.valor}`).join(', ')}`}>
        {total === 0 ? (
          <circle cx="60" cy="60" r="42.5" fill="none" stroke="#e5ecf1" strokeWidth="17" />
        ) : (
          segmentos.map((s) => (
            <path key={s.clave} d={trayectoSector(60, 60, 51, 34, s.inicio, s.fin)} fill={s.color} stroke="#fff" strokeWidth="1.5">
              <title>{`${s.etiqueta}: ${s.valor} (${s.porcentaje} %)`}</title>
            </path>
          ))
        )}
        <text x="60" y="58" textAnchor="middle" fontSize="20" fontWeight="500" fill="#17324c">{miles(total)}</text>
        <text x="60" y="73" textAnchor="middle" fontSize="8.5" fill="#536577">evaluaciones</text>
      </svg>
      <figcaption className="w-full max-w-60">
        <ul className="space-y-2.5 text-sm">
          {segmentos.map((s) => (
            <li key={s.clave} className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-2 text-slate-700">
                <i className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: s.color }} aria-hidden="true" />
                {s.etiqueta}
              </span>
              <span className="tabular-nums text-slate-900">
                <b className="font-medium">{miles(s.valor)}</b>
                <span className="text-slate-500 text-xs ml-1.5">{s.porcentaje} %</span>
              </span>
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  );
}
