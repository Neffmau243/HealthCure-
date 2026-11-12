import { BANDAS, porcentaje } from '../../utils/reportes';

/** Una barra al 100 % dividida por banda (bajo / moderado / alto): sirve para comparar grupos de edad. */
export default function BarraApilada({ etiqueta, fila }) {
  const total = fila.total;
  return (
    <li>
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="text-slate-800">{etiqueta}</span>
        <span className="tabular-nums text-slate-500 text-xs">{total} {total === 1 ? 'evaluación' : 'evaluaciones'}</span>
      </div>
      <div className="report-bar-track mt-1.5 flex" role="img"
        aria-label={`${etiqueta}: ${BANDAS.map((b) => `${b.etiqueta} ${fila[b.clave]}`).join(', ')}`}>
        {total > 0 && BANDAS.map((b) => fila[b.clave] > 0 && (
          <div key={b.clave} style={{ width: `${porcentaje(fila[b.clave], total, 4)}%`, background: b.color }}
            title={`${b.etiqueta}: ${fila[b.clave]} (${porcentaje(fila[b.clave], total)} %)`} />
        ))}
      </div>
    </li>
  );
}
