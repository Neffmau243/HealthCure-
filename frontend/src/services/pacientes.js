import { api } from './api'

export const pacientesService = {
  /** GET /pacientes/ → lista completa */
  async listar() {
    const { data } = await api.get('/pacientes/')
    return data
  },

  /** GET /pacientes/search?documento= → búsqueda parcial (max 10) */
  async buscar(documento) {
    const { data } = await api.get('/pacientes/search', {
      params: { documento },
    })
    return data
  },

  /** GET /pacientes/by-documento/{documento} → documento exacto */
  async porDocumento(documento) {
    const { data } = await api.get(`/pacientes/by-documento/${documento}`)
    return data
  },

  /** GET /pacientes/{id} */
  async obtener(id) {
    const { data } = await api.get(`/pacientes/${id}`)
    return data
  },

  /** POST /pacientes/ */
  async crear(payload) {
    const { data } = await api.post('/pacientes/', payload)
    return data
  },

  /** PUT /pacientes/{id} (update parcial) */
  async actualizar(id, payload) {
    const { data } = await api.put(`/pacientes/${id}`, payload)
    return data
  },
}
