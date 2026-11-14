import PageHeader from '../components/ui/PageHeader';
import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import {
  Search,
  User,
  BrainCircuit,
  Stethoscope,
  CheckCircle2,
  Loader2,
  FileDown,
} from 'lucide-react';
import { pacientesService } from '../services/pacientes';
import { evaluacionesService } from '../services/evaluaciones';
import { atencionesService } from '../services/atenciones';
import { mensajeError } from '../services/api';
import { Cargando, Alerta, Vacio } from '../components/ui/Feedback';
import TarjetaTriaje from '../components/triaje/TarjetaTriaje';
import TarjetaAtencion from '../components/atenciones/TarjetaAtencion';
import { TIPOS_ATENCION, LUGARES_ATENCION, contextoPaciente, datosMaternos, etiquetaCategoria, etiquetaGrupo, evaluacionDeHoy } from '../utils/clinica';
import { calcularEdad, etiquetaSexo, nombreCompleto, clasesClasificacion } from '../utils/triaje';
import MedicionesFuaForm from '../components/atenciones/MedicionesFuaForm';
import { construirObservaciones, formDesdeObservaciones } from '../utils/observaciones';
import ContextoPacienteForm from '../components/clinica/ContextoPacienteForm';

const FORM_VACIO = { diagnostico: '', tratamiento: '', indicaciones: '', tipo_atencion: 'ambulatoria', lugar_atencion: 'intramural', condicion_materna: 'ninguna', usar_observaciones_evaluacion: false };
const nuevoFormulario = (paciente) => ({ ...FORM_VACIO, ...contextoPaciente(paciente) });

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
  const [atencionGuardada, setAtencionGuardada] = useState(null);
  const [descargandoFua, setDescargandoFua] = useState(false);
  const resultadoRef = useRef(null);
  const pacienteRef = useRef(null);
  const busquedaRef = useRef(null);
  const observaciones = construirObservaciones(form, form.condicion_materna);

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
          setForm(nuevoFormulario(inicial));
          setCargandoDetalle(true);
        }
      })
      .catch((e) => { if (activo) setError(mensajeError(e, 'No se pudieron cargar los pacientes')); })
      .finally(() => { if (activo) setCargando(false); });
    return () => { activo = false; };
  }, [pacienteInicialId]);

  const pacienteId = pacienteSeleccionado?.id;
  useEffect(() => {
    if (pacienteId && window.matchMedia('(max-width: 1023px)').matches) {
      pacienteRef.current?.scrollIntoView({ block: 'start' });
      pacienteRef.current?.focus({ preventScroll: true });
    }
  }, [pacienteId]);
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
        setEvaluacionSeleccionada(null);
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
    if (pacienteSeleccionado && JSON.stringify(form) !== JSON.stringify(nuevoFormulario(pacienteSeleccionado))
      && !window.confirm('Tienes datos de una atención sin guardar. ¿Descartarlos para cambiar de paciente?')) return;
    setPacienteSeleccionado(paciente);
    setForm(nuevoFormulario(paciente));
    setAtencionGuardada(null);
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
      const nueva = await atencionesService.crear({
        paciente_id: pacienteSeleccionado.id,
        evaluacion_id: evaluacionSeleccionada?.id ?? null,
        diagnostico: form.diagnostico.trim(),
        tratamiento: form.tratamiento.trim(),
        indicaciones: form.indicaciones.trim() || null,
        tipo_atencion: form.tipo_atencion,
        lugar_atencion: form.lugar_atencion,
        condicion_materna: form.condicion_materna,
        datos_maternos: datosMaternos(form),
        observaciones_clinicas: form.usar_observaciones_evaluacion ? null : observaciones,
        usar_observaciones_evaluacion: Boolean(form.usar_observaciones_evaluacion),
      });
      const actualizado = { ...pacienteSeleccionado, contexto_atencion: { condicion_materna: form.condicion_materna, datos_maternos: datosMaternos(form) } };
      setPacienteSeleccionado(actualizado);
      setPacientes(lista => lista.map(p => p.id === actualizado.id ? actualizado : p));
      setForm(nuevoFormulario(actualizado));
      setEvaluacionSeleccionada(null);
      setAtencionGuardada(nueva);
      setExito('Atención registrada correctamente.');
      setAtenciones(lista => [nueva, ...lista]);
    } catch (err) {
      setErrorForm(mensajeError(err, 'No se pudo registrar la atención'));
    } finally {
      setGuardando(false);
    }
  };

  useEffect(() => {
    if (atencionGuardada) {
      resultadoRef.current?.scrollIntoView({ block: 'start' });
      resultadoRef.current?.focus({ preventScroll: true });
    }
  }, [atencionGuardada]);

  const descargarFua = async () => {
    setDescargandoFua(true);
    try {
      await atencionesService.descargarFua(atencionGuardada.id);
    } catch (e) {
      setErrorForm(mensajeError(e, 'No se pudo descargar el FUA'));
    } finally {
      setDescargandoFua(false);
    }
  };

  const termino = busqueda.trim().toLowerCase();
  const pacientesDisponibles = termino
    ? pacientes.filter((p) =>
        [p.documento_identidad, p.nombre_completo, p.apellido_paterno, p.apellido_materno, p.nombres]
          .filter(Boolean)
          .some((c) => String(c).toLowerCase().includes(termino))
      )
    : pacientes;

  return (
    <div className="space-y-6">
      <PageHeader title="Consultorio médico" description="Selecciona al paciente, confirma la categoría de esta visita y registra la atención para emitir su FUA." />

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
                ref={busquedaRef}
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
                      aria-pressed={pacienteSeleccionado?.id === p.id}
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
                      {p.contexto_atencion?.condicion_materna !== 'ninguna' && p.contexto_atencion?.condicion_materna && <p className="text-xs font-medium text-sky-800 mt-1">{etiquetaCategoria(p.contexto_atencion.condicion_materna, p.grupo_etario)}</p>}
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Evaluaciones del paciente */}
          {pacienteSeleccionado && <div className="clinical-panel p-5">
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
                <button type="button" disabled={guardando} aria-pressed={!evaluacionSeleccionada}
                  onClick={() => { setEvaluacionSeleccionada(null); setForm(prev => ({ ...prev, usar_observaciones_evaluacion: false })); }}
                  className="w-full p-3 min-h-11 text-left text-xs rounded-lg bg-slate-100 hover:bg-slate-200 cursor-pointer">Atender sin vincular una evaluación ML</button>
                {evaluaciones.map((ev) => (
                  <button
                    key={ev.id}
                    disabled={guardando}
                    onClick={() => {const obs = ev.observaciones_clinicas ?? {}; setEvaluacionSeleccionada(ev); setForm({...form,usar_observaciones_evaluacion:false,tipo_atencion:obs.tipo_atencion ?? form.tipo_atencion,lugar_atencion:obs.lugar_atencion ?? form.lugar_atencion});}}
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
                  </button>
                ))}
              </div>
            )}
          </div>}
        </div>

        {/* COLUMNA DERECHA: Resultado ML + acto médico */}
        <div className="space-y-6 lg:col-span-2">
          {!pacienteSeleccionado && <Vacio titulo="Selecciona un paciente para empezar" detalle="La categoría y los datos del FUA se confirman en cada visita. Una misma persona puede pasar de atención general a gestante o puérpera sin modificar su historial." icono={Stethoscope} />}
          {pacienteSeleccionado && <details className="consultation-reference">
            <summary>Evaluación cardiovascular de referencia (opcional)</summary>

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
          </details>}

          {pacienteSeleccionado && <form
            onSubmit={handleSubmit}
            onChange={() => setExito(null)}
            className="consultation-form space-y-5"
          >
            <h3 className="font-semibold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
              <Stethoscope className="w-5 h-5 text-sky-600" /> Registro de la atención
            </h3>
            <div ref={pacienteRef} tabIndex={-1} className="pb-4 border-b border-slate-100 scroll-mt-5">
              <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-base font-semibold text-slate-800">{nombreCompleto(pacienteSeleccionado)}</h2>
                <button type="button" disabled={guardando} onClick={() => busquedaRef.current?.focus()} className="lg:hidden report-btn">Cambiar paciente</button></div>
              <p className="text-xs text-slate-600 mt-1">Doc. {pacienteSeleccionado.documento_identidad} · {calcularEdad(pacienteSeleccionado.fecha_nacimiento)} años · {etiquetaGrupo(pacienteSeleccionado.grupo_etario)}</p>
            </div>

            {errorForm && <Alerta>{errorForm}</Alerta>}
            {exito && <div ref={resultadoRef} tabIndex={-1} className="space-y-3 scroll-mt-5"><Alerta tipo="exito">{exito} Puedes descargar el FUA de esta visita.</Alerta>
              <button type="button" onClick={descargarFua} disabled={descargandoFua} className="report-btn"><FileDown className="w-4 h-4" aria-hidden="true" />{descargandoFua ? 'Generando FUA…' : `Descargar FUA de atención #${atencionGuardada.id}`}</button>
            </div>}

            <fieldset disabled={guardando || cargandoDetalle} className="space-y-5">
            <ContextoPacienteForm value={form} onChange={setForm} sexo={pacienteSeleccionado.sexo} grupo={pacienteSeleccionado.grupo_etario} />

            {pacienteSeleccionado && <>
              <details className="consultation-reference">
              <summary>Datos para el FUA: mediciones, atención y lugar (opcional)</summary>
              <div className="space-y-4">
              {evaluacionDeHoy(evaluacionSeleccionada) && evaluacionSeleccionada?.observaciones_clinicas && <label className="flex items-start gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={Boolean(form.usar_observaciones_evaluacion)} disabled={guardando || cargandoDetalle}
                  onChange={e => setForm({...form,usar_observaciones_evaluacion:e.target.checked})} className="mt-1 w-4 h-4 shrink-0 accent-[#17324c]" />
                <span>He verificado que las mediciones de evaluación #{evaluacionSeleccionada.id} ({new Date(evaluacionSeleccionada.created_at).toLocaleString()}) corresponden a esta visita. Usarlas sin volver a transcribir. Solo se admiten evaluaciones de hoy.</span>
              </label>}
              <MedicionesFuaForm value={form.usar_observaciones_evaluacion ? formDesdeObservaciones(evaluacionSeleccionada.observaciones_clinicas) : form} onChange={setForm} disabled={guardando || cargandoDetalle || form.usar_observaciones_evaluacion} />
              </div>
              </details>
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

            </fieldset>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end gap-4 pt-4 border-t border-slate-200">
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
          </form>}

          {/* Atenciones previas */}
          {pacienteSeleccionado && (
            <details className="clinical-panel p-5">
              <summary className="font-semibold text-slate-800 cursor-pointer min-h-11">Atenciones registradas ({atenciones.length})</summary>

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
            </details>
          )}
        </div>
      </div>
    </div>
  );
}
