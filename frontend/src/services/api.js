import axios from 'axios'

// URL base del backend FastAPI.
// Por defecto es relativa: el backend sirve esta interfaz en el mismo puerto
// (http://localhost:8000), así que no hay CORS ni host fijo que configurar y
// funciona igual entrando por localhost, 127.0.0.1 o la IP de la red local.
// Se puede sobreescribir con VITE_API_URL (ver frontend/.env.example).
export const BASE_URL = import.meta.env?.VITE_API_URL ?? '/api/v1'

export const api = axios.create({ baseURL: BASE_URL })

// Inyecta el token JWT en cada petición autenticada.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Un 401 de una petición protegida invalida la sesión. El login gestiona su propio
// 401 en el formulario para conservar los campos y mostrar un mensaje recuperable.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config?.skipAuthRedirect) {
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
