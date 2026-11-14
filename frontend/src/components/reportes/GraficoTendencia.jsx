import { BANDAS, escalaEje, fechaCorta, indicesEtiquetas } from '../../utils/reportes';

// Columnas apiladas: una por día, divididas por banda del modelo.
// viewBox fijo (se escala con el ancho de la tarjeta) para que se vea igual en móvil y escritorio.
const W = 640;
const H = 250;
const M = { arriba: 12, derecha: 8, abajo: 28, izquierda: 34 };

export default function GraficoTendencia({ serie, titulo = 'Evaluaciones por día', alturaMax }) {
  const maxDia = Math.max(0, ...serie.map((p) => p.total));
  const { max, marcas } = escalaEje(maxDia);
  const areaW = W - M.izquierda - M.derecha;
  const areaH = H - M.arriba - M.abajo;
  const paso = areaW / Math.max(serie.length, 1);
  const ancho = Math.min(Math.max(paso * 0.68, 2), 26);
  const y = (v) => M.arriba + areaH - (v / max) * areaH;
  const etiquetados = new Set(indicesEtiquetas(serie.length, serie.length > 14 ? 7 : serie.length > 7 ? 8 : 7));
  const total = serie.reduce((s, p) => s + p.total, 0);

  return (
    <figure>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" className="w-full h-auto" style={alturaMax ? { maxHeight: alturaMax } : undefined}
        aria-label={`${titulo}: ${total} evaluaciones en ${serie.length} días`}>
        {marcas.map((m) => (
          <g key={m}>
            <line x1={M.izquierda} x2={W - M.derecha} y1={y(m)} y2={y(m)} stroke="#dce5eb" strokeWidth="1" />
            <text x={M.izquierda - 8} y={y(m) + 4} textAnchor="end" fontSize="11" fill="#536577">{m}</text>
          </g>
        ))}
        {serie.map((p, i) => {
          const x = M.izquierda + paso * i + (paso - ancho) / 2;
          let base = 0;
          return (
            <g key={p.fecha}>
              <title>{`${fechaCorta(p.fecha)}: ${p.total} evaluaciones (bajo ${p.bajo}, moderado ${p.moderado}, alto ${p.alto})`}</title>
              {BANDAS.map((b) => {
                const valor = p[b.clave];
                if (!valor) return null;
                const alto = (valor / max) * areaH;
                const yy = y(base + valor);
                base += valor;
                return <rect key={b.clave} x={x} y={yy} width={ancho} height={alto} fill={b.color} rx="1.5" stroke="#fff" strokeWidth="0.75" />;
              })}
              {etiquetados.has(i) && (
                <text x={x + ancho / 2} y={H - 8} textAnchor="middle" fontSize="11" fill="#536577">{fechaCorta(p.fecha)}</text>
              )}
            </g>
          );
        })}
        <line x1={M.izquierda} x2={W - M.derecha} y1={y(0)} y2={y(0)} stroke="#9aafbd" strokeWidth="1" />
      </svg>
      <figcaption className="report-legend">
        {BANDAS.map((b) => (
          <span key={b.clave}><i style={{ background: b.color }} aria-hidden="true" />{b.etiqueta}</span>
        ))}
      </figcaption>
      {/* Alternativa para lectores de pantalla: los mismos datos en tabla. */}
      <table className="sr-only">
        <caption>{titulo}</caption>
        <thead><tr><th>Fecha</th><th>Total</th><th>Bajo</th><th>Moderado</th><th>Alto</th></tr></thead>
        <tbody>
          {serie.map((p) => (
            <tr key={p.fecha}><td>{p.fecha}</td><td>{p.total}</td><td>{p.bajo}</td><td>{p.moderado}</td><td>{p.alto}</td></tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
