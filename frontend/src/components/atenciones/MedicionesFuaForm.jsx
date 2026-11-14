import { useId } from 'react';
import { CAMPOS_SIGNOS } from '../../utils/observaciones';
import { calcularIMC, parsePresion } from '../../utils/triaje';
import { TIPOS_ATENCION, LUGARES_ATENCION } from '../../utils/clinica';

const CAMPOS_FUA = CAMPOS_SIGNOS.filter(([campo]) => ['peso_kg', 'talla_cm', 'presion_sistolica', 'presion_diastolica'].includes(campo));

function Opciones({ id, campo, titulo, opciones, columnas, value, onChange, disabled }) {
  const actual = value?.[campo] ?? Object.keys(opciones)[0];
  return <fieldset className="space-y-2">
    <legend className="text-xs font-medium text-slate-700 mb-1.5">{titulo}</legend>
    <div className={`grid grid-cols-1 ${columnas} gap-2`}>
      {Object.entries(opciones).map(([clave, etiqueta]) => <label key={clave}
        className={`flex items-center gap-2 px-3 py-2.5 min-h-11 rounded-lg border text-sm cursor-pointer transition ${
          actual === clave ? 'bg-sky-50 border-sky-300 text-slate-900' : 'bg-slate-50 border-slate-200 text-slate-700'
        }`}>
        <input type="radio" name={`${id}-${campo}`} value={clave} checked={actual === clave} disabled={disabled}
          onChange={() => onChange({ ...value, [campo]: clave })}
          className="h-4 w-4 shrink-0 accent-[#17324c]" />
        <span>{etiqueta}</span>
      </label>)}
    </div>
  </fieldset>;
}

/**
 * Datos administrativos y mediciones que se imprimen en el FUA oficial.
 * `presionArterial` se usa en Triaje, donde la lectura ya se capturó para el
 * modelo con formato "120/80": aquí solo se muestran ambas cifras para el FUA.
 */
export default function MedicionesFuaForm({ value, onChange, presionArterial, disabled = false }) {
  const id = useId();
  const imc = calcularIMC(value.peso_kg, value.talla_cm);
  const lectura = presionArterial === undefined ? null : parsePresion(presionArterial);
  const campos = presionArterial === undefined
    ? CAMPOS_FUA
    : CAMPOS_FUA.filter(([campo]) => !campo.startsWith('presion_'));

  return <fieldset disabled={disabled} className="space-y-5">
    <legend className="text-sm font-medium text-slate-800 mb-2">Mediciones para el FUA</legend>
    <p className="text-xs text-slate-600">Completa los datos registrados por el área correspondiente. Deja vacío lo que no esté disponible.</p>
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {campos.map(([campo, titulo, min, max, step]) => <div key={campo}>
        <label htmlFor={`${id}-${campo}`} className="block text-xs font-medium text-slate-700 mb-1.5">{titulo}</label>
        <input id={`${id}-${campo}`} type="number" min={min} max={max} step={step} value={value[campo] ?? ''}
          onChange={e => onChange({ ...value, [campo]: e.target.value })}
          className="w-full p-3 min-h-11 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-400" />
      </div>)}
      {presionArterial !== undefined && <div className="sm:col-span-2">
        <p className="text-xs font-medium text-slate-700 mb-1.5">Presión arterial para el FUA</p>
        <p className="text-sm text-slate-800">
          Sistólica: <strong className="font-semibold">{lectura?.sistolica ?? 'Sin registrar'}</strong> mmHg
          {' · '}
          Diastólica: <strong className="font-semibold">{lectura?.diastolica ?? 'Sin registrar'}</strong> mmHg
        </p>
        <p className="text-xs text-slate-600 mt-1">Se toma de la lectura «Presión arterial» registrada arriba para esta visita.</p>
      </div>}
    </div>
    {imc != null && <p className="text-xs text-slate-600">IMC calculado para el FUA: <strong className="font-medium">{imc}</strong></p>}
    <Opciones id={id} campo="tipo_atencion" titulo="Atención" opciones={TIPOS_ATENCION} columnas="sm:grid-cols-3"
      value={value} onChange={onChange} disabled={disabled} />
    <Opciones id={id} campo="lugar_atencion" titulo="Lugar de atención" opciones={LUGARES_ATENCION} columnas="sm:grid-cols-2"
      value={value} onChange={onChange} disabled={disabled} />
    <p className="text-xs text-slate-600">Atención y lugar se marcan en el formulario FUA oficial al generarlo.</p>
  </fieldset>;
}
