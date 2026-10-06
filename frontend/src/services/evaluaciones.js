import { api, descargarBlob } from './api'

export const evaluacionesService = {
  /** POST /evaluaciones/ → predicción ML + triaje clínico */
  async crear(payload) {
    const { data } = await api.post('/evaluaciones/', payload)
    return data
  },

  /** GET /evaluaciones/?limit&offset */
  async listar({ limit = 50, offset = 0 } = {}) {
    const { data } = await api.get('/evaluaciones/', { params: { limit, offset } })
    return data
  },

  /** GET /evaluaciones/by-paciente/{id} → historial del paciente */
  async porPaciente(pacienteId) {
    const { data } = await api.get(`/evaluaciones/by-paciente/${pacienteId}`)
    return data
  },

  /** GET /evaluaciones/{id} */
  async obtener(id) {
    const { data } = await api.get(`/evaluaciones/${id}`)
    return data
  },

  /**
   * GET /evaluaciones/{id}/fua → descarga el PDF (Formato Único de Atención).
   * Se descarga como blob porque la ruta requiere el header Authorization.
   */
  async descargarFua(id) {
    const { data } = await api.get(`/evaluaciones/${id}/fua`, {
      responseType: 'blob',
    })
    descargarBlob(data, `fua_${id}.pdf`)
  },
}
