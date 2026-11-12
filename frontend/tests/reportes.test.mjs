import test from 'node:test'
import assert from 'node:assert/strict'
import {
  porcentaje, fechaCorta, fechaHora, escalaEje, indicesEtiquetas, segmentosDona, trayectoSector,
  resumenSerie, parametrosFiltros, hayFiltros, miles, BANDAS, PERIODOS,
} from '../src/utils/reportes.js'

test('porcentaje: redondea a 1 decimal y nunca devuelve NaN', () => {
  assert.equal(porcentaje(1, 3), 33.3)
  assert.equal(porcentaje(2, 3), 66.7)
  assert.equal(porcentaje(0, 0), 0)
  assert.equal(porcentaje(5, undefined), 0)
  assert.equal(porcentaje(1, 4, 0), 25)
})

test('fechaCorta usa el texto ISO sin pasar por Date (evita el desfase de zona horaria)', () => {
  assert.equal(fechaCorta('2026-11-05'), '05 nov')
  assert.equal(fechaCorta('2026-01-31'), '31 ene')
  assert.equal(fechaCorta('2026-12-01T10:00:00'), '01 dic')
  assert.equal(fechaCorta(''), '')
  assert.equal(fechaCorta(null), '')
})

test('fechaHora devuelve vacío con valores inválidos', () => {
  assert.equal(fechaHora('no es fecha'), '')
  assert.match(fechaHora('2026-11-05T08:30:00'), /^05\/11\/2026 08:30$/)
})

test('miles usa separador de miles y tolera null', () => {
  assert.equal(miles(null), '0')
  assert.equal(typeof miles(12345), 'string')
})

test('escalaEje redondea el máximo a 1, 2, 5 × 10^n y cubre el dato', () => {
  for (const [dato, max] of [[37, 40], [4, 4], [9, 10], [101, 150], [1, 1], [0.5, 0.6]]) {
    const e = escalaEje(dato)
    assert.ok(e.max >= dato, `${e.max} debe cubrir ${dato}`)
    assert.equal(e.max, max, `escala de ${dato}`)
    assert.equal(e.marcas[0], 0)
    assert.equal(e.marcas.at(-1), e.max)
  }
  assert.deepEqual(escalaEje(37).marcas, [0, 10, 20, 30, 40])
})

test('escalaEje con 0, vacío o inválido sigue dibujando ejes', () => {
  for (const v of [0, -3, NaN, undefined]) {
    const e = escalaEje(v)
    assert.equal(e.marcas.length, 5)
    assert.ok(e.max > 0)
  }
})

test('indicesEtiquetas incluye primero y último y no supera el máximo', () => {
  assert.deepEqual(indicesEtiquetas(0), [])
  assert.deepEqual(indicesEtiquetas(5), [0, 1, 2, 3, 4])
  const i = indicesEtiquetas(30, 7)
  assert.equal(i[0], 0)
  assert.equal(i.at(-1), 29)
  assert.ok(i.length <= 7)
  assert.deepEqual([...i].sort((a, b) => a - b), i)
})

test('segmentosDona reparte 360° según los conteos', () => {
  const s = segmentosDona({ bajo: 1, moderado: 1, alto: 2 })
  assert.deepEqual(s.map((x) => x.clave), ['bajo', 'moderado', 'alto'])
  assert.deepEqual(s.map((x) => x.porcentaje), [25, 25, 50])
  assert.ok(Math.abs(s[2].fin - Math.PI * 2) < 1e-9)
  assert.ok(Math.abs(s[0].fin - s[1].inicio) < 1e-9)
})

test('segmentosDona sin datos: todo en cero, sin NaN', () => {
  const s = segmentosDona({})
  assert.ok(s.every((x) => x.valor === 0 && x.porcentaje === 0 && x.inicio === 0 && x.fin === 0))
  assert.equal(trayectoSector(50, 50, 40, 25, s[0].inicio, s[0].fin), '')
})

test('trayectoSector: un sector del 100 % se divide en dos arcos y no genera NaN', () => {
  const d = trayectoSector(50, 50, 40, 25, 0, Math.PI * 2)
  assert.equal((d.match(/M/g) || []).length, 2)
  assert.ok(!d.includes('NaN'))
  const medio = trayectoSector(50, 50, 40, 25, 0, Math.PI)
  assert.match(medio, /^M50 10 A40 40 0 0 1/)
})

test('resumenSerie calcula total, promedio y pico', () => {
  const r = resumenSerie([
    { fecha: '2026-11-01', total: 2 }, { fecha: '2026-11-02', total: 7 }, { fecha: '2026-11-03', total: 0 },
  ])
  assert.deepEqual(r, { total: 9, promedioDiario: 3, pico: { fecha: '2026-11-02', total: 7 } })
  assert.deepEqual(resumenSerie([]), { total: 0, promedioDiario: 0, pico: null })
  assert.equal(resumenSerie([{ fecha: '2026-11-01', total: 0 }]).pico, null)
})

test('parametrosFiltros descarta vacíos pero conserva el 0 y false', () => {
  assert.deepEqual(parametrosFiltros({ q: '', desde: '2026-11-01', clasificacion: null, offset: 0 }), { desde: '2026-11-01', offset: 0 })
  assert.equal(hayFiltros({ q: '', desde: '' }), false)
  assert.equal(hayFiltros({ q: 'juan' }), true)
})

test('catálogos del módulo: tres bandas y tres periodos', () => {
  assert.deepEqual(BANDAS.map((b) => b.clave), ['bajo', 'moderado', 'alto'])
  assert.deepEqual(PERIODOS.map((p) => p.dias), [7, 30, 90])
})
