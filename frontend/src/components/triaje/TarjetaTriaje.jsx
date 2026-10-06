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

/**
 * Muestra el resultado de una evaluación: probabilidad, clasificación,
 * semáforo del triaje clínico, factores y recomendaciones, y permite
 * descargar el PDF FUA.
 */
export default function TarjetaTriaje({ evaluacion, compacta = false }) {
  const [descargando, setDescargando] = useState(false);
  const [error, setError] = useState(null);

  if (!evaluacion) return null;

  const triaje = evaluacion.triaje_clinico;
  const semaforo = clasesSemaforo(triaje?.codigo_color);
  const probabilidad = (evaluacion.probabilidad * 100).toFixed(1);

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
      className={`rounded-2xl border ${semaforo.borde} ${semaforo.fondo} p-5 space-y-4`}
    >
      {/* Encabezado: clasificación + probabilidad */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className={`w-3 h-3 rounded-full ${semaforo.punto}`} />
          <div>
            <p className={`text-sm font-bold ${semaforo.texto}`}>
              {triaje?.nivel_alerta ?? 'Resultado de la evaluación'}
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
            className={`px-2.5 py-1 rounded-full text-xs font-semibold capitalize ${clasesClasificacion(
              evaluacion.clasificacion
            )}`}
          >
            Riesgo {evaluacion.clasificacion}
          </span>
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-white/70 text-slate-700 border border-white">
            {probabilidad}%
          </span>
        </div>
      </div>

      {triaje?.accion_sugerida && (
        <p className="text-sm text-slate-700">
          <span className="font-semibold">Acción sugerida: </span>
          {triaje.accion_sugerida}
        </p>
      )}

      {!compacta && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="bg-white/70 rounded-xl p-4 border border-white">
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

          <div className="bg-white/70 rounded-xl p-4 border border-white">
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

          <div className="bg-white/70 rounded-xl p-4 border border-white">
            <p className="text-xs font-semibold text-sky-800 flex items-center gap-1.5 mb-2">
              <ClipboardList className="w-3.5 h-3.5" /> Recomendaciones
            </p>
            <ul className="text-xs text-slate-700 space-y-1 list-disc list-inside">
              {triaje?.recomendaciones_medicas?.length ? (
                triaje.recomendaciones_medicas.map((r, i) => <li key={i}>{r}</li>)
              ) : (
                <li className="text-slate-400 list-none">Sin recomendaciones</li>
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
          {descargando ? 'Generando PDF...' : 'Descargar FUA (PDF)'}
        </button>
      </div>
    </div>
  );
}
