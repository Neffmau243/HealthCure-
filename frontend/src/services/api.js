import axios from 'axios'

// URL base del backend FastAPI.
// Se puede sobreescribir con VITE_API_URL (ver frontend/.env.example).
export const BASE_URL =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

export const api = axios.create({ baseURL: BASE_URL })

// Inyecta el token JWT en cada petición autenticada.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Si el token expira (401), limpiamos la sesión y volvemos al login.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
    }
    return Promise.reject(error)
  }
)

// Extrae un mensaje legible de un error de axios/FastAPI.
// FastAPI devuelve {"detail": "..."} o, en 422, {"detail": [{msg, loc}, ...]}.
export function mensajeError(error, fallback = 'Ocurrió un error inesperado') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join(', ')
  }
  return error?.message || fallback
}

// Dispara la descarga de un blob (usado por el PDF FUA).
export function descargarBlob(blob, nombreArchivo) {
  const url = window.URL.createObjectURL(blob)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = nombreArchivo
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  window.URL.revokeObjectURL(url)
}
