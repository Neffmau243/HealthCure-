// Una sesión antigua o incompleta no debe impedir que se abra el formulario.
export function leerSesionGuardada(almacen) {
  try {
    const almacenamiento = almacen ?? localStorage
    const token = almacenamiento.getItem('token')
    const guardado = almacenamiento.getItem('user')
    if (!token || !guardado) return null

    const user = JSON.parse(guardado)
    if (
      !user ||
      !Number.isInteger(user.id) ||
      !['admin', 'usuario'].includes(user.rol)
    ) return null

    return { user, token }
  } catch {
    return null
  }
}
