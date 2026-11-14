import test from 'node:test'
import assert from 'node:assert/strict'
import {construirObservaciones, hayAlerta} from '../src/utils/observaciones.js'
import {construirPayloadEvaluacion} from '../src/utils/triaje.js'

test('las mediciones administrativas del FUA se guardan sin afirmar revisión de síntomas', () => {
  const payload = construirPayloadEvaluacion({id:1}, {peso_kg:'68',talla_cm:'162',presionArterial:'120/80',diabetes:'0'}, 20)
  assert.equal(payload.observaciones_clinicas.peso_kg, '68')
  assert.equal(payload.observaciones_clinicas.talla_cm, '162')
  assert.equal(payload.observaciones_clinicas.presion_sistolica, 120)
  assert.equal(payload.observaciones_clinicas.sintomas, null)
  assert.equal(payload.observaciones_clinicas.temperatura_c, null)
  const administrativos = construirObservaciones({ tipo_atencion: 'referencia', lugar_atencion: 'extramural' })
  assert.equal(administrativos.tipo_atencion, 'referencia')
  assert.equal(administrativos.lugar_atencion, 'extramural')
  assert.equal(construirObservaciones({}).tipo_atencion, null)
  assert.equal(construirObservaciones({}).lugar_atencion, null)
})

test('el payload envía las nueve variables que espera el modelo',()=>{
  const p=construirPayloadEvaluacion({id:1},{
    presionArterial:'150/95',hipertensionPrevia:false,colesterolAlto:true,fuma:true,
    actividadFisica:false,derrame:true,diabetes:'1',saludGeneral:'5',dificultadCaminar:true,
  },64)
  const esperado={paciente_id:1,edad:64,presion_alta:true,colesterol_alto:true,tabaquismo:true,
    actividad_fisica:false,antecedente_acv:true,diabetes:true,salud_general:5,dificultad_para_caminar:true}
  for(const [campo,valor] of Object.entries(esperado)) assert.equal(p[campo],valor,campo)
  assert.equal(Object.keys(p).length,Object.keys(esperado).length+1) // + observaciones_clinicas
})

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
