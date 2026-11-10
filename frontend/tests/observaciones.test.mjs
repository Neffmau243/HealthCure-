import test from 'node:test'
import assert from 'node:assert/strict'
import {construirObservaciones, hayAlerta} from '../src/utils/observaciones.js'
import {construirPayloadEvaluacion} from '../src/utils/triaje.js'

test('el formulario ya envía y conserva todos los signos de un caso crítico',()=>{
  const form={presionArterial:'80/50',frecuenciaCardiaca:'160',saturacion:'75',temperatura:'40',frecuencia_respiratoria:'30',peso:'70',altura:'170',sintomas:['dolor_toracico'],sintomas_revisados:true,diabetes:'0'}
  const p=construirPayloadEvaluacion({id:1},form,30)
  assert.equal(p.presion_alta,false)
  assert.equal(p.observaciones_clinicas.presion_sistolica,80)
  assert.equal(p.observaciones_clinicas.saturacion_o2,'75')
  assert.equal(p.observaciones_clinicas.frecuencia_cardiaca,'160')
  assert.equal(p.observaciones_clinicas.temperatura_c,'40')
  assert.equal(p.observaciones_clinicas.peso_kg,'70')
  assert.deepEqual(p.observaciones_clinicas.sintomas,['dolor_toracico'])
})
test('faltante, cero y síntomas confirmados son estados distintos',()=>{
  assert.equal(construirObservaciones({}).frecuencia_cardiaca,null)
  assert.equal(construirObservaciones({frecuenciaCardiaca:0}).frecuencia_cardiaca,0)
  assert.equal(construirObservaciones({}).sintomas,null)
  assert.deepEqual(construirObservaciones({sintomas_revisados:true}).sintomas,[])
  assert.deepEqual(construirObservaciones({sintomas:['convulsiones'],sintomas_revisados:false}).sintomas,['convulsiones'])
})
test('presión inválida se envía a validación, no se sustituye por signos normales',()=>{
  assert.equal(construirObservaciones({presionArterial:'no válida'}).presion_sistolica,'formato inválido')
  assert.equal(construirObservaciones({presionArterial:''}).presion_sistolica,null)
  assert.equal(hayAlerta({nivel:'inmediata'}),true)
  assert.equal(hayAlerta({nivel:'datos_insuficientes'}),false)
})
