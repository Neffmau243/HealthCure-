import test from 'node:test'
import assert from 'node:assert/strict'
import { grupoPorEdad, etiquetaGrupo, TIPOS_ATENCION, CONDICIONES_MATERNAS } from '../src/utils/clinica.js'

test('grupos solicitados: niño 0–17, adulto 18–59 y mayor 60+', () => {
  for (const [edad, grupo] of [[0, 'nino'], [17, 'nino'], [18, 'adulto'], [59, 'adulto'], [60, 'adulto_mayor'], [90, 'adulto_mayor']]) {
    assert.equal(grupoPorEdad(edad), grupo)
  }
  for (const edad of [null, undefined, NaN, -1]) assert.equal(grupoPorEdad(edad), null)
})

test('el historial conserva la ausencia de contexto de visitas antiguas', () => {
  assert.equal(etiquetaGrupo(null), 'No registrado')
  assert.equal(etiquetaGrupo('adulto'), 'Adulto/a')
  assert.deepEqual(Object.keys(TIPOS_ATENCION), ['ambulatoria', 'emergencia'])
  assert.deepEqual(Object.keys(CONDICIONES_MATERNAS), ['ninguna', 'gestante', 'puerpera'])
})
