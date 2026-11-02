import { useState } from 'react';
import {
  AlertTriangle,
  ShieldCheck,
  ClipboardList,
  FileDown,
  Activity,
  Loader2,
} from 'lucide-react';
import { evaluacionesService } from '../../services/evaluaciones';
import { mensajeError } from '../../services/api';
import { clasesSemaforo, clasesClasificacion } from '../../utils/triaje';
import AlertaClinica from '../clinica/AlertaClinica';

/**
 * Muestra el resultado de una evaluación: probabilidad, clasificación,
 * semáforo del triaje clínico, factores y recomendaciones, y permite
 * descargar el PDF FUA.
 */
// EXPO-ML 15a | Final visible del recorrido: interpretar la respuesta del backend.
// El índice se muestra sobre 100; esta tarjeta no recalcula el riesgo del paciente.
// Las recomendaciones provienen de reglas y la decisión corresponde al profesional.
export default function TarjetaTriaje({ evaluacion, compacta = false }) {
  const [descargando, setDescargando] = useState(false);
  const [error, setError] = useState(null);

  if (!evaluacion) return null;

  const triaje = evaluacion.triaje_clinico;
  const preventiva = evaluacion.alerta_clinica?.nivel === 'sin_criterios_detectados';
  const semaforo = clasesSemaforo(preventiva ? triaje?.codigo_color : null);
  // Se muestra como ÍNDICE de riesgo, no como probabilidad: el modelo no está
  // calibrado (Brier 0.1714 vs 0.0853 del baseline, ver docs/MODEL_CARD.md),
  // así que un "82.6%" se leería como probabilidad real de enfermedad.
  const indiceRiesgo = (evaluacion.probabilidad * 100).toFixed(1);

  const descargarFua = async () => {
    setDescargando(true);
    setError(null);
    try {
      await evaluacionesService.descargarFua(evaluacion.id);
    } catch (e) {
      setError(mensajeError(e, 'No se pudo descargar el PDF'));
    } finally {
      setDescargando(false);
    }
  };

  return (
    <div
      className="evaluation-result space-y-5"
    >
      <AlertaClinica alerta={evaluacion.alerta_clinica} observaciones={evaluacion.observaciones_clinicas} historica />
      {/* Encabezado: clasificación + probabilidad */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className={`w-3 h-3 rounded-full ${semaforo.punto}`} />
          <div>
            <p className={`text-sm font-bold ${semaforo.texto}`}>
              {preventiva ? triaje?.nivel_alerta : 'Índice cardiovascular del modelo · no determina la urgencia actual'}
            </p>
            <p className="text-xs text-slate-500">
              Evaluación #{evaluacion.id} ·{' '}
              {new Date(evaluacion.created_at).toLocaleString()}
              {evaluacion.modelo_version && ` · modelo v${evaluacion.modelo_version}`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`px-2.5 py-1 rounded-full text-xs font-semibold capitalize ${preventiva ? clasesClasificacion(evaluacion.clasificacion) : 'bg-slate-100 text-slate-700'}`}
          >
            Banda ML {evaluacion.clasificacion}
          </span>
          <span
            className="px-2.5 py-1 rounded-full text-xs font-bold bg-white/70 text-slate-700 border border-white"
            title="Índice de riesgo: sirve para ordenar y priorizar. No es la probabilidad de que el paciente esté enfermo."
          >
            Índice de riesgo {indiceRiesgo}
          </span>
        </div>
      </div>

      {preventiva && triaje?.accion_sugerida && (
        <p className="text-sm text-slate-700">
          <span className="font-semibold">Acción sugerida: </span>
          {triaje.accion_sugerida}
        </p>
      )}

      {/* Advertencia explícita: evita que el número se lea como diagnóstico. */}
      <p className="text-[11px] text-slate-600 leading-relaxed">
        Este índice no evalúa la urgencia actual ni confirma enfermedad. Los signos y síntomas
        se revisan por separado y la decisión corresponde al personal de salud.
      </p>

      {!compacta && (
        <div className="evaluation-factors">
          <div>
            <p className="text-xs font-semibold text-rose-800 flex items-center gap-1.5 mb-2">
              <AlertTriangle className="w-3.5 h-3.5" /> Factores de riesgo
            </p>
            <ul className="text-xs text-slate-700 space-y-1 list-disc list-inside">
              {triaje?.factores_riesgo_detectados?.length ? (
                triaje.factores_riesgo_detectados.map((f, i) => <li key={i}>{f}</li>)
              ) : (
                <li className="text-slate-400 list-none">Sin factores detectados</li>
              )}
            </ul>
          </div>

          <div>
            <p className="text-xs font-semibold text-emerald-800 flex items-center gap-1.5 mb-2">
              <ShieldCheck className="w-3.5 h-3.5" /> Factores protectores
            </p>
            <ul className="text-xs text-slate-700 space-y-1 list-disc list-inside">
              {triaje?.factores_protectores?.length ? (
                triaje.factores_protectores.map((f, i) => <li key={i}>{f}</li>)
              ) : (
                <li className="text-slate-400 list-none">Sin factores protectores</li>
              )}
            </ul>
          </div>

          <div>
            <p className="text-xs font-semibold text-sky-800 flex items-center gap-1.5 mb-2">
              <ClipboardList className="w-3.5 h-3.5" /> Recomendaciones
            </p>
            <ul className="text-xs text-slate-700 space-y-1 list-disc list-inside">
              {preventiva && triaje?.recomendaciones_medicas?.length ? (
                triaje.recomendaciones_medicas.map((r, i) => <li key={i}>{r}</li>)
              ) : (
                <li className="text-slate-600 list-none">Las indicaciones sobre la situación actual se muestran en la revisión clínica superior.</li>
              )}
            </ul>
          </div>
        </div>
      )}

      {!compacta && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
          <Activity className="w-3.5 h-3.5" />
          <span>
            Edad {evaluacion.edad} · presión alta:{' '}
            {evaluacion.presion_alta ? 'sí' : 'no'} · colesterol alto:{' '}
            {evaluacion.colesterol_alto ? 'sí' : 'no'} · tabaquismo:{' '}
            {evaluacion.tabaquismo ? 'sí' : 'no'} · diabetes:{' '}
            {evaluacion.diabetes ? 'sí' : 'no'} · salud general:{' '}
            {evaluacion.salud_general}/5
          </span>
        </div>
      )}

      {error && <p className="text-xs text-rose-700">{error}</p>}

      <div className="pt-1">
        <button
          type="button"
          onClick={descargarFua}
          disabled={descargando}
          className="inline-flex items-center gap-2 px-3.5 py-2 bg-[#17324c] hover:bg-slate-800 text-white rounded-xl text-xs font-semibold transition cursor-pointer disabled:opacity-50"
        >
          {descargando ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <FileDown className="w-3.5 h-3.5" />
          )}
          {descargando ? 'Generando PDF...' : 'Descargar tamizaje (PDF)'}
        </button>
        <p className="text-xs text-slate-600 mt-2">El FUA final con el tipo y las condiciones de la visita se descarga desde la atención registrada en Consultorio.</p>
      </div>
    </div>
  );
}
