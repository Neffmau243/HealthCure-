import test from 'node:test'
import assert from 'node:assert/strict'
import { grupoPorEdad, etiquetaGrupo, contextoPaciente, datosMaternos, etiquetaCategoria, evaluacionDeHoy, TIPOS_ATENCION, LUGARES_ATENCION, CONDICIONES_MATERNAS } from '../src/utils/clinica.js'
import { construirPayloadEvaluacion } from '../src/utils/triaje.js'

test('grupos solicitados: niño 0–17, adulto 18–59 y mayor 60+', () => {
  for (const [edad, grupo] of [[0, 'nino'], [17, 'nino'], [18, 'adulto'], [59, 'adulto'], [60, 'adulto_mayor'], [90, 'adulto_mayor']]) {
    assert.equal(grupoPorEdad(edad), grupo)
  }
  for (const edad of [null, undefined, NaN, -1]) assert.equal(grupoPorEdad(edad), null)
})

test('general es el valor inicial y la categoría materna conserva el grupo por edad', () => {
  assert.deepEqual(contextoPaciente({}), { condicion_materna: 'ninguna', datos_maternos: {} })
  assert.equal(etiquetaCategoria('ninguna', 'adulto'), 'General · Adulto/a')
  assert.equal(etiquetaCategoria('gestante', 'adulto'), 'Gestante')
  const paciente = { contexto_atencion: { condicion_materna: 'gestante', datos_maternos: { numero_control_prenatal: 2 } } }
  const formulario = contextoPaciente(paciente)
  formulario.datos_maternos.numero_control_prenatal = 3
  assert.equal(paciente.contexto_atencion.datos_maternos.numero_control_prenatal, 2)
})

test('cambiar categoría elimina campos ocultos del envío y distingue vacío de cero', () => {
  const datos = { fecha_probable_parto: '2027-01-01', fecha_parto: '2026-11-01', numero_control_prenatal: 2, numero_control_puerperal: '' }
  assert.deepEqual(datosMaternos({ condicion_materna: 'gestante', datos_maternos: datos }), { fecha_probable_parto: '2027-01-01', numero_control_prenatal: 2 })
  assert.deepEqual(datosMaternos({ condicion_materna: 'puerpera', datos_maternos: datos }), { fecha_parto: '2026-11-01' })
  assert.equal(datosMaternos({ condicion_materna: 'ninguna', datos_maternos: datos }), null)
  assert.deepEqual(datosMaternos({ condicion_materna: 'gestante', datos_maternos: { edad_gestacional_semanas: 0 } }), { edad_gestacional_semanas: 0 })
})

test('los datos del FUA viajan en observaciones y no reemplazan las variables del ML', () => {
  const p = construirPayloadEvaluacion({ id: 1 }, { condicion_materna: 'gestante', datos_maternos: { numero_control_prenatal: 3 } }, 20)
  assert.equal(p.edad, 20)
  assert.equal(p.observaciones_clinicas.condicion_materna, 'gestante')
  assert.equal(p.observaciones_clinicas.datos_maternos.numero_control_prenatal, 3)
  assert.equal(p.datos_maternos, undefined)
})

test('solo las evaluaciones de la misma fecha permiten reutilizar sus mediciones', () => {
  const hoy = new Date('2026-11-13T10:00:00')
  assert.equal(evaluacionDeHoy({ created_at: '2026-11-13T08:00:00' }, hoy), true)
  assert.equal(evaluacionDeHoy({ created_at: '2026-11-12T23:59:00' }, hoy), false)
  assert.equal(evaluacionDeHoy(null, hoy), false)
})

test('el historial conserva la ausencia de contexto de visitas antiguas', () => {
  assert.equal(etiquetaGrupo(null), 'No registrado')
  assert.equal(etiquetaGrupo('adulto'), 'Adulto/a')
  assert.deepEqual(Object.keys(TIPOS_ATENCION), ['ambulatoria', 'referencia', 'emergencia'])
  assert.deepEqual(Object.keys(LUGARES_ATENCION), ['intramural', 'extramural'])
  assert.deepEqual(Object.keys(CONDICIONES_MATERNAS), ['ninguna', 'gestante', 'puerpera'])
})
