// Funciones puras del módulo de reportes (sin React): escalas, fechas, geometría de los
// gráficos y armado de filtros. Se prueban con `npm test` (tests/reportes.test.mjs).

// Colores de las bandas del modelo. Coinciden con las insignias del resto de la app
// (verde / ámbar / rojo) pero con tonos más oscuros para que se distingan en un gráfico.
export const BANDAS = [
  { clave: 'bajo', etiqueta: 'Bajo', color: '#2f855a' },
  { clave: 'moderado', etiqueta: 'Moderado', color: '#d69e2e' },
  { clave: 'alto', etiqueta: 'Alto', color: '#c53030' },
];

export const PERIODOS = [
  { dias: 7, etiqueta: '7 días' },
  { dias: 30, etiqueta: '30 días' },
  { dias: 90, etiqueta: '90 días' },
];

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

/** parte/total en % con 1 decimal. total 0 → 0 (nunca NaN). */
export const porcentaje = (parte, total, decimales = 1) => {
  const t = Number(total);
  if (!t || !Number.isFinite(t)) return 0;
  const factor = 10 ** decimales;
  return Math.round((Number(parte) / t) * 100 * factor) / factor;
};

/** Formato de miles para la interfaz en español: 12345 → "12 345". */
export const miles = (n) => Number(n ?? 0).toLocaleString('es-PE');

/**
 * "2026-11-05" → "05 nov". Se separa el texto a mano: new Date('2026-11-05') se interpreta
 * como UTC y en Perú (UTC-5) mostraría el día anterior.
 */
export const fechaCorta = (iso) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso ?? '');
  if (!m) return '';
  return `${m[3]} ${MESES[Number(m[2]) - 1] ?? ''}`.trim();
};

/** Fecha y hora legibles: "05/11/2026 08:30". Devuelve '' si el valor no es una fecha. */
export const fechaHora = (valor) => {
  const d = new Date(valor);
  if (Number.isNaN(d.getTime())) return '';
  const p = (n) => String(n).padStart(2, '0');
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
};

/**
 * Escala "bonita" para el eje Y: máximo y marcas en 1, 2, 5 × 10ⁿ.
 * escalaEje(37) → { max: 40, marcas: [0, 10, 20, 30, 40] }. Con máximo 0 devuelve 0..4 para que
 * el gráfico vacío siga dibujando ejes.
 */
export const escalaEje = (maximo, objetivo = 4) => {
  const m = Number(maximo);
  if (!Number.isFinite(m) || m <= 0) return { max: objetivo, marcas: Array.from({ length: objetivo + 1 }, (_, i) => i) };
  const bruto = m / objetivo;
  const potencia = 10 ** Math.floor(Math.log10(bruto));
  const f = bruto / potencia;
  const paso = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * potencia;
  const max = Math.round(Math.ceil(m / paso) * paso * 1e6) / 1e6;
  const marcas = [];
  for (let v = 0; v <= max + paso / 1e6; v += paso) marcas.push(Math.round(v * 1e6) / 1e6);
  return { max, marcas };
};

/** Índices del eje X que llevan etiqueta (siempre el primero y el último; el resto espaciado). */
export const indicesEtiquetas = (cantidad, maximo = 7) => {
  if (cantidad <= 0) return [];
  if (cantidad <= maximo) return Array.from({ length: cantidad }, (_, i) => i);
  const paso = (cantidad - 1) / (maximo - 1);
  const set = new Set(Array.from({ length: maximo }, (_, i) => Math.round(i * paso)));
  return [...set].sort((a, b) => a - b);
};

/** Ángulos (radianes, desde las 12 en punto, sentido horario) de cada segmento de la dona. */
export const segmentosDona = (conteos) => {
  const total = BANDAS.reduce((s, b) => s + Number(conteos?.[b.clave] ?? 0), 0);
  let acumulado = 0;
  return BANDAS.map((b) => {
    const valor = Number(conteos?.[b.clave] ?? 0);
    const inicio = total ? (acumulado / total) * Math.PI * 2 : 0;
    acumulado += valor;
    const fin = total ? (acumulado / total) * Math.PI * 2 : 0;
    return { ...b, valor, porcentaje: porcentaje(valor, total), inicio, fin };
  });
};

const punto = (cx, cy, r, ang) => [cx + r * Math.sin(ang), cy - r * Math.cos(ang)];

/**
 * Path SVG de un sector de dona. Un sector que ocupa el 100 % se parte en dos mitades porque
 * un arco SVG con inicio = fin no se dibuja.
 */
export const trayectoSector = (cx, cy, rExt, rInt, inicio, fin) => {
  if (fin - inicio <= 0) return '';
  if (fin - inicio >= Math.PI * 2 - 1e-6) {
    return `${trayectoSector(cx, cy, rExt, rInt, 0, Math.PI)} ${trayectoSector(cx, cy, rExt, rInt, Math.PI, Math.PI * 2)}`;
  }
  const grande = fin - inicio > Math.PI ? 1 : 0;
  const [x1, y1] = punto(cx, cy, rExt, inicio);
  const [x2, y2] = punto(cx, cy, rExt, fin);
  const [x3, y3] = punto(cx, cy, rInt, fin);
  const [x4, y4] = punto(cx, cy, rInt, inicio);
  const f = (n) => Number(n.toFixed(3));
  return `M${f(x1)} ${f(y1)} A${rExt} ${rExt} 0 ${grande} 1 ${f(x2)} ${f(y2)} L${f(x3)} ${f(y3)} A${rInt} ${rInt} 0 ${grande} 0 ${f(x4)} ${f(y4)} Z`;
};

/** Resumen de la serie diaria: total, promedio por día y día con más evaluaciones. */
export const resumenSerie = (serie = []) => {
  const total = serie.reduce((s, p) => s + p.total, 0);
  const pico = serie.reduce((mejor, p) => (p.total > (mejor?.total ?? 0) ? p : mejor), null);
  return {
    total,
    promedioDiario: serie.length ? Math.round((total / serie.length) * 10) / 10 : 0,
    pico: pico ? { fecha: pico.fecha, total: pico.total } : null,
  };
};

/** Quita del objeto de filtros lo que esté vacío para no enviar `?q=&desde=` al backend. */
export const parametrosFiltros = (filtros = {}) =>
  Object.fromEntries(
    Object.entries(filtros).filter(([, v]) => v !== '' && v !== null && v !== undefined)
  );

/** ¿Hay algún filtro activo? (para mostrar el botón "Limpiar"). */
export const hayFiltros = (filtros = {}) => Object.keys(parametrosFiltros(filtros)).length > 0;
