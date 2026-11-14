import { useState } from 'react';
import {
  AlertTriangle,
  ShieldCheck,
  FileDown,
  Activity,
  Loader2,
} from 'lucide-react';
import { evaluacionesService } from '../../services/evaluaciones';
import { mensajeError } from '../../services/api';
import { clasesClasificacion } from '../../utils/triaje';

/**
 * Muestra el índice del modelo, su banda y los factores registrados.
 */
// EXPO-ML 15a | Final visible del recorrido: interpretar la respuesta del backend.
// El índice se muestra sobre 100; esta tarjeta no recalcula el riesgo del paciente.
export default function TarjetaTriaje({ evaluacion, compacta = false }) {
  const [descargando, setDescargando] = useState(false);
  const [error, setError] = useState(null);

  if (!evaluacion) return null;

  const triaje = evaluacion.triaje_clinico;
  // Se muestra como ÍNDICE de riesgo, no como probabilidad: el modelo no está
  // calibrado (Brier 0.1714 vs 0.0853 del baseline, ver docs/MODEL_CARD.md),
  // así que un "82.6%" se leería como probabilidad real de enfermedad.
  const indiceRiesgo = (evaluacion.probabilidad * 100).toFixed(1)

  // Las nueve variables que recibe el modelo, con el mismo nombre que ve el
  // profesional en el Registro de Triaje. Antes solo se mostraban seis, así que
  // dos evaluaciones distintas podían parecer idénticas.
  const datosModelo = [
    ['Edad', `${evaluacion.edad} años`],
    ['Presión alta', evaluacion.presion_alta ? 'Sí' : 'No'],
    ['Colesterol alto', evaluacion.colesterol_alto ? 'Sí' : 'No'],
    ['Tabaquismo', evaluacion.tabaquismo ? 'Sí' : 'No'],
    ['Actividad física', evaluacion.actividad_fisica ? 'Sí' : 'No'],
    ['ACV previo', evaluacion.antecedente_acv ? 'Sí' : 'No'],
    ['Diabetes', evaluacion.diabetes ? 'Sí' : 'No'],
    ['Salud general', `${evaluacion.salud_general}/5`],
    ['Dificultad para caminar', evaluacion.dificultad_para_caminar ? 'Sí' : 'No'],
  ]
  const obs = evaluacion.observaciones_clinicas ?? {}
  const sistolica = Number(obs.presion_sistolica)
  const diastolica = Number(obs.presion_diastolica)
  const lecturaPresion = Number.isFinite(sistolica) && Number.isFinite(diastolica)
    ? `${sistolica}/${diastolica} mmHg`
    : null;

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
      {/* Encabezado: identificación de la evaluación y resultado en primer plano */}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-800">
            Evaluación cardiovascular
          </p>
          <p className="text-xs text-slate-500 mt-1 leading-relaxed">
            #{evaluacion.id} · {new Date(evaluacion.created_at).toLocaleString()}
            {evaluacion.modelo_version && ` · modelo v${evaluacion.modelo_version}`}
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <div className="text-right">
            <p className="text-[11px] text-slate-500">Índice de riesgo</p>
            <p
              className="text-2xl font-semibold leading-none tracking-tight text-slate-900 tabular-nums"
              title="Índice de riesgo: sirve para ordenar y priorizar. No es la probabilidad de que el paciente esté enfermo."
            >
              {indiceRiesgo}
              <span className="text-xs font-normal text-slate-400">/100</span>
            </p>
          </div>
          <span
            className={`px-2.5 py-1 rounded-full text-xs font-semibold capitalize ${clasesClasificacion(evaluacion.clasificacion)}`}
          >
            Banda ML {evaluacion.clasificacion}
          </span>
        </div>
      </header>

      {/* Advertencia explícita: evita que el número se lea como diagnóstico. */}
      <p className="text-[11px] text-slate-600 leading-relaxed">
        Índice del modelo en escala de 0 a 100. No es un diagnóstico ni una probabilidad clínica de enfermedad.
      </p>

      {!compacta && (
        <div className="evaluation-factors">
          <div className="rounded-xl border border-rose-100 bg-rose-50/60 p-3">
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

          <div className="rounded-xl border border-emerald-100 bg-emerald-50/60 p-3">
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

        </div>
      )}

      {!compacta && (
        <div className="border-t border-slate-100 pt-3">
          <p className="text-xs font-semibold text-slate-700 flex items-center gap-1.5 mb-2">
            <Activity className="w-3.5 h-3.5 text-slate-500" aria-hidden="true" />
            Datos que recibió el modelo
          </p>
          <dl className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {datosModelo.map(([etiqueta, valor]) => (
              <div key={etiqueta} className="rounded-lg bg-slate-50 border border-slate-100 px-2.5 py-1.5">
                <dt className="text-[11px] text-slate-500">{etiqueta}</dt>
                <dd className="text-xs font-semibold text-slate-800">{valor}</dd>
              </div>
            ))}
          </dl>
          {lecturaPresion && (
            <p className="text-[11px] text-slate-500 mt-2 leading-relaxed">
              Presión arterial registrada en la visita: <strong className="font-semibold text-slate-700">{lecturaPresion}</strong>.
              {' '}«Presión alta» se marca con el diagnóstico previo o con una lectura de 140/90 mmHg o más.
            </p>
          )}
          <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
            Con los mismos nueve datos el modelo devuelve el mismo índice: es determinista.
          </p>
        </div>
      )}

      {error && <p className="text-xs text-rose-700">{error}</p>}

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-t border-slate-100 pt-4">
        <p className="text-xs text-slate-600 sm:max-w-md leading-relaxed">
          El FUA final con el tipo y las condiciones de la visita se descarga desde la atención registrada en Consultorio.
        </p>
        <button
          type="button"
          onClick={descargarFua}
          disabled={descargando}
          className="inline-flex items-center justify-center gap-2 px-3.5 py-2 min-h-11 bg-[#17324c] hover:bg-slate-800 text-white rounded-xl text-xs font-semibold transition cursor-pointer disabled:opacity-50 shrink-0"
        >
          {descargando ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <FileDown className="w-3.5 h-3.5" />
          )}
          {descargando ? 'Generando PDF...' : 'Descargar tamizaje (PDF)'}
        </button>
      </div>
    </div>
  );
}
