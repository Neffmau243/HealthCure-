import { createContext, useContext } from 'react'

// Contexto de autenticación + hook de consumo.
// Vive separado de AuthProvider.jsx porque react-refresh exige que un
// archivo de componente exporte SOLO componentes.
export const AuthContext = createContext(null)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth debe ser usado dentro de un AuthProvider')
  }
  return context
}
