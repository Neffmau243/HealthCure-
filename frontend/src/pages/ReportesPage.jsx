import { useEffect, useState } from 'react';
import { Activity, AlertTriangle, CalendarCheck, Gauge, RefreshCw, Users } from 'lucide-react';
import PageHeader from '../components/ui/PageHeader';
import { Alerta, Cargando } from '../components/ui/Feedback';
import GraficoTendencia from '../components/reportes/GraficoTendencia';
import GraficoDona from '../components/reportes/GraficoDona';
import BarrasHorizontales from '../components/reportes/BarrasHorizontales';
import BarraApilada from '../components/reportes/BarraApilada';
import TarjetaKpi from '../components/reportes/TarjetaKpi';
import TablaEvaluaciones from '../components/reportes/TablaEvaluaciones';
import { reportesService } from '../services/reportes';
import { mensajeError } from '../services/api';
import { useAuth } from '../context/useAuth';
import { PERIODOS, fechaCorta, miles, resumenSerie } from '../utils/reportes';

export default function ReportesPage() {
  const { user } = useAuth();
  const [dias, setDias] = useState(30);
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [version, setVersion] = useState(0);   // sube al pulsar "Actualizar"

  useEffect(() => {
    const controlador = new AbortController();
    (async () => {
      setCargando(true);
      try {
        setDatos(await reportesService.dashboard(dias, { signal: controlador.signal }));
        setError(null);
      } catch (e) {
        if (e.code !== 'ERR_CANCELED') setError(mensajeError(e, 'No se pudieron cargar los reportes'));
      } finally {
        if (!controlador.signal.aborted) setCargando(false);
      }
    })();
    return () => controlador.abort();
  }, [dias, version]);

  const k = datos?.kpis;
  const resumen = datos ? resumenSerie(datos.serie_diaria) : null;

  return (
    <div className="space-y-6">
      <PageHeader title="Reportes y análisis" description="Panorama de las evaluaciones del centro: tendencia, distribución por banda del modelo, distritos y factores de riesgo registrados.">
        <div className="flex items-center gap-2">
          <div role="radiogroup" aria-label="Periodo del reporte" className="report-segmentado">
            {PERIODOS.map((p) => (
              <button key={p.dias} type="button" role="radio" aria-checked={dias === p.dias} onClick={() => setDias(p.dias)}>{p.etiqueta}</button>
            ))}
          </div>
          <button type="button" className="report-btn" onClick={() => setVersion((v) => v + 1)} disabled={cargando} aria-label="Actualizar datos" title="Actualizar datos">
            <RefreshCw className={`w-4 h-4 ${cargando ? 'animate-spin' : ''}`} aria-hidden="true" />
          </button>
        </div>
      </PageHeader>

      {error && <Alerta onClose={() => setError(null)}>{error}</Alerta>}

      {!datos ? (
        cargando && <Cargando texto="Cargando reportes..." />
      ) : (
        <div aria-busy={cargando} className={cargando ? 'opacity-70 transition-opacity' : 'transition-opacity'}>
          <p className="text-xs text-slate-500 mb-3">
            Del {fechaCorta(datos.desde)} al {fechaCorta(datos.hasta)} · {datos.periodo_dias} días
          </p>

          <div className="report-kpis">
            <TarjetaKpi titulo="Evaluaciones" valor={miles(k.evaluaciones)} detalle={`${miles(k.evaluaciones_hoy)} hoy`} icono={Activity} />
            <TarjetaKpi titulo="Pacientes evaluados" valor={miles(k.pacientes_evaluados)} detalle={`de ${miles(k.pacientes_registrados)} registrados`} icono={Users} tono="text-indigo-700 bg-indigo-50" />
            <TarjetaKpi titulo="Banda alta del modelo" valor={miles(k.riesgo_alto)} detalle={`${k.porcentaje_alto} % de las evaluaciones`} icono={AlertTriangle} tono="text-rose-700 bg-rose-50" />
            <TarjetaKpi titulo="Índice promedio" valor={k.indice_promedio.toFixed(1)} detalle="escala 0–100 del modelo" icono={Gauge} tono="text-amber-700 bg-amber-50" />
            <TarjetaKpi titulo="Promedio diario" valor={resumen.promedioDiario} detalle={resumen.pico ? `Pico: ${resumen.pico.total} el ${fechaCorta(resumen.pico.fecha)}` : 'Sin evaluaciones'} icono={CalendarCheck} tono="text-emerald-700 bg-emerald-50" />
          </div>

          <div className="report-grid mt-6">
            <section className="clinical-panel p-5 report-span-2" aria-labelledby="t-tendencia">
              <h2 id="t-tendencia" className="font-semibold text-slate-800">Evaluaciones por día</h2>
              <p className="text-xs text-slate-500 mt-1 mb-4">Cada columna se divide según la banda del modelo.</p>
              <GraficoTendencia serie={datos.serie_diaria} />
            </section>
            <section className="clinical-panel p-5" aria-labelledby="t-dona">
              <h2 id="t-dona" className="font-semibold text-slate-800">Distribución por banda</h2>
              <p className="text-xs text-slate-500 mt-1 mb-4">Resultado del modelo en el periodo.</p>
              <GraficoDona distribucion={datos.distribucion} />
            </section>

            <section className="clinical-panel p-5 report-span-2" aria-labelledby="t-distritos">
              <h2 id="t-distritos" className="font-semibold text-slate-800">Evaluaciones por distrito</h2>
              <p className="text-xs text-slate-500 mt-1 mb-4">Los 8 distritos con más evaluaciones. <span className="inline-flex items-center gap-1.5 ml-1"><i className="w-2.5 h-2.5 rounded-sm bg-[#c53030]" aria-hidden="true" />parte en banda alta</span></p>
              <BarrasHorizontales
                items={datos.por_distrito.map((d) => ({ id: d.distrito, etiqueta: d.distrito, valor: d.evaluaciones, destacado: d.alto, extra: `${d.pacientes} pac. · ${d.alto} alto` }))}
              />
            </section>
            <section className="clinical-panel p-5" aria-labelledby="t-edad">
              <h2 id="t-edad" className="font-semibold text-slate-800">Banda por grupo de edad</h2>
              <p className="text-xs text-slate-500 mt-1 mb-4">Edad al momento de la evaluación.</p>
              <ul className="space-y-4">
                {datos.por_grupo_edad.map((g) => <BarraApilada key={g.grupo} etiqueta={`${g.grupo} años`.replace('60+ años', '60 o más años')} fila={g} />)}
              </ul>
            </section>

            <section className="clinical-panel p-5 report-span-3" aria-labelledby="t-factores">
              <h2 id="t-factores" className="font-semibold text-slate-800">Factores de riesgo registrados</h2>
              <p className="text-xs text-slate-500 mt-1 mb-4">Porcentaje de las evaluaciones del periodo en que se marcó cada factor.</p>
              <BarrasHorizontales
                items={datos.factores.map((f) => ({ id: f.clave, etiqueta: f.etiqueta, valor: f.porcentaje, extra: `${miles(f.cantidad)} casos` }))}
                formato={(v) => `${v} %`} escalaMax={100} color="#5a6fa8"
              />
            </section>
          </div>

          <p className="text-xs text-slate-500 leading-relaxed mt-4 max-w-3xl">
            Las bandas describen el índice del modelo de aprendizaje automático (no es una probabilidad de enfermedad ni mide urgencia).
            La urgencia se revisa en cada atención con las alertas clínicas.
          </p>
        </div>
      )}

      <TablaEvaluaciones puedeExportar={user?.rol === 'admin'} />
    </div>
  );
}
