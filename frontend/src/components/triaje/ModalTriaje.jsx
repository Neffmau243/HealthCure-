import { cloneElement, useId, useState } from 'react';
import { Loader2, Info, BrainCircuit } from 'lucide-react';
import { edadACategoria, obtenerEdad, nombreCompleto, parsePresion } from '../../utils/triaje';
import { Alerta } from '../ui/Feedback';
import { useDialogoAccesible } from '../../hooks/useDialogoAccesible';
import MedicionesFuaForm from '../atenciones/MedicionesFuaForm';
import ContextoPacienteForm from '../clinica/ContextoPacienteForm';
import { contextoPaciente } from '../../utils/clinica';

const inputClass =
  'w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-sky-400 focus:outline-none';

const FORM_INICIAL = {
  // Signos vitales
  peso_kg: '',
  talla_cm: '',
  presionArterial: '',
  // Antecedentes
  hipertensionPrevia: false,
  colesterolAlto: false,
  derrame: false,
  dificultadCaminar: false,
  // Hábitos
  fuma: false,
  actividadFisica: false,
  // Percepción de salud
  diabetes: '0',
  saludGeneral: '3',
  // Datos administrativos del FUA (no entran al modelo)
  tipo_atencion: 'ambulatoria',
  lugar_atencion: 'intramural',
};

// Orden visible del formulario. El paso 4 no interviene en el modelo.
const PASOS = [
  ['1', 'Signos de hoy'],
  ['2', 'Antecedentes y hábitos'],
  ['3', 'Salud general'],
  ['4', 'FUA (opcional)'],
];

/**
 * Arma el formulario precargando:
 *   - Peso y talla del REGISTRO del paciente (lo que se capturó al registrarlo).
 *   - Antecedentes, hábitos y percepción de salud de su última evaluación,
 *     como referencia que debe verificarse en cada visita.
 * El indicador anterior de presión alta no prueba un diagnóstico previo.
 * La lectura de presión se registra para esta visita.
 */
const formInicialTriaje = (paciente, ultimaEvaluacion) => ({
  ...FORM_INICIAL,
  ...contextoPaciente(paciente),
  // Del registro administrativo del paciente
  peso_kg: paciente?.peso_kg ?? '',
  talla_cm: paciente?.talla_cm ?? '',
  ...(ultimaEvaluacion
    ? {
        colesterolAlto: Boolean(ultimaEvaluacion.colesterol_alto),
        derrame: Boolean(ultimaEvaluacion.antecedente_acv),
        dificultadCaminar: Boolean(ultimaEvaluacion.dificultad_para_caminar),
        fuma: Boolean(ultimaEvaluacion.tabaquismo),
        actividadFisica: Boolean(ultimaEvaluacion.actividad_fisica),
        diabetes: ultimaEvaluacion.diabetes ? '2' : '0',
        saludGeneral: String(ultimaEvaluacion.salud_general ?? 3),
      }
    : {}),
});

function NumeroPaso({ children }) {
  return (
    <span className="w-6 h-6 shrink-0 rounded-full bg-[#17324c] text-white text-[11px] font-bold flex items-center justify-center">
      {children}
    </span>
  );
}

function Seccion({ paso, titulo, nota, children }) {
  return (
    <fieldset className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
      <legend className="w-full mb-1">
        <span className="flex flex-wrap items-center gap-2">
          <NumeroPaso>{paso}</NumeroPaso>
          <span className="text-sm font-semibold text-slate-800">{titulo}</span>
          {nota && <span className="text-[11px] font-normal text-slate-500">{nota}</span>}
        </span>
      </legend>
      {children}
    </fieldset>
  );
}

/**
 * Campo con etiqueta ASOCIADA de verdad (`htmlFor` + `id`).
 * Antes el <label> y el input eran hermanos sueltos, así que el campo no
 * tenía nombre accesible y el lector de pantalla anunciaba "cuadro de edición".
 */
function Campo({ label, children, ayuda }) {
  const id = useId();
  const hijo = cloneElement(children, {
    id,
    'aria-describedby': ayuda ? `${id}-ayuda` : undefined,
  });
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-medium text-slate-700 mb-1">
        {label}
      </label>
      {hijo}
      {ayuda && (
        <p id={`${id}-ayuda`} className="text-[11px] text-slate-500 mt-1">
          {ayuda}
        </p>
      )}
    </div>
  );
}

/** La casilla ya envuelve al input, así que su etiqueta sí está asociada. */
function Casilla({ name, label, checked, onChange }) {
  return (
    <label
      className={`flex items-start gap-2.5 text-sm text-slate-700 cursor-pointer rounded-xl border p-3 min-h-11 transition ${
        checked ? 'bg-sky-50 border-sky-300' : 'bg-slate-50/60 border-slate-200 hover:bg-slate-50'
      }`}
    >
      <input
        type="checkbox"
        name={name}
        checked={checked}
        onChange={onChange}
        className="mt-0.5 h-4 w-4 rounded border-slate-300 accent-[#17324c]"
      />
      <span>{label}</span>
    </label>
  );
}

// EXPO-ML 02 | Capturar las respuestas de la evaluación del paciente seleccionado.
// Los predictores se envían al modelo; los datos de visita se guardan en observaciones.
// Al guardar, TriajePage llama a construirPayloadEvaluacion: EXPO-ML 03.
export default function ModalTriaje({
  paciente,
  ultimaEvaluacion,
  onClose,
  onGuardar,
  onGuardarContexto,
  guardando,
  error,
}) {
  // El modal solo se monta al abrirse, así el formulario arranca con los datos
  // precargados del paciente y de su última evaluación.
  const [form, setForm] = useState(() => formInicialTriaje(paciente, ultimaEvaluacion));

  // Scroll bloqueado, Escape, clic fuera y foco inicial: ver el hook.
  const { propsContenedor, alClicFondo } = useDialogoAccesible({
    abierto: true,
    onClose,
    ocupado: guardando,
  });

  const tieneRegistro = Boolean(paciente?.peso_kg || paciente?.talla_cm);
  const precargado = tieneRegistro || Boolean(ultimaEvaluacion);

  const handleChange = (e) => {
    const { name, type, checked, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  // El modelo solo aplica a adultos con edad conocida (el dataset es de 18 años o más).
  const edad = obtenerEdad(paciente);
  const sinEdadValida = edadACategoria(edad) === null;

  // Lectura ya capturada, mostrada desglosada para que se vea qué se guarda.
  const presion = parsePresion(form.presionArterial);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (sinEdadValida || guardando) return;
    onGuardar(form);
  };

  return (
    <div
      className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50"
      onClick={alClicFondo}
    >
      <div
        {...propsContenedor}
        aria-labelledby="titulo-triaje"
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] shadow-2xl border border-slate-100 flex flex-col"
      >
        <div className="px-6 lg:px-8 pt-6 lg:pt-8 pb-4 border-b border-slate-100 shrink-0">
          <h2 id="titulo-triaje" className="text-xl font-bold text-slate-800 mb-1">
            Registro de Triaje
          </h2>
          <p className="text-xs text-slate-500">
            Paciente:{' '}
            <span className="font-semibold text-slate-700">{nombreCompleto(paciente)}</span> (Doc:{' '}
            {paciente?.documento_identidad}) · {edad != null ? `${edad} años` : 'edad desconocida'}
          </p>
          <ol className="mt-3 flex flex-wrap items-center gap-x-1.5 gap-y-1">
            {PASOS.map(([numero, titulo], indice) => (
              <li key={numero} className="flex items-center gap-1.5">
                {indice > 0 && (
                  <span className="text-slate-300 text-xs" aria-hidden="true">
                    ›
                  </span>
                )}
                <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
                  <span className="font-bold text-slate-700">{numero}</span> {titulo}
                </span>
              </li>
            ))}
          </ol>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col min-h-0 flex-1">
          <div className="overflow-y-auto px-6 lg:px-8 py-5 space-y-4 flex-1">
            {error && <Alerta>{error}</Alerta>}

            {precargado && (
              <div className="flex items-start gap-2.5 text-xs text-sky-900 bg-sky-50 border border-sky-200 rounded-xl p-3">
                <Info className="w-4 h-4 mt-0.5 shrink-0 text-sky-600" aria-hidden="true" />
                <span>
                  Hay datos precargados de registros anteriores. Revísalos y corrige lo que haya cambiado en esta visita.
                </span>
              </div>
            )}

            {sinEdadValida && (
              <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-xl p-3">
                El modelo de riesgo solo aplica a pacientes de 18 años o más con fecha de nacimiento
                registrada. Actualiza la fecha de nacimiento del paciente antes de evaluarlo.
              </p>
            )}

            <Seccion
              paso="1"
              titulo="Signos de esta visita"
              nota="Obligatorio · se usa para el modelo y el FUA"
            >
              <Campo
                label="Presión arterial (mmHg)"
                ayuda="Escribe la lectura completa, por ejemplo 120/80."
              >
                <input
                  type="text"
                  name="presionArterial"
                  required
                  inputMode="numeric"
                  autoComplete="off"
                  pattern="\d{2,3}\s*/\s*\d{2,3}"
                  title="Formato: 120/80"
                  value={form.presionArterial}
                  onChange={handleChange}
                  placeholder="120/80"
                  className={inputClass}
                />
              </Campo>
              <div className="grid grid-cols-2 gap-2" aria-live="polite">
                <div className="rounded-xl bg-slate-50 border border-slate-200 px-3 py-2">
                  <p className="text-[11px] text-slate-500">Sistólica</p>
                  <p className="text-sm font-semibold text-slate-800">
                    {presion ? `${presion.sistolica} mmHg` : '—'}
                  </p>
                </div>
                <div className="rounded-xl bg-slate-50 border border-slate-200 px-3 py-2">
                  <p className="text-[11px] text-slate-500">Diastólica</p>
                  <p className="text-sm font-semibold text-slate-800">
                    {presion ? `${presion.diastolica} mmHg` : '—'}
                  </p>
                </div>
              </div>
              <p className="text-[11px] text-slate-500">
                Ambas cifras quedan registradas para el FUA. No hace falta escribirlas otra vez.
              </p>
            </Seccion>

            <Seccion
              paso="2"
              titulo="Antecedentes y hábitos"
              nota="Marca solo lo confirmado en esta visita"
            >
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <Casilla name="hipertensionPrevia" label="Diagnóstico previo de hipertensión" checked={form.hipertensionPrevia} onChange={handleChange} />
                <Casilla name="colesterolAlto" label="Colesterol alto" checked={form.colesterolAlto} onChange={handleChange} />
                <Casilla name="derrame" label="Derrame cerebral previo" checked={form.derrame} onChange={handleChange} />
                <Casilla name="dificultadCaminar" label="Dificultad seria para caminar o subir escaleras" checked={form.dificultadCaminar} onChange={handleChange} />
              </div>
              <Campo label="Diabetes" ayuda="Prediabetes y diabetes cuentan igual para el modelo.">
                <select name="diabetes" value={form.diabetes} onChange={handleChange} className={inputClass}>
                  <option value="0">No tiene</option>
                  <option value="1">Prediabetes</option>
                  <option value="2">Diabetes</option>
                </select>
              </Campo>
              <div className="pt-3 border-t border-slate-100 space-y-2.5">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Hábitos</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <Casilla name="fuma" label="Ha fumado al menos 100 cigarrillos en su vida" checked={form.fuma} onChange={handleChange} />
                  <Casilla name="actividadFisica" label="Actividad física en los últimos 30 días" checked={form.actividadFisica} onChange={handleChange} />
                </div>
              </div>
            </Seccion>

            <Seccion paso="3" titulo="Percepción de salud">
              <Campo label="Salud general" ayuda="1 es excelente y 5 es mala.">
                <select name="saludGeneral" value={form.saludGeneral} onChange={handleChange} className={inputClass}>
                  <option value="1">Excelente</option>
                  <option value="2">Muy buena</option>
                  <option value="3">Buena</option>
                  <option value="4">Regular</option>
                  <option value="5">Mala</option>
                </select>
              </Campo>
            </Seccion>

            <p className="text-xs text-slate-500 leading-relaxed">
              Con los pasos 1 a 3 se calcula el riesgo. El paso 4 solo completa el FUA: no cambia el resultado del modelo.
            </p>

            <details className="consultation-reference">
              <summary className="flex items-start gap-2.5">
                <NumeroPaso>4</NumeroPaso>
                <span>
                  <span className="font-semibold">Datos para el FUA</span>
                  <span className="block text-[11px] font-normal text-slate-500">
                    Opcional · mediciones, atención, lugar y categoría de la visita
                  </span>
                </span>
              </summary>
              <div className="space-y-5">
                <ContextoPacienteForm value={form} onChange={setForm} sexo={paciente?.sexo} grupo={paciente?.grupo_etario} disabled={guardando} />
                <MedicionesFuaForm value={form} onChange={setForm} presionArterial={form.presionArterial} disabled={guardando} />
              </div>
            </details>

            <details className="text-xs text-slate-600 border-t border-slate-200 pt-3 leading-relaxed">
              <summary className="flex items-center gap-2 cursor-pointer min-h-11"><BrainCircuit className="w-4 h-4 shrink-0" aria-hidden="true" />Qué usa el modelo: 9 datos</summary>
              <p className="mt-2">El modelo recibe 9 variables: presión alta, colesterol alto, tabaquismo, actividad física, antecedente de ACV, diabetes, salud general, dificultad para caminar y edad.</p>
              <p className="mt-2">La edad se toma del paciente. Presión alta se obtiene del diagnóstico previo confirmado o de la lectura de esta visita; prediabetes se agrupa con diabetes. Peso, talla, otros signos y categoría de atención se guardan aparte.</p>
            </details>
          </div>

          {/* Acciones fijas: antes el botón de guardar quedaba ~180px por debajo
              del pliegue en un viewport de 900px y había que bajar todo el formulario. */}
          <div className="px-6 lg:px-8 py-4 border-t border-slate-100 bg-slate-50/70 rounded-b-2xl flex flex-col-reverse sm:flex-row sm:items-center sm:justify-end gap-3 shrink-0">
            <p className="text-[11px] text-slate-500 sm:mr-auto">
              Los pasos 1 a 3 alimentan el modelo; el paso 4 solo completa el FUA.
            </p>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 min-h-11 border border-slate-200 rounded-xl text-slate-600 hover:bg-white bg-white font-medium text-sm transition cursor-pointer"
            >
              Cancelar
            </button>
            {paciente?.sexo === 'F' && <button
              type="button"
              onClick={() => onGuardarContexto(form)}
              disabled={guardando}
              className="px-4 py-2.5 min-h-11 border border-slate-300 rounded-xl text-slate-700 bg-white hover:bg-slate-100 text-sm font-medium cursor-pointer disabled:opacity-50"
            >Guardar categoría para el FUA</button>}
            <button
              type="submit"
              disabled={sinEdadValida || guardando}
              className="px-5 py-2.5 min-h-11 bg-[#17324c] hover:bg-slate-800 text-white rounded-xl font-medium text-sm shadow transition cursor-pointer disabled:opacity-50 inline-flex items-center justify-center gap-2"
            >
              {guardando && <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />}
              {guardando ? 'Evaluando...' : 'Guardar y Calcular Riesgo'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
