import { api, descargarBlob } from './api'

export const evaluacionesService = {
  /** POST /evaluaciones/ → predicción ML + triaje clínico */
  async crear(payload) {
    // EXPO-ML 04 | Enviar los datos al backend y esperar su resultado.
    // La URL base /api/v1 y el JWT se añaden en services/api.js.
    // React no ejecuta XGBoost: la predicción ocurre en Python.
    // Siguiente: app/api/v1/evaluaciones.py, EXPO-ML 05.
    const { data } = await api.post('/evaluaciones/', payload)
    return data
  },

  /** GET /evaluaciones/?limit&offset */
  async listar({ limit = 50, offset = 0 } = {}) {
    const { data } = await api.get('/evaluaciones/', { params: { limit, offset } })
    return data
  },

  /**
   * GET /evaluaciones/resumen → conteos exactos para el dashboard.
   * Se resuelven con COUNT en el backend, así que no dependen de cuántas
   * filas se hayan traído (contar una página daría números falsos).
   */
  async resumen() {
    const { data } = await api.get('/evaluaciones/resumen')
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
