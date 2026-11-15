export const TIPOS_ATENCION = { ambulatoria: 'Ambulatoria', emergencia: 'Emergencia' }
export const GRUPOS_ETARIOS = {
  nino: 'Niño/a', adulto: 'Adulto/a', adulto_mayor: 'Adulto/a mayor',
}
export const CONDICIONES_MATERNAS = { ninguna: 'Ninguna', gestante: 'Gestante', puerpera: 'Puérpera' }

export const grupoPorEdad = (edad) => {
  if (edad == null || !Number.isFinite(edad) || edad < 0) return null
  if (edad < 18) return 'nino'
  return edad < 60 ? 'adulto' : 'adulto_mayor'
}

// Los historiales usan exclusivamente la instantánea recibida del backend.
export const etiquetaGrupo = (grupo) => GRUPOS_ETARIOS[grupo] ?? 'No registrado'
