import { api } from './api'

export const authService = {
  /** POST /auth/login → { access_token, token_type, usuario } */
  async login(email, password) {
    const { data } = await api.post('/auth/login', { email, password })
    return data
  },

  /** GET /auth/me → datos del usuario autenticado */
  async me() {
    const { data } = await api.get('/auth/me')
    return data
  },
}
