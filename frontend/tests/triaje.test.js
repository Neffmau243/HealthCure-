import test from 'node:test';
import assert from 'node:assert/strict';
import { construirPayloadEvaluacion, diabetesFormulario, etiquetaDiabetes, edadACategoria, calcularEdad, resumenPolitica } from '../src/utils/triaje.js';

const datos = { hipertensionPrevia: false, presionArterial: '160/95', diabetes: '1', saludGeneral: '3' };

test('una lectura elevada se conserva sin inventar hipertensión previa', () => {
  const payload = construirPayloadEvaluacion({ id: 1 }, datos, 55);
  assert.equal(payload.presion_alta, false);
  assert.equal(payload.presion_sistolica, 160);
  assert.equal(payload.presion_diastolica, 95);
  assert.equal(payload.estado_diabetes, 'prediabetes');
  assert.equal(payload.diabetes, true);
});

test('la recarga conserva prediabetes y no adivina el subtipo histórico', () => {
  assert.equal(diabetesFormulario({ diabetes: true, estado_diabetes: 'prediabetes' }), '1');
  assert.equal(diabetesFormulario({ diabetes: true, estado_diabetes: null }), '');
  assert.match(etiquetaDiabetes({ diabetes: true }), /sin detalle/);
  assert.throws(() => construirPayloadEvaluacion({ id: 1 }, { ...datos, diabetes: '' }, 55));
});

test('sin lectura no se inventan valores; lecturas inválidas se rechazan', () => {
  assert.equal(construirPayloadEvaluacion({ id: 1 }, { ...datos, presionArterial: '' }, 55).presion_sistolica, null);
  assert.throws(() => construirPayloadEvaluacion({ id: 1 }, { ...datos, presionArterial: '80/120' }, 55));
  assert.equal(edadACategoria(17), null);
  assert.equal(edadACategoria(18), 1);
});

test('la edad cambia al cumpleaños en Lima, independientemente del huso del navegador', () => {
  assert.equal(calcularEdad('2008-10-15', new Date('2026-10-15T04:59:00Z')), 17);
  assert.equal(calcularEdad('2008-10-15', new Date('2026-10-15T05:00:00Z')), 18);
  assert.equal(calcularEdad('2008-02-30'), null);
  assert.equal(edadACategoria(121), null);
});


test('cada evaluación muestra sus propios cortes e identifica históricos', () => {
  assert.match(resumenPolitica({}), /Histórico.*sin calibrar/);
  const result = resumenPolitica({ politica_modelo: {
    reglas_version: 'bandas-academicas-3.0.0', umbrales: { bajo_max: .051065, moderado_max: .210469 },
  } });
  assert.match(result, /5.1065/);
  assert.match(result, /21.0469/);
  assert.match(result, /bandas-academicas-3.0.0/);
});
