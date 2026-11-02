import { HeartPulse, Stethoscope, ClipboardList, ChevronDown, CircleAlert, Circle } from 'lucide-react'
import { CAMPOS_SIGNOS, SINTOMAS_ALARMA, hayAlerta } from '../../utils/observaciones'

const TITULOS = {
  inmediata: 'Signos de alarma: valoración inmediata',
  prioritaria: 'Hallazgos que requieren valoración prioritaria',
  valoracion_especifica: 'Requiere valoración pediátrica u obstétrica',
  datos_insuficientes: 'Faltan datos para valorar la urgencia',
  sin_criterios_detectados: 'Sin señales de alarma en los datos registrados',
}

export default function AlertaClinica({ alerta, observaciones, revisando=false, error, historica=false }) {
  const grave = alerta?.nivel === 'inmediata'
  const prioritaria = hayAlerta(alerta)
  const Icono = grave ? HeartPulse : prioritaria ? CircleAlert : alerta?.nivel === 'datos_insuficientes' ? ClipboardList : Stethoscope
  const estilos = grave ? 'bg-rose-50 border-rose-300 text-rose-950' : prioritaria
    ? 'bg-amber-50 border-amber-300 text-amber-950' : 'bg-slate-50 border-slate-200 text-slate-800'
  return (
    <section className={`clinical-alert ${estilos}`} aria-label="Valoración clínica de la visita" aria-live="polite" aria-busy={revisando}>
      <div className="clinical-alert-header">
        <span className="clinical-alert-icon"><Icono className="w-5 h-5" aria-hidden="true" /></span>
        <div className="min-w-0">
          <h4 className="clinical-alert-title">{TITULOS[alerta?.nivel] ?? alerta?.titulo ?? (historica ? 'Sin valoración de urgencia registrada' : 'Revisión clínica de la visita')}</h4>
          {revisando && <p className="text-xs mt-1" role="status">Revisando las mediciones y los síntomas…</p>}
          {error && <p role="alert" className="text-sm mt-2">No se pudo actualizar la revisión: {error}. Verifica los campos; el aviso anterior no corresponde a los datos nuevos.</p>}
          <p className="clinical-alert-action">{alerta?.accion ?? 'Registra los signos y síntomas actuales para apoyar la valoración. Sin estos datos no se puede concluir que el paciente esté estable.'}</p>
        </div>
      </div>
      {Boolean(alerta?.motivos?.length) && <ul className="clinical-alert-reasons">{alerta.motivos.map(motivo => <li key={motivo}><Circle className="w-2 h-2 fill-current" aria-hidden="true" /><span>{motivo}</span></li>)}</ul>}
      {alerta?.datos_faltantes?.length > 0 && <p className="clinical-alert-note"><strong className="font-medium">Pendiente de registrar: </strong>{alerta.datos_faltantes.join(', ')}.</p>}
      <details>
        <summary><ChevronDown className="w-3.5 h-3.5" aria-hidden="true" />{observaciones ? 'Mediciones registradas y alcance de la revisión' : 'Alcance de esta revisión'}</summary>
        {observaciones && <>
          <dl className="grid grid-cols-2 gap-3 mt-3">{CAMPOS_SIGNOS.map(([campo,label]) => <div key={campo}><dt className="font-medium">{label}</dt><dd>{observaciones[campo] ?? 'Sin registrar'}</dd></div>)}</dl>
          <p className="mt-3">Síntomas: {observaciones.sintomas == null ? 'No revisados' : observaciones.sintomas.length ? observaciones.sintomas.map(s => SINTOMAS_ALARMA[s] ?? s).join('; ') : 'Se confirmó ausencia de los síntomas listados'}.</p>
        </>}
        <p className="mt-3">Apoyo a la valoración del personal de salud. No establece un diagnóstico ni sustituye el protocolo asistencial local.</p>
        {alerta?.origen_evaluacion_id && <p className="mt-2">Mediciones verificadas de la evaluación #{alerta.origen_evaluacion_id} para esta visita.</p>}
        {alerta?.version_reglas && <p className="mt-2 opacity-80">Versión de la revisión: {alerta.version_reglas}.</p>}
      </details>
    </section>
  )
}
