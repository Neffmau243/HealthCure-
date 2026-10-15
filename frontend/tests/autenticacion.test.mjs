import test from 'node:test'
import assert from 'node:assert/strict'
import { AxiosError } from 'axios'
import { api } from '../src/services/api.js'
import { authService } from '../src/services/auth.js'
import { leerSesionGuardada } from '../src/utils/sesion.js'

const usuario = { id: 1, rol: 'admin', email: 'admin@example.com' }

function crearAlmacen(valores = {}) {
  const datos = new Map(Object.entries(valores))
  return {
    getItem: (clave) => datos.get(clave) ?? null,
    removeItem: (clave) => datos.delete(clave),
  }
}

async function conErrorHttp(estado, ejecutar) {
  const previos = new Map(['window', 'localStorage'].map((clave) => [
    clave, Object.getOwnPropertyDescriptor(globalThis, clave),
  ]))
  const adapterAnterior = api.defaults.adapter
  const almacen = crearAlmacen({ token: 'token-de-prueba', user: JSON.stringify(usuario) })
  const redirecciones = []
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: almacen })
  Object.defineProperty(globalThis, 'window', {
    configurable: true,
    value: { location: { pathname: '/', assign: (url) => redirecciones.push(url) } },
  })
  api.defaults.adapter = async (config) => {
    throw new AxiosError('Respuesta de prueba', 'ERR_BAD_REQUEST', config, {}, {
      status: estado, data: {}, headers: {}, config,
    })
  }
  try {
    await ejecutar(almacen, redirecciones)
  } finally {
    api.defaults.adapter = adapterAnterior
    for (const [clave, descriptor] of previos) {
      if (descriptor) Object.defineProperty(globalThis, clave, descriptor)
      else delete globalThis[clave]
    }
  }
}

test('un login rechazado llega al formulario sin borrar la sesión ni redirigir', async () => {
  await conErrorHttp(401, async (almacen, redirecciones) => {
    await assert.rejects(authService.login('admin@example.com', 'incorrecta'), (error) => {
      assert.equal(error.response.status, 401)
      return true
    })
    assert.equal(almacen.getItem('token'), 'token-de-prueba')
    assert.deepEqual(JSON.parse(almacen.getItem('user')), usuario)
    assert.deepEqual(redirecciones, [])
  })
})

test('un 401 de una petición protegida sigue cerrando la sesión', async () => {
  await conErrorHttp(401, async (almacen, redirecciones) => {
    await assert.rejects(api.get('/pacientes/'))
    assert.equal(almacen.getItem('token'), null)
    assert.equal(almacen.getItem('user'), null)
    assert.deepEqual(redirecciones, ['/login'])
  })
})

test('un error del servidor no cierra una sesión existente', async () => {
  await conErrorHttp(500, async (almacen, redirecciones) => {
    await assert.rejects(api.get('/pacientes/'))
    assert.equal(almacen.getItem('token'), 'token-de-prueba')
    assert.deepEqual(redirecciones, [])
  })
})

test('una sesión válida puede recuperarse después de recargar', () => {
  const almacen = crearAlmacen({ token: 'token-de-prueba', user: JSON.stringify(usuario) })
  assert.deepEqual(leerSesionGuardada(almacen), { user: usuario, token: 'token-de-prueba' })
})

test('datos de sesión dañados o incompletos permiten volver al login', () => {
  for (const user of ['undefined', '{invalido', 'null', '[]', '{}', '"texto"']) {
    assert.equal(leerSesionGuardada(crearAlmacen({ token: 'token-de-prueba', user })), null)
  }
  assert.equal(leerSesionGuardada(crearAlmacen({ user: JSON.stringify(usuario) })), null)
  assert.equal(leerSesionGuardada(crearAlmacen({ token: 'token-de-prueba' })), null)
})

test('un almacenamiento inaccesible no impide abrir el formulario', () => {
  assert.equal(leerSesionGuardada({ getItem: () => { throw new Error('No disponible') } }), null)
})
