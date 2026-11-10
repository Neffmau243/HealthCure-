import PageHeader from '../components/ui/PageHeader';
import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
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
import TarjetaAtencion from '../components/atenciones/TarjetaAtencion';
import { TIPOS_ATENCION, CONDICIONES_MATERNAS, etiquetaGrupo } from '../utils/clinica';
import { calcularEdad, etiquetaSexo, nombreCompleto, clasesClasificacion } from '../utils/triaje';
import ObservacionesForm from '../components/clinica/ObservacionesForm';
import AlertaClinica from '../components/clinica/AlertaClinica';
import { construirObservaciones, hayAlerta } from '../utils/observaciones';
import { useAlertaClinica } from '../hooks/useAlertaClinica';

const FORM_VACIO = { diagnostico: '', tratamiento: '', indicaciones: '', tipo_atencion: 'ambulatoria', condicion_materna: 'ninguna' };

export default function ConsultorioPage() {
  const location = useLocation();
  const pacienteInicialId = location.state?.pacienteId;
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
  const observaciones = construirObservaciones(form, form.condicion_materna);
  const observacionesVigentes = form.usar_observaciones_evaluacion && evaluacionSeleccionada?.observaciones_clinicas
    ? {...evaluacionSeleccionada.observaciones_clinicas,condicion_materna:form.condicion_materna} : observaciones;
  const revision = useAlertaClinica(pacienteSeleccionado?.id, observacionesVigentes);

  useEffect(() => {
    let activo = true;
    pacientesService
      .listar()
      .then((lista) => {
        if (!activo) return;
        setPacientes(lista);
        const inicial = lista.find((p) => p.id === pacienteInicialId);
        if (inicial) {
          setPacienteSeleccionado(inicial);
          setCargandoDetalle(true);
        }
      })
      .catch((e) => { if (activo) setError(mensajeError(e, 'No se pudieron cargar los pacientes')); })
      .finally(() => { if (activo) setCargando(false); });
    return () => { activo = false; };
  }, [pacienteInicialId]);

  const pacienteId = pacienteSeleccionado?.id;
  useEffect(() => {
    if (!pacienteId) return;
    let activo = true;
    (async () => {
      try {
        const [evs, ats] = await Promise.all([
          evaluacionesService.porPaciente(pacienteId),
          atencionesService.porPaciente(pacienteId),
        ]);
        if (!activo) return;
        setEvaluaciones(evs);
        setAtenciones(ats);
        setEvaluacionSeleccionada(evs[0] ?? null);
      } catch (e) {
        if (!activo) return;
        setError(mensajeError(e, 'No se pudo cargar el historial del paciente'));
        setEvaluaciones([]);
        setAtenciones([]);
        setEvaluacionSeleccionada(null);
      } finally {
        if (activo) setCargandoDetalle(false);
      }
    })();
    return () => { activo = false; };
  }, [pacienteId]);

  const seleccionarPaciente = (paciente) => {
    if (guardando || paciente.id === pacienteId) return;
    setPacienteSeleccionado(paciente);
    setForm(FORM_VACIO);
    setErrorForm(null);
    setExito(null);
    setError(null);
    setEvaluaciones([]);
    setAtenciones([]);
    setEvaluacionSeleccionada(null);
    setCargandoDetalle(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!pacienteSeleccionado || cargandoDetalle || guardando) return;
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
        tipo_atencion: form.tipo_atencion,
        condicion_materna: form.condicion_materna,
        observaciones_clinicas: form.usar_observaciones_evaluacion ? null : observaciones,
        usar_observaciones_evaluacion: Boolean(form.usar_observaciones_evaluacion),
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
    <div className="space-y-6">
      <PageHeader title="Consultorio médico" description="Integra la valoración del paciente, documenta la atención y emite su FUA." />

      {error && <Alerta onClose={() => setError(null)}>{error}</Alerta>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* COLUMNA IZQUIERDA: Paciente + evaluaciones */}
        <div className="space-y-6 lg:col-span-1">
          <div className="clinical-panel p-5">
            <h3 className="font-semibold text-slate-800 flex items-center gap-2 mb-3">
              <User className="w-5 h-5 text-sky-600" /> Seleccionar Paciente
            </h3>

            <div className="relative mb-3">
              <Search
                className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4"
                aria-hidden="true"
              />
              <input
                type="text"
                placeholder="Buscar por documento o nombre..."
                aria-label="Buscar paciente por documento o nombre"
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                className="w-full pl-10 pr-3 py-3 min-h-11 text-sm bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-sky-400 transition"
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
                    <button
                      key={p.id}
                      type="button"
                      disabled={guardando}
                      onClick={() => seleccionarPaciente(p)}
                      className={`w-full text-left p-3 rounded-xl border text-sm cursor-pointer transition disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-sky-600 ${
                        pacienteSeleccionado?.id === p.id
                          ? 'bg-sky-50 border-sky-300 shadow-xs'
                          : 'bg-slate-50 hover:bg-slate-100 border-slate-200'
                      }`}
                    >
                      <p className="font-bold text-slate-800">{nombreCompleto(p)}</p>
                      <p className="text-xs text-slate-500">
                        Doc: {p.documento_identidad} ·{' '}
                        {calcularEdad(p.fecha_nacimiento) ?? '—'} años · {etiquetaSexo(p.sexo)}
                        {' · '}{etiquetaGrupo(p.grupo_etario)}
                      </p>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Evaluaciones del paciente */}
          <div className="clinical-panel p-5">
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
                {calcularEdad(pacienteSeleccionado.fecha_nacimiento) < 18
                  ? 'Paciente menor de edad. Registra la atención y su FUA sin ejecutar el modelo de adultos.'
                  : 'Este paciente aún no tiene evaluaciones. Puedes registrar la atención sin ML o evaluar en Triaje.'}
              </p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {evaluaciones.map((ev) => (
                  <button
                    key={ev.id}
                    disabled={guardando}
                    onClick={() => {setEvaluacionSeleccionada(ev); setForm({...form,usar_observaciones_evaluacion:false});}}
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
                        Índice {(ev.probabilidad * 100).toFixed(1)}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-1">
                      {new Date(ev.created_at).toLocaleString()} · {ev.edad} años
                    </p>
                    {hayAlerta(ev.alerta_clinica) && <p className="mt-1 text-xs font-semibold text-rose-900">{ev.alerta_clinica.titulo}</p>}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* COLUMNA DERECHA: Resultado ML + acto médico */}
        <div className="space-y-6 lg:col-span-2">
          <div className="space-y-3">
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
                {cargandoDetalle ? 'Cargando evaluación…' : 'Sin evaluación ML asociada. La atención y el FUA están disponibles.'}
              </p>
            )}
          </div>

          <form
            onSubmit={handleSubmit}
            className="consultation-form space-y-5"
          >
            <h3 className="font-semibold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
              <Stethoscope className="w-5 h-5 text-sky-600" /> Registro de la atención
            </h3>

            {errorForm && <Alerta>{errorForm}</Alerta>}
            {exito && <Alerta tipo="exito">{exito}</Alerta>}

            <fieldset disabled={!pacienteSeleccionado || cargandoDetalle || guardando} className="space-y-3">
              <legend className="text-sm font-semibold text-slate-800 mb-2">Contexto de esta atención</legend>
              <p className="text-xs text-slate-600">
                Grupo por edad: <strong>{etiquetaGrupo(pacienteSeleccionado?.grupo_etario)}</strong>.
                {' '}La edad y el grupo quedarán registrados con esta atención.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="cons-tipo-atencion" className="block text-xs font-semibold text-slate-700 mb-1">Tipo de atención *</label>
                  <select id="cons-tipo-atencion" required value={form.tipo_atencion} onChange={(e) => setForm({ ...form, tipo_atencion: e.target.value })}
                    className="w-full p-3 min-h-11 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-400">
                    {Object.entries(TIPOS_ATENCION).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select>
                </div>
                <div>
                  <label htmlFor="cons-condicion-materna" className="block text-xs font-semibold text-slate-700 mb-1">Condición materna *</label>
                  <select id="cons-condicion-materna" required value={form.condicion_materna} disabled={pacienteSeleccionado?.sexo !== 'F'}
                    aria-describedby="cons-contexto-ayuda" onChange={(e) => setForm({ ...form, condicion_materna: e.target.value })}
                    className="w-full p-3 min-h-11 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-400 disabled:opacity-60">
                    {Object.entries(CONDICIONES_MATERNAS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select>
                </div>
              </div>
              <p id="cons-contexto-ayuda" className="text-xs text-slate-600">Gestante y puérpera se registran según la evaluación del profesional, en pacientes con sexo femenino registrado. El tipo de atención no lo decide el puntaje ML.</p>
            </fieldset>

            {pacienteSeleccionado && <>
              <AlertaClinica {...revision} observaciones={observacionesVigentes} />
              {evaluacionSeleccionada?.observaciones_clinicas && <label className="flex items-start gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={Boolean(form.usar_observaciones_evaluacion)} disabled={guardando || cargandoDetalle}
                  onChange={e => setForm({...form,usar_observaciones_evaluacion:e.target.checked})} className="mt-1 w-4 h-4 shrink-0 accent-[#17324c]" />
                <span>He verificado que las mediciones de evaluación #{evaluacionSeleccionada.id} ({new Date(evaluacionSeleccionada.created_at).toLocaleString()}) corresponden a esta visita. Usarlas sin volver a transcribir. Solo se admiten evaluaciones de hoy.</span>
              </label>}
              <ObservacionesForm value={form} onChange={setForm} disabled={guardando || cargandoDetalle || form.usar_observaciones_evaluacion} />
            </>}

            <div>
              <label
                className="block text-xs font-semibold text-slate-700 mb-1"
                htmlFor="cons-diagnostico"
              >
                Diagnóstico Final del Médico *
              </label>
              <textarea
                id="cons-diagnostico"
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
                <label
                  className="block text-xs font-semibold text-slate-700 mb-1"
                  htmlFor="cons-tratamiento"
                >
                  Tratamiento / Receta *
                </label>
                <textarea
                  id="cons-tratamiento"
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
                <label
                  className="block text-xs font-semibold text-slate-700 mb-1"
                  htmlFor="cons-indicaciones"
                >
                  Indicaciones Generales
                </label>
                <textarea
                  id="cons-indicaciones"
                  rows="3"
                  value={form.indicaciones}
                  onChange={(e) => setForm({ ...form, indicaciones: e.target.value })}
                  placeholder="Dieta, exámenes auxiliares o cita de control..."
                  className="w-full p-3 text-sm bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-sky-400 transition"
                />
              </div>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end gap-4 pt-4 border-t border-slate-200">
              {hayAlerta(revision.alerta) && <p role="alert" className="mr-3 text-sm font-semibold text-rose-900">{revision.alerta.titulo}. No esperar al registro para solicitar valoración.</p>}
              <button
                type="submit"
                disabled={!pacienteSeleccionado || guardando || cargandoDetalle}
                className="flex items-center justify-center gap-2 px-5 py-3 min-h-11 shrink-0 bg-[#17324c] hover:bg-slate-800 text-white rounded-xl text-sm font-semibold transition-colors cursor-pointer disabled:opacity-40"
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
            <div className="clinical-panel p-5">
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
                      <TarjetaAtencion atencion={a} />
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
