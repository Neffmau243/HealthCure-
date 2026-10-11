import { api } from './api'

export const atencionesService = {
  /** POST /atenciones/ → registra diagnóstico/tratamiento */
  async crear(payload) {
    const { data } = await api.post('/atenciones/', payload)
    return data
  },

  /** GET /atenciones/?limit&offset */
  async listar({ limit = 50, offset = 0 } = {}) {
    const { data } = await api.get('/atenciones/', { params: { limit, offset } })
    return data
  },

  /** GET /atenciones/by-paciente/{id} */
  async porPaciente(pacienteId) {
    const { data } = await api.get(`/atenciones/by-paciente/${pacienteId}`)
    return data
  },

  /** GET /atenciones/{id} */
  async obtener(id) {
    const { data } = await api.get(`/atenciones/${id}`)
    return data
  },
}
