import { useId } from 'react'
import { CAMPOS_SIGNOS, SINTOMAS_ALARMA } from '../../utils/observaciones'
import { CONDICIONES_MATERNAS } from '../../utils/clinica'

export default function ObservacionesForm({value, onChange, disabled=false, incluirPresion=true, incluirMediciones=true, mostrarCondicion=false}) {
  const id = useId()
  const set = (campo, dato) => onChange({...value,[campo]:dato})
  const sintomas = value.sintomas ?? []
  return (
    <fieldset disabled={disabled} className="observations-form space-y-4">
      <legend className="text-sm font-semibold text-slate-800 mb-2">Signos y síntomas de esta visita</legend>
      <p className="text-xs text-slate-600 leading-relaxed">Registra las mediciones de esta visita y los síntomas presentes. Deja el campo vacío si no se realizó la medición.</p>
      {incluirMediciones && <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">{CAMPOS_SIGNOS.filter(([campo]) => incluirPresion || !campo.startsWith('presion_')).map(([campo,label,min,max,step]) => <div key={campo}>
        <label htmlFor={`${id}-${campo}`} className="block text-xs font-medium text-slate-700 mb-1">{label}</label>
        <input id={`${id}-${campo}`} type="number" min={min} max={max} step={step} value={value[campo] ?? ''} onChange={e => set(campo,e.target.value)} className="w-full p-2.5 min-h-11 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-sky-400 focus:outline-none" />
      </div>)}</div>}
      {mostrarCondicion && <div>
        <label htmlFor={`${id}-materna`} className="block text-xs font-medium text-slate-700 mb-1">Condición materna de esta visita</label>
        <select id={`${id}-materna`} value={value.condicion_materna ?? ''} onChange={e => set('condicion_materna',e.target.value)} className="w-full p-2.5 min-h-11 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-sky-400 focus:outline-none">
          <option value="">No informada</option>{Object.entries(CONDICIONES_MATERNAS).map(([v,label]) => <option key={v} value={v}>{label}</option>)}
        </select>
      </div>}
      <p className="text-xs font-semibold text-slate-700">Marca los síntomas actuales presentes</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">{Object.entries(SINTOMAS_ALARMA).map(([clave,label]) => <label key={clave} className="symptom-choice flex items-start gap-2 text-sm text-slate-700 cursor-pointer">
        <input type="checkbox" checked={sintomas.includes(clave)} onChange={e => onChange({...value,sintomas:e.target.checked ? [...sintomas,clave] : sintomas.filter(s => s !== clave),sintomas_revisados:true})} className="mt-1 w-4 h-4 shrink-0 accent-[#17324c]" /><span>{label}</span>
      </label>)}</div>
      <label className="symptom-confirmation flex items-start gap-3 text-sm text-slate-700 cursor-pointer"><input type="checkbox" checked={Boolean(value.sintomas_revisados)} onChange={e => set('sintomas_revisados',e.target.checked)} className="mt-1 w-4 h-4 shrink-0 accent-[#17324c]" /><span>He revisado los síntomas de alarma de esta visita (las casillas sin marcar se confirmaron ausentes).</span></label>
    </fieldset>
  )
}
