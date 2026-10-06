import { api } from './api'

export const catalogosService = {
  /** GET /catalogos/distritos → solo distritos activos */
  async distritos() {
    const { data } = await api.get('/catalogos/distritos')
    return data
  },

  /** GET /catalogos/localidades?distrito_id= → solo activas del distrito */
  async localidades(distritoId) {
    const { data } = await api.get('/catalogos/localidades', {
      params: distritoId ? { distrito_id: distritoId } : {},
    })
    return data
  },
}
