export const TIPOS_ATENCION = { ambulatoria: 'Ambulatoria', referencia: 'Referencia', emergencia: 'Emergencia' }
export const LUGARES_ATENCION = { intramural: 'Intramural', extramural: 'Extramural' }
export const GRUPOS_ETARIOS = {
  nino: 'Niño/a', adulto: 'Adulto/a', adulto_mayor: 'Adulto/a mayor',
}
export const CONDICIONES_MATERNAS = { ninguna: 'Ninguna', gestante: 'Gestante', puerpera: 'Puérpera' }

export const CAMPOS_MATERNOS = {
  gestante: [
    ['fecha_probable_parto', 'Fecha probable de parto', 'date'],
    ['edad_gestacional_semanas', 'Edad gestacional (semanas)', 'number'],
    ['numero_control_prenatal', 'Número de control prenatal', 'number'],
    ['altura_uterina_cm', 'Altura uterina (cm)', 'number'],
  ],
  puerpera: [
    ['fecha_parto', 'Fecha de parto', 'date'],
    ['numero_control_puerperal', 'Número de control puerperal', 'number'],
  ],
}

export const contextoPaciente = (paciente) => ({
  condicion_materna: paciente?.contexto_atencion?.condicion_materna ?? 'ninguna',
  datos_maternos: { ...(paciente?.contexto_atencion?.datos_maternos ?? {}) },
})

// Envía solo los campos visibles para evitar conservar datos de otra categoría.
export const datosMaternos = (form) => {
  const datos = Object.fromEntries((CAMPOS_MATERNOS[form.condicion_materna] ?? [])
    .map(([campo]) => [campo, form.datos_maternos?.[campo]])
    .filter(([, valor]) => valor !== '' && valor != null))
  return Object.keys(datos).length ? datos : null
}

export const etiquetaCategoria = (condicion, grupo) =>
  condicion === 'gestante' || condicion === 'puerpera' ? CONDICIONES_MATERNAS[condicion] : `General · ${etiquetaGrupo(grupo)}`

export const evaluacionDeHoy = (evaluacion, hoy = new Date()) =>
  Boolean(evaluacion?.created_at && new Date(evaluacion.created_at).toDateString() === hoy.toDateString())

export const grupoPorEdad = (edad) => {
  if (edad == null || !Number.isFinite(edad) || edad < 0) return null
  if (edad < 18) return 'nino'
  return edad < 60 ? 'adulto' : 'adulto_mayor'
}

// Los historiales usan exclusivamente la instantánea recibida del backend.
export const etiquetaGrupo = (grupo) => GRUPOS_ETARIOS[grupo] ?? 'No registrado'
