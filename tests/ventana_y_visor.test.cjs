const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')

const raiz = path.join(__dirname, '..')
const leer = (archivo) => fs.readFileSync(path.join(raiz, archivo), 'utf8')

test('el visor se monta en la raíz y no queda recortado por el panel animado', () => {
  const visor = leer('src/components/VisorPdf.jsx')
  assert.match(visor, /createPortal\(/)
  assert.match(visor, /document\.body\s*,/)
  assert.match(visor, /flex-1 w-full border-0/)
  assert.match(visor, /URL\.revokeObjectURL\(creada\)/)
})

test('la ventana sin marco expone solo controles acotados al renderer', () => {
  const main = leer('electron/main.js')
  const preload = leer('electron/preload.js')
  assert.match(main, /frame:\s*false/)
  for (const accion of ['minimizar', 'maximizar', 'cerrar']) {
    assert.match(main, new RegExp(`ventana:${accion}`))
    assert.match(preload, new RegExp(`ventana:${accion}`))
  }
  assert.match(main, /BrowserWindow\.fromWebContents\(evento\.sender\)/)
  assert.match(main, /frame-src blob:/)
})

test('la barra global tiene zonas de arrastre y controles accesibles', () => {
  const app = leer('src/App.jsx')
  const barra = leer('src/components/BarraVentana.jsx')
  assert.match(app, /<BarraVentana/)
  assert.match(barra, /region-arrastrable/)
  assert.match(barra, /region-no-arrastrable/)
  for (const accion of ['Minimizar', 'Maximizar', 'Cerrar']) {
    assert.match(barra, new RegExp(accion))
  }
  const css = leer('src/index.css')
  assert.match(css, /-webkit-app-region: drag/)
  assert.match(css, /-webkit-app-region: no-drag/)
})
