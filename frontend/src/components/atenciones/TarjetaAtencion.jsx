import { useState } from 'react'
import { FileDown, Loader2 } from 'lucide-react'
import { atencionesService } from '../../services/atenciones'
import { mensajeError } from '../../services/api'
import { TIPOS_ATENCION, CONDICIONES_MATERNAS, etiquetaGrupo } from '../../utils/clinica'
import AlertaClinica from '../clinica/AlertaClinica'

export default function TarjetaAtencion({ atencion: a, mostrarPaciente = false }) {
  const [descargando, setDescargando] = useState(false)
  const [error, setError] = useState(null)

  const descargar = async () => {
    if (descargando) return
    setDescargando(true)
    setError(null)
    try {
      await atencionesService.descargarFua(a.id)
    } catch (e) {
      setError(mensajeError(e, 'No se pudo descargar el FUA de la atención'))
    } finally {
      setDescargando(false)
    }
  }

  return (
    <article className="visit-record">
      <div className="visit-header">
        <div>
          {mostrarPaciente && <h3 className="visit-patient">{a.paciente_nombre ?? `Paciente #${a.paciente_id}`}</h3>}
          <p className="text-xs text-slate-500 mt-1 leading-relaxed">
            Atención #{a.id} · {new Date(a.created_at).toLocaleString()}
            {a.evaluacion_id ? ` · evaluación #${a.evaluacion_id}` : ' · sin evaluación ML asociada'}
          </p>
        </div>
        <button type="button" onClick={descargar} disabled={descargando}
          aria-label={`Descargar FUA de atención ${a.id}`}
          className="inline-flex items-center gap-2 px-3 py-2.5 min-h-11 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition cursor-pointer disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-600">
          {descargando ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : <FileDown className="w-4 h-4" aria-hidden="true" />}
          {descargando ? 'Generando FUA…' : 'Descargar FUA'}
        </button>
      </div>
      <dl className="visit-context">
        <div><dt>Tipo de atención</dt><dd>{TIPOS_ATENCION[a.tipo_atencion] ?? 'No registrado'}</dd></div>
        <div><dt>Grupo al atender</dt><dd>{etiquetaGrupo(a.grupo_etario)}{a.edad_al_atender != null ? ` · ${a.edad_al_atender} años` : ''}</dd></div>
        <div><dt>Condición materna</dt><dd>{CONDICIONES_MATERNAS[a.condicion_materna] ?? 'No registrada'}</dd></div>
      </dl>
      <AlertaClinica alerta={a.alerta_clinica} observaciones={a.observaciones_clinicas} historica />
      <div className="visit-notes">
        <div><h4>Diagnóstico</h4><p>{a.diagnostico}</p></div>
        <div><h4>Tratamiento</h4><p>{a.tratamiento}</p></div>
        {a.indicaciones && <div className="sm:col-span-2"><h4>Indicaciones</h4><p>{a.indicaciones}</p></div>}
      </div>
      {error && <p role="alert" className="text-xs text-rose-700">{error}</p>}
    </article>
  )
}
