import { useEffect, useState } from 'react';
import { Users, Activity, AlertTriangle, TrendingUp, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../components/ui/PageHeader';
import { pacientesService } from '../services/pacientes';
import { evaluacionesService } from '../services/evaluaciones';
import { mensajeError } from '../services/api';
import { Cargando, Alerta } from '../components/ui/Feedback';
import { clasesClasificacion, nombreCompleto } from '../utils/triaje';

// Solo para la lista de "últimas evaluaciones". Los KPIs NO se calculan
// contando esta página: vienen del resumen agregado del backend.
const LIMITE_RECIENTES = 20;

export default function DashboardPage() {
  const navigate = useNavigate();
  const [pacientes, setPacientes] = useState([]);
  const [evaluaciones, setEvaluaciones] = useState([]);
  // Conteos exactos (COUNT en SQL). Antes los KPIs se contaban en el cliente
  // sobre un máximo de 200 evaluaciones: a partir de la 201 el número era
  // falso sin avisar.
  const [resumen, setResumen] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let activo = true;
    (async () => {
      try {
        const [listaPacientes, listaEvaluaciones, datosResumen] = await Promise.all([
          pacientesService.listar(),
          evaluacionesService.listar({ limit: LIMITE_RECIENTES }),
          evaluacionesService.resumen(),
        ]);
        if (!activo) return;
        setPacientes(listaPacientes);
        setEvaluaciones(listaEvaluaciones);
        setResumen(datosResumen);
      } catch (e) {
        if (activo) setError(mensajeError(e, 'No se pudieron cargar las métricas'));
      } finally {
        if (activo) setCargando(false);
      }
    })();
    return () => {
      activo = false;
    };
  }, []);

  const conteo = (nivel) =>
    evaluaciones.filter((ev) => ev.clasificacion === nivel).length;

  const pacientesPorId = Object.fromEntries(pacientes.map((p) => [p.id, p]));

  const clasificaciones = resumen?.por_clasificacion ?? {};
  const totalEvaluaciones = resumen?.total_evaluaciones ?? evaluaciones.length;

  const metricas = [
    { titulo: 'Pacientes registrados', valor: pacientes.length, icono: Users, color: 'text-sky-600 bg-sky-50' },
    {
      titulo: 'Evaluaciones realizadas',
      valor: totalEvaluaciones,
      pie: resumen ? 'total histórico' : 'últimas cargadas',
      icono: Activity,
      color: 'text-indigo-600 bg-indigo-50',
    },
    { titulo: 'Banda ML alta', valor: clasificaciones.alto ?? conteo('alto'), icono: AlertTriangle },
    { titulo: 'Banda ML moderada', valor: clasificaciones.moderado ?? conteo('moderado'), icono: TrendingUp },
  ];

  const recientes = evaluaciones.slice(0, 6);

  return (
    <div className="space-y-6">
      <PageHeader title="Al cuidado de cada paciente" description="Tu espacio de trabajo para acompañar la atención, desde el registro hasta el seguimiento clínico." />

      {error && <Alerta onClose={() => setError(null)}>{error}</Alerta>}

      {cargando ? (
        <Cargando texto="Cargando métricas..." />
      ) : (
        <>
          <div className="dashboard-overview">
            <section className="dashboard-start" aria-labelledby="iniciar-atencion">
              <h2 id="iniciar-atencion">Continúa el recorrido de atención</h2>
              <p>Accede a la información que necesitas para la próxima valoración.</p>
              <div className="mt-5">
                {[
                  ['Pacientes', 'Consulta el directorio o registra a una persona.', '/dashboard/pacientes'],
                  ['Triaje y evaluación', 'Registra mediciones y revisa señales de alarma.', '/dashboard/triaje'],
                  ['Consultorio médico', 'Documenta la atención y genera el FUA.', '/dashboard/consultorio'],
                ].map(([titulo, detalle, ruta]) => <button key={ruta} className="dashboard-start-link" onClick={() => navigate(ruta)}><div><span>{titulo}</span><small>{detalle}</small></div><ArrowRight className="w-4 h-4 shrink-0" aria-hidden="true" /></button>)}
              </div>
            </section>
            <section aria-labelledby="actividad-centro" className="pt-2">
              <h2 id="actividad-centro" className="text-base font-semibold">Actividad del centro</h2>
              <p className="text-xs text-slate-600 mt-2">Resumen de los registros disponibles.</p>
              <dl className="dashboard-metrics mt-3">
            {metricas.map((m) => {
              const Icono = m.icono;
              return (
                <div
                  key={m.titulo}
                  className="dashboard-metric"
                >
                  <dt><Icono className="w-4 h-4 shrink-0" aria-hidden="true" />{m.titulo}</dt>
                  <dd>{m.valor}</dd>
                  {m.pie && <p className="text-xs text-slate-600 mt-1">{m.pie}</p>}
                </div>
              );
            })}
              </dl>
              <p className="text-xs text-slate-600 leading-relaxed mt-5">Las bandas del modelo describen el índice cardiovascular. La urgencia se revisa en cada atención.</p>
            </section>
          </div>

          <div className="clinical-panel overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">Últimas evaluaciones</h2>
              <span className="text-xs text-slate-500">
                Mostrando {recientes.length} de {totalEvaluaciones}
                {typeof resumen?.total_hoy === 'number' && ` · ${resumen.total_hoy} hoy`}
              </span>
            </div>

            {recientes.length === 0 ? (
              <p className="p-8 text-center text-sm text-slate-400">
                Todavía no hay evaluaciones registradas.
              </p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {recientes.map((ev) => {
                  const paciente = pacientesPorId[ev.paciente_id];
                  return (
                    <li key={ev.id} className="p-4 flex flex-wrap items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-slate-800 truncate">
                          {paciente ? nombreCompleto(paciente) : `Paciente #${ev.paciente_id}`}
                        </p>
                        <p className="text-xs text-slate-500">
                          {new Date(ev.created_at).toLocaleString()} · {ev.edad} años
                          {ev.alerta_clinica?.titulo ? ` · ${ev.alerta_clinica.titulo}` : ' · Urgencia actual no revisada'}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span
                          className={`px-2.5 py-1 rounded-full text-xs font-semibold capitalize ${clasesClasificacion(
                            ev.clasificacion
                          )}`}
                        >
                          {ev.clasificacion}
                        </span>
                        <span
                          className="text-xs font-bold text-slate-600"
                          title="Índice de riesgo del modelo (ordena el riesgo; no es probabilidad de enfermedad)"
                        >
                          índice {(ev.probabilidad * 100).toFixed(1)}
                        </span>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}
