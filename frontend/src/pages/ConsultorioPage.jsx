import { useEffect, useState } from 'react';
import {
  Search,
  User,
  BrainCircuit,
  Stethoscope,
  CheckCircle2,
  History,
  Loader2,
} from 'lucide-react';
import { pacientesService } from '../services/pacientes';
import { evaluacionesService } from '../services/evaluaciones';
import { atencionesService } from '../services/atenciones';
import { mensajeError } from '../services/api';
import { Cargando, Alerta } from '../components/ui/Feedback';
import TarjetaTriaje from '../components/triaje/TarjetaTriaje';
import { calcularEdad, etiquetaSexo, nombreCompleto, clasesClasificacion } from '../utils/triaje';

const FORM_VACIO = { diagnostico: '', tratamiento: '', indicaciones: '' };

export default function ConsultorioPage() {
  const [pacientes, setPacientes] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [busqueda, setBusqueda] = useState('');

  const [pacienteSeleccionado, setPacienteSeleccionado] = useState(null);
  const [evaluaciones, setEvaluaciones] = useState([]);
  const [atenciones, setAtenciones] = useState([]);
  const [cargandoDetalle, setCargandoDetalle] = useState(false);
  const [evaluacionSeleccionada, setEvaluacionSeleccionada] = useState(null);

  const [form, setForm] = useState(FORM_VACIO);
  const [guardando, setGuardando] = useState(false);
  const [errorForm, setErrorForm] = useState(null);
  const [exito, setExito] = useState(null);

  useEffect(() => {
    pacientesService
      .listar()
      .then(setPacientes)
      .catch((e) => setError(mensajeError(e, 'No se pudieron cargar los pacientes')))
      .finally(() => setCargando(false));
  }, []);

  const cargarDetalle = async (paciente) => {
    setCargandoDetalle(true);
    setError(null);
    try {
      const [evs, ats] = await Promise.all([
        evaluacionesService.porPaciente(paciente.id),
        atencionesService.porPaciente(paciente.id),
      ]);
      setEvaluaciones(evs);
      setAtenciones(ats);
      setEvaluacionSeleccionada(evs[0] ?? null);
    } catch (e) {
      setError(mensajeError(e, 'No se pudo cargar el historial del paciente'));
      setEvaluaciones([]);
      setAtenciones([]);
      setEvaluacionSeleccionada(null);
    } finally {
      setCargandoDetalle(false);
    }
  };

  const seleccionarPaciente = (paciente) => {
    setPacienteSeleccionado(paciente);
    setForm(FORM_VACIO);
    setErrorForm(null);
    setExito(null);
    cargarDetalle(paciente);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!pacienteSeleccionado) return;
    setGuardando(true);
    setErrorForm(null);
    setExito(null);
    try {
      await atencionesService.crear({
        paciente_id: pacienteSeleccionado.id,
        evaluacion_id: evaluacionSeleccionada?.id ?? null,
        diagnostico: form.diagnostico.trim(),
        tratamiento: form.tratamiento.trim(),
        indicaciones: form.indicaciones.trim() || null,
      });
      setForm(FORM_VACIO);
      setExito('Atención registrada correctamente.');
      const ats = await atencionesService.porPaciente(pacienteSeleccionado.id);
      setAtenciones(ats);
    } catch (err) {
      setErrorForm(mensajeError(err, 'No se pudo registrar la atención'));
    } finally {
      setGuardando(false);
    }
  };

  const termino = busqueda.trim().toLowerCase();
  const pacientesDisponibles = termino
    ? pacientes.filter((p) =>
        [p.documento_identidad, p.nombre_completo, p.apellido_paterno, p.nombres]
          .filter(Boolean)
          .some((c) => String(c).toLowerCase().includes(termino))
      )
    : pacientes;

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Consultorio Médico & Diagnóstico IA</h2>
        <p className="text-sm text-slate-500">
          Revisa la evaluación del modelo, registra el acto médico y descarga el FUA.
        </p>
      </div>

      {error && <Alerta onClose={() => setError(null)}>{error}</Alerta>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* COLUMNA IZQUIERDA: Paciente + evaluaciones */}
        <div className="space-y-6 lg:col-span-1">
          <div className="bg-white p-5 rounded-2xl shadow-xs border border-slate-100">
            <h3 className="font-semibold text-slate-800 flex items-center gap-2 mb-3">
              <User className="w-5 h-5 text-sky-600" /> Seleccionar Paciente
            </h3>

            <div className="relative mb-3">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Buscar por documento o nombre..."
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                className="w-full pl-10 pr-3 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-sky-400 transition"
              />
            </div>

            {cargando ? (
              <Cargando texto="Cargando pacientes..." />
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {pacientesDisponibles.length === 0 ? (
                  <p className="text-xs text-slate-400 text-center py-4">
                    No se encontraron pacientes.
                  </p>
                ) : (
                  pacientesDisponibles.map((p) => (
                    <div
                      key={p.id}
                      onClick={() => seleccionarPaciente(p)}
                      className={`p-3 rounded-xl border text-sm cursor-pointer transition ${
                        pacienteSeleccionado?.id === p.id
                          ? 'bg-sky-50 border-sky-300 shadow-xs'
                          : 'bg-slate-50 hover:bg-slate-100 border-slate-200'
                      }`}
                    >
                      <p className="font-bold text-slate-800">{nombreCompleto(p)}</p>
                      <p className="text-xs text-slate-500">
                        Doc: {p.documento_identidad} ·{' '}
                        {calcularEdad(p.fecha_nacimiento) ?? '—'} años · {etiquetaSexo(p.sexo)}
                      </p>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Evaluaciones del paciente */}
          <div className="bg-white p-5 rounded-2xl shadow-xs border border-slate-100">
            <h3 className="font-semibold text-slate-800 flex items-center gap-2 mb-3">
              <BrainCircuit className="w-5 h-5 text-indigo-600" /> Evaluaciones del paciente
            </h3>

            {!pacienteSeleccionado ? (
              <p className="text-xs text-slate-400 text-center py-4">
                Selecciona un paciente para ver sus evaluaciones.
              </p>
            ) : cargandoDetalle ? (
              <Cargando texto="Cargando evaluaciones..." />
            ) : evaluaciones.length === 0 ? (
              <p className="text-xs text-slate-400 text-center py-4">
                Este paciente aún no tiene evaluaciones. Regístralas en Triaje.
              </p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {evaluaciones.map((ev) => (
                  <button
                    key={ev.id}
                    onClick={() => setEvaluacionSeleccionada(ev)}
                    className={`w-full text-left p-3 rounded-xl border transition cursor-pointer ${
                      evaluacionSeleccionada?.id === ev.id
                        ? 'bg-indigo-50 border-indigo-300'
                        : 'bg-slate-50 hover:bg-slate-100 border-slate-200'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold capitalize ${clasesClasificacion(ev.clasificacion)}`}>
                        {ev.clasificacion}
                      </span>
                      <span className="text-xs font-bold text-slate-600">
                        {(ev.probabilidad * 100).toFixed(1)}%
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-1">
                      {new Date(ev.created_at).toLocaleString()} · {ev.edad} años
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* COLUMNA DERECHA: Resultado ML + acto médico */}
        <div className="space-y-6 lg:col-span-2">
          <div className="bg-white p-5 rounded-2xl shadow-xs border border-slate-100 space-y-3">
            <h3 className="font-semibold text-slate-800 flex items-center gap-2">
              <BrainCircuit className="w-5 h-5 text-indigo-600" /> Resultado del modelo
            </h3>

            {!pacienteSeleccionado ? (
              <p className="text-sm text-slate-400 py-6 text-center">
                Selecciona un paciente para ver el resultado de su evaluación.
              </p>
            ) : evaluacionSeleccionada ? (
              <TarjetaTriaje evaluacion={evaluacionSeleccionada} />
            ) : (
              <p className="text-sm text-slate-400 py-6 text-center">
                Este paciente no tiene evaluaciones registradas todavía.
              </p>
            )}
          </div>

          <form
            onSubmit={handleSubmit}
            className="bg-white p-6 rounded-2xl shadow-xs border border-slate-100 space-y-4"
          >
            <h3 className="font-semibold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
              <Stethoscope className="w-5 h-5 text-sky-600" /> Diagnóstico & Receta Médica
            </h3>

            {errorForm && <Alerta>{errorForm}</Alerta>}
            {exito && <Alerta tipo="exito">{exito}</Alerta>}

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Diagnóstico Final del Médico *
              </label>
              <textarea
                rows="2"
                required
                minLength={3}
                value={form.diagnostico}
                onChange={(e) => setForm({ ...form, diagnostico: e.target.value })}
                placeholder="Confirmación diagnóstica u observaciones del especialista..."
                className="w-full p-3 text-sm bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-sky-400 transition"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Tratamiento / Receta *
                </label>
                <textarea
                  rows="3"
                  required
                  minLength={3}
                  value={form.tratamiento}
                  onChange={(e) => setForm({ ...form, tratamiento: e.target.value })}
                  placeholder="Medicamentos, dosis e indicaciones..."
                  className="w-full p-3 text-sm bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-sky-400 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Indicaciones Generales
                </label>
                <textarea
                  rows="3"
                  value={form.indicaciones}
                  onChange={(e) => setForm({ ...form, indicaciones: e.target.value })}
                  placeholder="Dieta, exámenes auxiliares o cita de control..."
                  className="w-full p-3 text-sm bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-sky-400 transition"
                />
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={!pacienteSeleccionado || guardando}
                className="flex items-center gap-2 px-5 py-2.5 bg-[#17324c] hover:bg-slate-800 text-white rounded-xl text-sm font-semibold transition-all shadow-sm cursor-pointer disabled:opacity-40"
              >
                {guardando ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                )}
                <span>{guardando ? 'Guardando...' : 'Registrar Atención'}</span>
              </button>
            </div>
          </form>

          {/* Atenciones previas */}
          {pacienteSeleccionado && (
            <div className="bg-white p-5 rounded-2xl shadow-xs border border-slate-100">
              <h3 className="font-semibold text-slate-800 flex items-center gap-2 mb-3">
                <History className="w-5 h-5 text-slate-500" /> Atenciones registradas
              </h3>

              {cargandoDetalle ? (
                <Cargando texto="Cargando atenciones..." />
              ) : atenciones.length === 0 ? (
                <p className="text-xs text-slate-400 text-center py-4">
                  Este paciente aún no tiene atenciones registradas.
                </p>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {atenciones.map((a) => (
                    <li key={a.id} className="py-3">
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
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
