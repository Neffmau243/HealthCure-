import { useEffect, useState } from 'react';
import { Users, Activity, AlertTriangle, TrendingUp } from 'lucide-react';
import { pacientesService } from '../services/pacientes';
import { evaluacionesService } from '../services/evaluaciones';
import { mensajeError } from '../services/api';
import { Cargando, Alerta } from '../components/ui/Feedback';
import { clasesClasificacion, nombreCompleto } from '../utils/triaje';

const LIMITE_EVALUACIONES = 200;

export default function DashboardPage() {
  const [pacientes, setPacientes] = useState([]);
  const [evaluaciones, setEvaluaciones] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let activo = true;
    (async () => {
      try {
        const [listaPacientes, listaEvaluaciones] = await Promise.all([
          pacientesService.listar(),
          evaluacionesService.listar({ limit: LIMITE_EVALUACIONES }),
        ]);
        if (!activo) return;
        setPacientes(listaPacientes);
        setEvaluaciones(listaEvaluaciones);
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

  const metricas = [
    { titulo: 'Pacientes registrados', valor: pacientes.length, icono: Users, color: 'text-sky-600 bg-sky-50' },
    { titulo: 'Evaluaciones realizadas', valor: evaluaciones.length, icono: Activity, color: 'text-indigo-600 bg-indigo-50' },
    { titulo: 'Riesgo alto', valor: conteo('alto'), icono: AlertTriangle, color: 'text-rose-600 bg-rose-50' },
    { titulo: 'Riesgo moderado', valor: conteo('moderado'), icono: TrendingUp, color: 'text-amber-600 bg-amber-50' },
  ];

  const recientes = evaluaciones.slice(0, 6);

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-2xl shadow-xs border border-slate-100">
        <h1 className="text-2xl font-bold text-slate-800">Panel Principal</h1>
        <p className="text-sm text-slate-500 mt-1">
          Resumen de la actividad del centro médico y del riesgo cardiovascular detectado.
        </p>
      </div>

      {error && <Alerta onClose={() => setError(null)}>{error}</Alerta>}

      {cargando ? (
        <Cargando texto="Cargando métricas..." />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {metricas.map((m) => {
              const Icono = m.icono;
              return (
                <div
                  key={m.titulo}
                  className="bg-white p-5 rounded-2xl shadow-xs border border-slate-100 flex items-center gap-4"
                >
                  <div className={`p-3 rounded-xl ${m.color}`}>
                    <Icono className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-800">{m.valor}</p>
                    <p className="text-xs text-slate-500">{m.titulo}</p>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="bg-white rounded-2xl shadow-xs border border-slate-100 overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">Últimas evaluaciones</h2>
              <span className="text-xs text-slate-400">
                Mostrando {recientes.length} de {evaluaciones.length}
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
                          {ev.triaje_clinico?.nivel_alerta ? ` · ${ev.triaje_clinico.nivel_alerta}` : ''}
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
                        <span className="text-xs font-bold text-slate-600">
                          {(ev.probabilidad * 100).toFixed(1)}%
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
