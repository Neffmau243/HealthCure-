import { useEffect, useState } from 'react';
import { FileText, Search, Loader2, Stethoscope } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { pacientesService } from '../services/pacientes';
import { evaluacionesService } from '../services/evaluaciones';
import { atencionesService } from '../services/atenciones';
import { mensajeError } from '../services/api';
import { Cargando, Alerta, Vacio } from '../components/ui/Feedback';
import TarjetaTriaje from '../components/triaje/TarjetaTriaje';
import { calcularEdad, etiquetaSexo, nombreCompleto } from '../utils/triaje';

export default function HistoriasClinicasPage() {
  const location = useLocation();

  const [documento, setDocumento] = useState('');
  const [resultados, setResultados] = useState([]);
  const [buscando, setBuscando] = useState(false);
  const [errorBusqueda, setErrorBusqueda] = useState(null);

  const [paciente, setPaciente] = useState(null);
  const [evaluaciones, setEvaluaciones] = useState([]);
  const [atenciones, setAtenciones] = useState([]);
  const [cargandoDetalle, setCargandoDetalle] = useState(false);
  const [error, setError] = useState(null);

  const cargarDetalle = async (p) => {
    setPaciente(p);
    setCargandoDetalle(true);
    setError(null);
    try {
      const [evs, ats] = await Promise.all([
        evaluacionesService.porPaciente(p.id),
        atencionesService.porPaciente(p.id),
      ]);
      setEvaluaciones(evs);
      setAtenciones(ats);
    } catch (e) {
      setError(mensajeError(e, 'No se pudo cargar la historia clínica'));
      setEvaluaciones([]);
      setAtenciones([]);
    } finally {
      setCargandoDetalle(false);
    }
  };

  // Si venimos desde Pacientes/Triaje con un paciente preseleccionado.
  useEffect(() => {
    const id = location.state?.pacienteId;
    if (!id) return;
    pacientesService
      .obtener(id)
      .then((p) => {
        setDocumento(p.documento_identidad);
        setResultados([p]);
        cargarDetalle(p);
      })
      .catch((e) => setError(mensajeError(e, 'No se pudo abrir la historia clínica')));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const buscar = async (e) => {
    e.preventDefault();
    const termino = documento.trim();
    if (!termino) return;
    setBuscando(true);
    setErrorBusqueda(null);
    try {
      const data = await pacientesService.buscar(termino);
      setResultados(data);
      if (data.length === 1) {
        await cargarDetalle(data[0]);
      } else {
        setPaciente(null);
      }
    } catch (err) {
      setErrorBusqueda(mensajeError(err, 'No se pudo buscar el paciente'));
      setResultados([]);
    } finally {
      setBuscando(false);
    }
  };

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Historias Clínicas</h2>
        <p className="text-sm text-slate-500">
          Consulta el expediente del paciente: evaluaciones, triaje clínico, atenciones y FUA.
        </p>
      </div>

      {/* Buscador */}
      <form
        onSubmit={buscar}
        className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 flex flex-col sm:flex-row gap-4"
      >
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
          <input
            type="text"
            placeholder="Buscar por documento del paciente..."
            value={documento}
            onChange={(e) => setDocumento(e.target.value)}
            className="w-full py-2.5 pl-10 pr-4 rounded-lg border border-slate-300 text-sm outline-none focus:border-sky-500 transition-colors"
          />
        </div>
        <button
          type="submit"
          disabled={buscando}
          className="px-5 py-2.5 bg-[#17324c] hover:bg-slate-800 text-white rounded-lg text-sm font-medium transition cursor-pointer disabled:opacity-60 inline-flex items-center justify-center gap-2"
        >
          {buscando && <Loader2 className="w-4 h-4 animate-spin" />}
          Buscar
        </button>
      </form>

      {errorBusqueda && <Alerta>{errorBusqueda}</Alerta>}

      {/* Resultados de búsqueda (cuando hay más de uno) */}
      {resultados.length > 1 && !paciente && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 divide-y divide-slate-100">
          {resultados.map((p) => (
            <button
              key={p.id}
              onClick={() => cargarDetalle(p)}
              className="w-full text-left p-4 hover:bg-slate-50 transition cursor-pointer"
            >
              <p className="text-sm font-medium text-slate-800">{nombreCompleto(p)}</p>
              <p className="text-xs text-slate-500">Doc: {p.documento_identidad}</p>
            </button>
          ))}
        </div>
      )}

      {error && <Alerta onClose={() => setError(null)}>{error}</Alerta>}

      {/* Expediente */}
      {cargandoDetalle ? (
        <Cargando texto="Cargando historia clínica..." />
      ) : paciente ? (
        <>
          <div className="bg-white p-5 rounded-2xl shadow-xs border border-slate-100">
            <h3 className="text-lg font-bold text-slate-800">{nombreCompleto(paciente)}</h3>
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-600 mt-2">
              <span>Doc: {paciente.documento_identidad}</span>
              {paciente.numero_historia_clinica && <span>H.C.: {paciente.numero_historia_clinica}</span>}
              <span>{calcularEdad(paciente.fecha_nacimiento) ?? '—'} años</span>
              <span>{etiquetaSexo(paciente.sexo)}</span>
              <span>Seguro: {paciente.tipo_seguro}</span>
              {paciente.distrito && <span>{paciente.distrito}</span>}
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-700">
              Evaluaciones ({evaluaciones.length})
            </h3>
            {evaluaciones.length === 0 ? (
              <Vacio
                titulo="Sin evaluaciones registradas"
                detalle="Registra un triaje para generar la primera evaluación."
                icono={FileText}
              />
            ) : (
              evaluaciones.map((ev) => <TarjetaTriaje key={ev.id} evaluacion={ev} />)
            )}
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-700">
              Atenciones ({atenciones.length})
            </h3>
            {atenciones.length === 0 ? (
              <Vacio
                titulo="Sin atenciones registradas"
                detalle="Las consultas del consultorio aparecerán aquí."
                icono={Stethoscope}
              />
            ) : (
              <div className="bg-white rounded-2xl shadow-xs border border-slate-100 divide-y divide-slate-100">
                {atenciones.map((a) => (
                  <div key={a.id} className="p-4">
                    <p className="text-xs text-slate-500 mb-1">
                      {new Date(a.created_at).toLocaleString()}
                      {a.evaluacion_id ? ` · evaluación #${a.evaluacion_id}` : ''}
                    </p>
                    <p className="text-sm text-slate-800">
                      <span className="font-semibold">Dx: </span>
                      {a.diagnostico}
                    </p>
                    <p className="text-sm text-slate-700">
                      <span className="font-semibold">Tx: </span>
                      {a.tratamiento}
                    </p>
                    {a.indicaciones && (
                      <p className="text-xs text-slate-500 mt-1">Indicaciones: {a.indicaciones}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      ) : (
        resultados.length === 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 text-center py-12">
            <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-700">
              No hay historias clínicas seleccionadas
            </h3>
            <p className="text-sm text-slate-500 mt-1">
              Busca un paciente por su documento para ver su historial detallado.
            </p>
          </div>
        )
      )}
    </div>
  );
}
