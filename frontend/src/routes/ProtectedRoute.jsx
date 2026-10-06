import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/useAuth'
import { PERMISSIONS } from '../constants/roles'

export const ProtectedRoute = ({ path }) => {
  const { user, isAuthenticated } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  // Si no llega la prop `path`, usamos la ruta actual.
  const ruta = path || location.pathname
  const allowedRoles = PERMISSIONS[ruta]

  if (allowedRoles && !allowedRoles.includes(user.rol)) {
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}
