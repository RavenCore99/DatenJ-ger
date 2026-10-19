const { test } = require('node:test')
const assert = require('node:assert/strict')
const { ServicioPython } = require('../electron/backend')

test('el backend acepta un token que empieza por guion', () => {
  const servicio = new ServicioPython({
    raiz: __dirname,
    datos: __dirname,
    binario: 'python3',
    dbPath: null,
  })
  servicio.token = '-token-de-prueba'
  const orden = servicio.ordenDeArranque(8756)
  assert.ok(orden.includes('--token=-token-de-prueba'))
  assert.equal(orden.includes('--token'), false)
  assert.equal(orden.includes('-token-de-prueba'), false)
})
