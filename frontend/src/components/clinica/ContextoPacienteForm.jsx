import { useId } from 'react';
import { CAMPOS_MATERNOS, etiquetaGrupo } from '../../utils/clinica';

export default function ContextoPacienteForm({ value, onChange, sexo, grupo, disabled = false }) {
  const id = useId();
  const condicion = value.condicion_materna ?? 'ninguna';
  const cambiar = (categoria) => {
    if (categoria === condicion) return;
    if (Object.values(value.datos_maternos ?? {}).some(v => v !== '' && v != null)
      && !window.confirm('Al cambiar la categoría se limpiarán los datos maternos de este formulario. Las visitas guardadas se conservarán. ¿Continuar?')) return;
    onChange({ ...value, condicion_materna: categoria, datos_maternos: {} });
  };

  return (
    <fieldset disabled={disabled} className="patient-context space-y-3">
      <legend className="text-sm font-semibold text-slate-800 mb-2">Categoría de atención</legend>
      {sexo !== 'F' ? <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
        <strong className="font-medium">General</strong><span className="ml-2 text-xs">{grupo ? etiquetaGrupo(grupo) : 'Grupo según fecha de nacimiento'}</span>
        <p className="text-xs leading-relaxed text-slate-600 mt-2">Gestante y puérpera se habilitan para pacientes con sexo femenino registrado.</p>
      </div> : <div className="patient-category-options">
        {[
          ['ninguna', 'General', grupo ? etiquetaGrupo(grupo) : 'Según fecha de nacimiento'],
          ['gestante', 'Gestante', 'Durante el embarazo'],
          ['puerpera', 'Puérpera', 'Después del parto'],
        ].map(([clave, titulo, detalle]) => (
          <label key={clave} className="patient-category-choice">
            <input type="radio" name={`${id}-categoria`} value={clave} checked={condicion === clave}
              disabled={disabled || (clave !== 'ninguna' && sexo !== 'F')} onChange={() => cambiar(clave)} />
            <span><strong>{titulo}</strong><small>{detalle}</small></span>
          </label>
        ))}
      </div>}
      {sexo === 'F' && <p className="text-xs leading-relaxed text-slate-600">El grupo por edad se calcula con la fecha de nacimiento. Confirma o cambia la categoría en cada visita para completar su FUA.</p>}
      {Object.values(value.datos_maternos ?? {}).some(v => v !== '' && v != null) && <p className="text-xs leading-relaxed text-slate-600">Verifica que estos datos correspondan a esta visita.</p>}
      {CAMPOS_MATERNOS[condicion] && (
        <div className="patient-maternal-fields">
          <p className="text-xs text-slate-600 sm:col-span-2">Datos de {condicion === 'gestante' ? 'gestación' : 'puerperio'} para el FUA. Deja vacíos los datos que aún no están registrados.</p>
          {CAMPOS_MATERNOS[condicion].map(([campo, titulo, tipo]) => (
            <div key={campo}>
              <label htmlFor={`${id}-${campo}`} className="block text-xs font-medium text-slate-700 mb-1.5">{titulo}</label>
              <input id={`${id}-${campo}`} type={tipo} value={value.datos_maternos?.[campo] ?? ''}
                min={tipo === 'number' ? (campo.startsWith('numero_') ? 1 : 0) : undefined}
                step={tipo === 'number' ? (campo.startsWith('numero_') ? '1' : '0.1') : undefined}
                max={campo === 'fecha_parto' ? new Date().toLocaleDateString('en-CA') : undefined}
                onChange={e => onChange({ ...value, datos_maternos: { ...value.datos_maternos, [campo]: e.target.value } })}
                className="w-full p-3 min-h-11 text-sm bg-white border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-400 focus:outline-none" />
            </div>
          ))}
        </div>
      )}
    </fieldset>
  );
}
