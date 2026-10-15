import { api } from './api.js'

export const authService = {
  /** POST /auth/login → { access_token, token_type, usuario } */
  async login(email, password) {
    // Un 401 aquí pertenece al formulario: debe mostrar el error y permitir reintentar.
    const { data } = await api.post('/auth/login', { email, password }, { skipAuthRedirect: true })
    return data
  },

  /** GET /auth/me → datos del usuario autenticado */
  async me() {
    const { data } = await api.get('/auth/me')
    return data
  },
}
