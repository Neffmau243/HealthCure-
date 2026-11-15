import { useState } from 'react'
import { AuthContext } from './useAuth'
import { authService } from '../services/auth'
import { leerSesionGuardada } from '../utils/sesion'

export const AuthProvider = ({ children }) => {
  // Persistimos la sesión en localStorage para sobrevivir recargas.
  const [sesion, setSesion] = useState(() => leerSesionGuardada())
  const user = sesion?.user ?? null
  const token = sesion?.token ?? null

  /**
   * Inicia sesión contra el backend real.
   * `usuario` tiene la forma { id, nombre, email, rol, activo, created_at }.
   */
  const login = async (email, password) => {
    const data = await authService.login(email, password)
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.usuario))
    setSesion({ user: data.usuario, token: data.access_token })
    return data.usuario
  }

  /** Vuelve a leer el perfil del usuario autenticado. */
  const refrescarUsuario = async () => {
    const usuario = await authService.me()
    localStorage.setItem('user', JSON.stringify(usuario))
    setSesion((actual) => actual ? { ...actual, user: usuario } : null)
    return usuario
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setSesion(null)
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
