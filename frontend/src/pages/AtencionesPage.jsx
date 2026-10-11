import { useEffect, useState } from 'react';
import { History } from 'lucide-react';
import { atencionesService } from '../services/atenciones';
import { evaluacionesService } from '../services/evaluaciones';
import { mensajeError } from '../services/api';
import { Cargando, Alerta, Vacio } from '../components/ui/Feedback';

const PAGINA = 25;

export default function AtencionesPage() {
  const [atenciones, setAtenciones] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [cargandoMas, setCargandoMas] = useState(false);
  const [error, setError] = useState(null);
  const [errorFua, setErrorFua] = useState(null);
  const [hayMas, setHayMas] = useState(true);

  // Carga inicial: los setState ocurren DESPUÉS del await, así el efecto
  // no provoca renders en cascada.
  useEffect(() => {
    let activo = true;
    (async () => {
      try {
        const data = await atencionesService.listar({ limit: PAGINA, offset: 0 });
        if (!activo) return;
        setAtenciones(data);
        setHayMas(data.length === PAGINA);
        setError(null);
      } catch (e) {
        if (activo) setError(mensajeError(e, 'No se pudieron cargar las atenciones'));
      } finally {
        if (activo) setCargando(false);
      }
    })();
    return () => {
      activo = false;
    };
  }, []);

  const cargarMas = async () => {
    setCargandoMas(true);
    setError(null);
    try {
      const data = await atencionesService.listar({
        limit: PAGINA,
        offset: atenciones.length,
      });
      setAtenciones((prev) => [...prev, ...data]);
      setHayMas(data.length === PAGINA);
    } catch (e) {
      setError(mensajeError(e, 'No se pudieron cargar las atenciones'));
    } finally {
      setCargandoMas(false);
    }
  };

  const descargarFua = async (evaluacionId) => {
    setErrorFua(null);
    try {
      await evaluacionesService.descargarFua(evaluacionId);
    } catch (e) {
      setErrorFua(mensajeError(e, 'No se pudo descargar el FUA'));
    }
  };

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Historial de Atenciones</h2>
        <p className="text-sm text-slate-500">
          Registro histórico de las consultas médicas realizadas en el centro.
        </p>
      </div>

      {error && <Alerta onClose={() => setError(null)}>{error}</Alerta>}
      {errorFua && <Alerta onClose={() => setErrorFua(null)}>{errorFua}</Alerta>}

      {cargando ? (
        <Cargando texto="Cargando atenciones..." />
      ) : atenciones.length === 0 ? (
        <Vacio
          titulo="Sin atenciones registradas"
          detalle="Las atenciones que registres en el Consultorio aparecerán aquí."
          icono={History}
        />
      ) : (
        <>
          <div className="bg-white rounded-2xl shadow-xs border border-slate-100 divide-y divide-slate-100">
            {atenciones.map((a) => (
              <div key={a.id} className="p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-800">
                      {a.paciente_nombre ?? `Paciente #${a.paciente_id}`}
                    </p>
                    <p className="text-xs text-slate-500">
                      {new Date(a.created_at).toLocaleString()}
                      {a.evaluacion_id ? ` · evaluación #${a.evaluacion_id}` : ' · sin evaluación asociada'}
                    </p>
                  </div>

                  {a.evaluacion_id && (
                    <button
                      onClick={() => descargarFua(a.evaluacion_id)}
                      className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium transition cursor-pointer"
                    >
                      Descargar FUA
                    </button>
                  )}
                </div>

                <div className="mt-2 space-y-1">
                  <p className="text-sm text-slate-800">
                    <span className="font-semibold">Diagnóstico: </span>
                    {a.diagnostico}
                  </p>
                  <p className="text-sm text-slate-700">
                    <span className="font-semibold">Tratamiento: </span>
                    {a.tratamiento}
                  </p>
                  {a.indicaciones && (
                    <p className="text-xs text-slate-500">Indicaciones: {a.indicaciones}</p>
                  )}
                </div>
              </div>
            ))}
          </div>

          {hayMas && (
            <div className="flex justify-center">
              <button
                onClick={cargarMas}
                disabled={cargandoMas}
                className="px-5 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-700 hover:bg-slate-50 transition cursor-pointer disabled:opacity-60"
              >
                {cargandoMas ? 'Cargando...' : 'Cargar más'}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
