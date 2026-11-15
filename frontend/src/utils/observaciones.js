import { parsePresion } from './presion.js'

export const SINTOMAS_ALARMA = {
  dolor_toracico: 'Dolor torácico actual',
  dificultad_respiratoria: 'Dificultad respiratoria actual en reposo',
  alteracion_conciencia: 'Confusión nueva, desmayo o alteración de conciencia',
  convulsiones: 'Convulsiones actuales o recientes sin recuperación completa',
  deficit_neurologico: 'Debilidad súbita, dificultad para hablar o asimetría facial',
  sangrado_abundante: 'Sangrado abundante actual',
  cefalea_intensa: 'Cefalea intensa nueva o persistente',
  alteraciones_visuales: 'Alteraciones visuales nuevas',
  dolor_abdominal_intenso: 'Dolor abdominal intenso persistente',
  movimientos_fetales_disminuidos: 'Disminución de movimientos fetales referida',
  incapacidad_beber: 'Incapacidad para beber o alimentarse',
}
export const CAMPOS_SIGNOS = [
  ['presion_sistolica', 'Presión sistólica (mmHg)', 1, 350, '1'],
  ['presion_diastolica', 'Presión diastólica (mmHg)', 1, 250, '1'],
  ['frecuencia_cardiaca', 'Frecuencia cardíaca (lpm)', 0, 300, '1'],
  ['frecuencia_respiratoria', 'Frecuencia respiratoria (rpm)', 0, 100, '1'],
  ['saturacion_o2', 'Saturación de oxígeno (%)', 0, 100, '0.1'],
  ['temperatura_c', 'Temperatura (°C)', 25, 45, '0.1'],
  ['peso_kg', 'Peso (kg)', 0.1, 500, '0.1'],
  ['talla_cm', 'Talla (cm)', 0.1, 300, '0.1'],
]
const dato = (v) => v === '' || v == null ? null : v

export function construirObservaciones(form, condicionMaterna) {
  const obs = Object.fromEntries(CAMPOS_SIGNOS.map(([campo]) => [campo, dato(form[campo])]))
  if (form.presionArterial != null) {
    const p = parsePresion(form.presionArterial)
    const invalida = form.presionArterial.trim() !== '' && !p
    obs.presion_sistolica = invalida ? 'formato inválido' : p?.sistolica ?? null
    obs.presion_diastolica = invalida ? 'formato inválido' : p?.diastolica ?? null
  }
  for (const [campo, alias] of Object.entries({frecuencia_cardiaca:'frecuenciaCardiaca', temperatura_c:'temperatura', saturacion_o2:'saturacion', peso_kg:'peso', talla_cm:'altura'})) {
    if (form[alias] != null) obs[campo] = dato(form[alias])
  }
  obs.sintomas = form.sintomas?.length || form.sintomas_revisados ? (form.sintomas ?? []) : null
  obs.condicion_materna = condicionMaterna || form.condicion_materna || null
  return obs
}

export function formDesdeObservaciones(obs = {}) {
  return { ...obs, sintomas: obs.sintomas ?? [], sintomas_revisados: obs.sintomas != null }
}

export const hayAlerta = (alerta) => ['inmediata', 'prioritaria'].includes(alerta?.nivel)
