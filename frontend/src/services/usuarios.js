import { api } from './api'

export const usuariosService = {
  /** GET /admin/usuarios (solo admin) */
  async listar() {
    const { data } = await api.get('/admin/usuarios')
    return data
  },

  /** POST /admin/usuarios (solo admin, permite elegir rol) */
  async crear(payload) {
    const { data } = await api.post('/admin/usuarios', payload)
    return data
  },

  /** PUT /admin/usuarios/{id} (update parcial) */
  async actualizar(usuarioId, payload) {
    const { data } = await api.put(`/admin/usuarios/${usuarioId}`, payload)
    return data
  },

  /** PUT /admin/usuarios/{id}/activate */
  async activar(id) {
    const { data } = await api.put(`/admin/usuarios/${id}/activate`)
    return data
  },

  /** PUT /admin/usuarios/{id}/deactivate */
  async desactivar(id) {
    const { data } = await api.put(`/admin/usuarios/${id}/deactivate`)
    return data
  },
}
