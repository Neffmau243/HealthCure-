import { useCallback, useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Download, Search, X } from 'lucide-react';
import { reportesService } from '../../services/reportes';
import { catalogosService } from '../../services/catalogos';
import { mensajeError } from '../../services/api';
import { Alerta, Cargando } from '../ui/Feedback';
import { clasesClasificacion } from '../../utils/triaje';
import { fechaHora, hayFiltros, miles } from '../../utils/reportes';

const POR_PAGINA = 10;
const FILTROS_VACIOS = { q: '', desde: '', hasta: '', clasificacion: '', distrito_id: '' };

/** Tabla de evaluaciones con filtros, paginación en servidor y exportación CSV (solo admin). */
export default function TablaEvaluaciones({ puedeExportar }) {
  const [filtros, setFiltros] = useState(FILTROS_VACIOS);
  const [aplicados, setAplicados] = useState(FILTROS_VACIOS);   // los que realmente se consultaron
  const [pagina, setPagina] = useState(0);
  const [datos, setDatos] = useState({ total: 0, items: [] });
  const [distritos, setDistritos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [exportando, setExportando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    catalogosService.distritos().then(setDistritos).catch(() => setDistritos([]));
  }, []);

  useEffect(() => {
    const controlador = new AbortController();
    (async () => {
      setCargando(true);
      try {
        const r = await reportesService.evaluaciones(aplicados, { limit: POR_PAGINA, offset: pagina * POR_PAGINA, signal: controlador.signal });
        setDatos(r);
        setError(null);
      } catch (e) {
        if (e.code !== 'ERR_CANCELED') setError(mensajeError(e, 'No se pudo cargar la tabla de evaluaciones'));
      } finally {
        if (!controlador.signal.aborted) setCargando(false);
      }
    })();
    return () => controlador.abort();
  }, [aplicados, pagina]);

  const cambiar = (campo) => (e) => setFiltros((f) => ({ ...f, [campo]: e.target.value }));
  const buscar = (e) => { e.preventDefault(); setPagina(0); setAplicados(filtros); };
  const limpiar = () => { setFiltros(FILTROS_VACIOS); setAplicados(FILTROS_VACIOS); setPagina(0); };

  const exportar = useCallback(async () => {
    setExportando(true);
    try { await reportesService.exportarCsv(aplicados); }
    catch (e) { setError(mensajeError(e, 'No se pudo exportar el archivo')); }
    finally { setExportando(false); }
  }, [aplicados]);

  const totalPaginas = Math.max(1, Math.ceil(datos.total / POR_PAGINA));
  const desdeN = datos.total === 0 ? 0 : pagina * POR_PAGINA + 1;
  const hastaN = Math.min(datos.total, (pagina + 1) * POR_PAGINA);
  const rangoInvalido = filtros.desde && filtros.hasta && filtros.desde > filtros.hasta;

  return (
    <section className="clinical-panel" aria-labelledby="titulo-tabla-eval">
      <div className="p-5 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="titulo-tabla-eval" className="font-semibold text-slate-800">Detalle de evaluaciones</h2>
          <p className="text-xs text-slate-500 mt-1">Filtra por fecha, banda del modelo, distrito o paciente.</p>
        </div>
        {puedeExportar && (
          <button type="button" onClick={exportar} disabled={exportando || datos.total === 0}
            className="report-btn" title="Descarga un CSV sin nombres ni documentos">
            <Download className="w-4 h-4" aria-hidden="true" />{exportando ? 'Exportando…' : 'Exportar CSV'}
          </button>
        )}
      </div>

      <form onSubmit={buscar} className="report-filtros" aria-label="Filtros de evaluaciones">
        <label className="report-campo report-campo-q">
          <span>Paciente o documento</span>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input type="search" value={filtros.q} onChange={cambiar('q')} maxLength={80} placeholder="Nombre o DNI" className="report-input report-input-icono" />
          </div>
        </label>
        <label className="report-campo"><span>Desde</span><input type="date" value={filtros.desde} onChange={cambiar('desde')} className="report-input" /></label>
        <label className="report-campo"><span>Hasta</span><input type="date" value={filtros.hasta} onChange={cambiar('hasta')} className="report-input" /></label>
        <label className="report-campo">
          <span>Banda del modelo</span>
          <select value={filtros.clasificacion} onChange={cambiar('clasificacion')} className="report-input">
            <option value="">Todas</option><option value="bajo">Bajo</option><option value="moderado">Moderado</option><option value="alto">Alto</option>
          </select>
        </label>
        <label className="report-campo">
          <span>Distrito</span>
          <select value={filtros.distrito_id} onChange={cambiar('distrito_id')} className="report-input">
            <option value="">Todos</option>
            {distritos.map((d) => <option key={d.id} value={d.id}>{d.nombre}</option>)}
          </select>
        </label>
        <div className="report-filtros-acciones">
          <button type="submit" className="report-btn report-btn-primario" disabled={rangoInvalido}>Aplicar</button>
          {(hayFiltros(filtros) || hayFiltros(aplicados)) && (
            <button type="button" onClick={limpiar} className="report-btn"><X className="w-4 h-4" aria-hidden="true" />Limpiar</button>
          )}
        </div>
        {rangoInvalido && <p className="text-xs text-rose-700 col-span-full" role="alert">La fecha inicial no puede ser posterior a la final.</p>}
      </form>

      {error && <div className="px-5 pb-4"><Alerta onClose={() => setError(null)}>{error}</Alerta></div>}

      <div className="w-full overflow-x-auto" aria-busy={cargando}>
        <table className="report-tabla">
          <caption className="sr-only">Evaluaciones, más recientes primero</caption>
          <thead>
            <tr>
              <th scope="col">Fecha</th><th scope="col">Paciente</th><th scope="col">Edad</th>
              <th scope="col">Distrito</th><th scope="col">Banda del modelo</th><th scope="col" className="text-right">Índice</th>
              <th scope="col">Urgencia revisada</th>
            </tr>
          </thead>
          <tbody>
            {cargando && datos.items.length === 0 ? (
              <tr><td colSpan={7}><Cargando texto="Cargando evaluaciones..." /></td></tr>
            ) : datos.items.length === 0 ? (
              <tr><td colSpan={7} className="p-10 text-center text-slate-500">No hay evaluaciones con estos filtros.</td></tr>
            ) : datos.items.map((f) => (
              <tr key={f.id} className={cargando ? 'opacity-60' : ''}>
                <td className="whitespace-nowrap tabular-nums">{fechaHora(f.fecha)}</td>
                <td><span className="block font-medium text-slate-800">{f.paciente}</span><span className="text-xs text-slate-500 tabular-nums">DNI {f.documento}</span></td>
                <td className="tabular-nums">{f.edad}</td>
                <td>{f.distrito ?? <span className="text-slate-400">Sin distrito</span>}</td>
                <td><span className={`px-2.5 py-1 rounded-full text-xs font-semibold capitalize ${clasesClasificacion(f.clasificacion)}`}>{f.clasificacion}</span></td>
                <td className="text-right tabular-nums" title="Índice del modelo (0-100). Ordena el riesgo; no es probabilidad de enfermedad">{f.indice.toFixed(1)}</td>
                <td className="text-xs text-slate-600">{f.alerta ?? 'No revisada'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="px-5 py-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-600">
        <span aria-live="polite">{datos.total === 0 ? 'Sin resultados' : `Mostrando ${miles(desdeN)}–${miles(hastaN)} de ${miles(datos.total)}`}</span>
        <div className="flex items-center gap-2">
          <button type="button" className="report-btn" onClick={() => setPagina((p) => Math.max(0, p - 1))} disabled={pagina === 0 || cargando} aria-label="Página anterior"><ChevronLeft className="w-4 h-4" aria-hidden="true" /></button>
          <span className="tabular-nums">Página {pagina + 1} de {totalPaginas}</span>
          <button type="button" className="report-btn" onClick={() => setPagina((p) => Math.min(totalPaginas - 1, p + 1))} disabled={pagina + 1 >= totalPaginas || cargando} aria-label="Página siguiente"><ChevronRight className="w-4 h-4" aria-hidden="true" /></button>
        </div>
      </div>
    </section>
  );
}
