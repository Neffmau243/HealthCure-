import { useEffect, useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import GraficoTendencia from './GraficoTendencia';
import { reportesService } from '../../services/reportes';
import { fechaCorta } from '../../utils/reportes';

/** Resumen de los últimos 7 días para la portada. Falla en silencio: no debe romper el inicio. */
export default function PanelTendencia() {
  const [datos, setDatos] = useState(null);
  const [fallo, setFallo] = useState(false);

  useEffect(() => {
    const controlador = new AbortController();
    reportesService.dashboard(7, { signal: controlador.signal })
      .then(setDatos)
      .catch((e) => { if (e.code !== 'ERR_CANCELED') setFallo(true); });
    return () => controlador.abort();
  }, []);

  if (fallo) return null;
  return (
    <section className="clinical-panel p-5" aria-labelledby="tendencia-semana">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <h2 id="tendencia-semana" className="font-semibold text-slate-800">Evaluaciones de la última semana</h2>
          {datos && <p className="text-xs text-slate-500 mt-1">{fechaCorta(datos.desde)} – {fechaCorta(datos.hasta)} · {datos.kpis.evaluaciones} en total</p>}
        </div>
        <Link to="/dashboard/reportes" className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--clinical-ink)] hover:underline">
          Ver reportes<ArrowRight className="w-4 h-4" aria-hidden="true" />
        </Link>
      </div>
      {datos ? <GraficoTendencia serie={datos.serie_diaria} alturaMax={220} /> : <div className="h-40 rounded-lg bg-slate-50 animate-pulse" aria-hidden="true" />}
    </section>
  );
}
