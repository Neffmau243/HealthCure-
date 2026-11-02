import { useEffect, useState } from 'react'
import { api, mensajeError } from '../services/api'

export function useAlertaClinica(pacienteId, observaciones) {
  const [resultado, setResultado] = useState(null)
  const entrada = JSON.stringify({paciente_id: pacienteId, observaciones_clinicas: observaciones})
  useEffect(() => {
    if (!pacienteId) return
    let activo = true
    const timer = setTimeout(async () => {
      try {
        const {data} = await api.post('/clinica/revisar', JSON.parse(entrada))
        if (activo) setResultado({entrada, pacienteId, alerta:data})
      } catch (e) {
        if (activo) setResultado({entrada, pacienteId, error:mensajeError(e, 'No se pudieron revisar las señales actuales')})
      }
    }, 250)
    return () => { activo = false; clearTimeout(timer) }
  }, [entrada, pacienteId])
  return {alerta: pacienteId && resultado?.pacienteId === pacienteId ? resultado?.alerta : null,
    error: pacienteId && resultado?.entrada === entrada ? resultado.error : null,
    revisando: Boolean(pacienteId && resultado?.entrada !== entrada)}
}
