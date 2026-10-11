import { useState } from 'react'
import { AuthContext } from './useAuth'
import { authService } from '../services/auth'

export const AuthProvider = ({ children }) => {
  // Persistimos la sesión en localStorage para sobrevivir recargas.
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user')
    return saved ? JSON.parse(saved) : null
  })
  const [token, setToken] = useState(() => localStorage.getItem('token'))

  /**
   * Inicia sesión contra el backend real.
   * `usuario` tiene la forma { id, nombre, email, rol, activo, created_at }.
   */
  const login = async (email, password) => {
    const data = await authService.login(email, password)
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.usuario))
    setToken(data.access_token)
    setUser(data.usuario)
    return data.usuario
  }

  /** Vuelve a leer el perfil del usuario autenticado. */
  const refrescarUsuario = async () => {
    const usuario = await authService.me()
    localStorage.setItem('user', JSON.stringify(usuario))
    setUser(usuario)
    return usuario
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
  }

  const isAuthenticated = Boolean(token && user)

  return (
    <AuthContext.Provider
      value={{ user, token, isAuthenticated, login, logout, refrescarUsuario }}
    >
      {children}
    </AuthContext.Provider>
  )
}
