import { api, descargarBlob } from './api'
import { parametrosFiltros } from '../utils/reportes'

export const reportesService = {
  /** GET /reportes/dashboard?dias= → KPIs, tendencia diaria, bandas, distritos, factores y edades. */
  async dashboard(dias = 30, { signal } = {}) {
    const { data } = await api.get('/reportes/dashboard', { params: { dias }, signal })
    return data
  },

  /** GET /reportes/evaluaciones → tabla paginada y filtrable (desde, hasta, clasificacion, distrito_id, q). */
  async evaluaciones(filtros = {}, { limit = 10, offset = 0, signal } = {}) {
    const { data } = await api.get('/reportes/evaluaciones', {
      params: parametrosFiltros({ ...filtros, limit, offset }),
      signal,
    })
    return data
  },

  /**
   * GET /reportes/evaluaciones/export → CSV (solo administradores, sin datos personales).
   * Se descarga como blob porque la ruta exige el header Authorization.
   */
  async exportarCsv(filtros = {}) {
    const { data } = await api.get('/reportes/evaluaciones/export', {
      params: parametrosFiltros(filtros),
      responseType: 'blob',
    })
    descargarBlob(data, `evaluaciones_${new Date().toISOString().slice(0, 10)}.csv`)
  },
}
