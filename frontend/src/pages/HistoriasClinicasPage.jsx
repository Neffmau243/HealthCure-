import PageHeader from '../components/ui/PageHeader';
import { useEffect, useState } from 'react';
import { FileText, Search, Loader2, Stethoscope } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { pacientesService } from '../services/pacientes';
import { evaluacionesService } from '../services/evaluaciones';
import { atencionesService } from '../services/atenciones';
import { mensajeError } from '../services/api';
import { Cargando, Alerta, Vacio } from '../components/ui/Feedback';
import TarjetaTriaje from '../components/triaje/TarjetaTriaje';
import TarjetaAtencion from '../components/atenciones/TarjetaAtencion';
import { etiquetaGrupo } from '../utils/clinica';
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
    <div className="space-y-6">
      <PageHeader title="Historia clínica" description="El recorrido de salud de cada paciente: evaluaciones, atenciones y documentos en un solo lugar." />

      {/* Buscador */}
      <form
        onSubmit={buscar}
        className="clinical-panel p-4 flex flex-col sm:flex-row gap-4"
      >
        <div className="relative flex-1">
          <Search
            className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4"
            aria-hidden="true"
          />
          <input
            type="text"
            placeholder="Buscar por documento del paciente..."
            aria-label="Buscar paciente por número de documento"
            value={documento}
            onChange={(e) => setDocumento(e.target.value)}
            className="w-full py-3 min-h-11 pl-10 pr-4 rounded-lg border border-slate-300 text-sm outline-none focus:border-sky-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#17324c] transition-colors"
          />
        </div>
        <button
          type="submit"
          disabled={buscando}
          className="px-5 py-3 min-h-11 bg-[#17324c] hover:bg-slate-800 text-white rounded-lg text-sm font-medium transition cursor-pointer disabled:opacity-60 inline-flex items-center justify-center gap-2"
        >
          {buscando && <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />}
          Buscar
        </button>
      </form>

      {errorBusqueda && <Alerta>{errorBusqueda}</Alerta>}

      {/* Resultados de búsqueda (cuando hay más de uno) */}
      {resultados.length > 1 && !paciente && (
        <div className="clinical-panel divide-y divide-slate-100">
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
          <div className="clinical-panel p-5">
            <h3 className="text-lg font-bold text-slate-800">{nombreCompleto(paciente)}</h3>
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-600 mt-2">
              <span>Doc: {paciente.documento_identidad}</span>
              {paciente.numero_historia_clinica && <span>H.C.: {paciente.numero_historia_clinica}</span>}
              <span>{calcularEdad(paciente.fecha_nacimiento) ?? '—'} años</span>
              <span>Grupo actual: {etiquetaGrupo(paciente.grupo_etario)}</span>
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
              <div className="clinical-panel divide-y divide-slate-100">
                {atenciones.map((a) => (
                  <div key={a.id} className="p-4">
                    <TarjetaAtencion atencion={a} />
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      ) : (
        resultados.length === 0 && (
          <div className="clinical-panel p-6 text-center py-12">
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
