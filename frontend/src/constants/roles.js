// Roles reales del backend (app/models/usuario.py → Enum('admin', 'usuario')).
// No existen medico/enfermero en la API: ambos son "usuario".
export const ROLES = {
  ADMIN: 'admin',
  USUARIO: 'usuario',
}

// Matriz de permisos por ruta y rol.
// Todo el personal de salud (usuario) ve lo clínico;
// solo el admin ve la gestión de usuarios.
export const PERMISSIONS = {
  '/dashboard': [ROLES.ADMIN, ROLES.USUARIO],
  '/dashboard/pacientes': [ROLES.ADMIN, ROLES.USUARIO],
  '/dashboard/triaje': [ROLES.ADMIN, ROLES.USUARIO],
  '/dashboard/historiales': [ROLES.ADMIN, ROLES.USUARIO],
  '/dashboard/consultorio': [ROLES.ADMIN, ROLES.USUARIO],
  '/dashboard/atenciones': [ROLES.ADMIN, ROLES.USUARIO],
  '/dashboard/usuarios': [ROLES.ADMIN],
}

/** ¿El rol puede ver esta ruta? Rutas sin entrada en PERMISSIONS se permiten. */
export const puedeVer = (path, rol) => {
  const permitidos = PERMISSIONS[path]
  return !permitidos || permitidos.includes(rol)
}

/** Nombre legible del rol para mostrar en la interfaz. */
export const etiquetaRol = (rol) =>
  rol === ROLES.ADMIN ? 'Administrador' : 'Personal de salud'
