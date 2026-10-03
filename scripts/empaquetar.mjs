// Copyright (c) 2024 DatenJäger. All rights reserved.
// scripts/empaquetar.mjs — una orden para construir el instalador
// Trazabilidad Jira: SCRUM-54 (DatenJäger — Electron).

/**
 * Empaqueta DatenJäger de principio a fin.
 *
 * Encadena los cuatro pasos que antes había que recordar y ejecutar en orden:
 *
 *   1. los iconos que exige el instalador (PNG ≥512 e `.ico` multi-resolución),
 *   2. el backend Python congelado, para que el usuario no instale Python,
 *   3. el renderer compilado con Vite,
 *   4. electron-builder, que arma el `.exe` (NSIS) o el `.AppImage`.
 *
 * El intérprete de Python no se adivina: se reutiliza `interprete()` de
 * `electron/backend.js`, el mismo que usa la aplicación al arrancar. Si el
 * empaquetado y la ejecución discrepasen sobre qué Python usar, el instalador
 * saldría con un backend distinto del que la aplicación buscaría.
 *
 * Uso:
 *
 *   npm run dist              # instalador de esta plataforma
 *   npm run dist:linux        # AppImage
 *   npm run dist:win          # .exe de Windows (NSIS)
 *   npm run dist -- --publish always   # además lo publica en GitHub Releases
 */

import { spawnSync } from 'node:child_process'
import { createRequire } from 'node:module'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const AQUI = path.dirname(fileURLToPath(import.meta.url))
const RAIZ = path.join(AQUI, '..')

// Mismo resolutor de intérprete que la aplicación en marcha.
const require = createRequire(import.meta.url)
const { interprete } = require(path.join(RAIZ, 'electron', 'backend.js'))

const PYTHON = interprete(RAIZ)

/** Ejecuta un paso y aborta el empaquetado si falla. */
function paso(descripcion, orden, opciones = {}) {
  console.log(`\n[empaquetado] ${descripcion}`)
  console.log(`[empaquetado] $ ${orden.join(' ')}`)

  const resultado = spawnSync(orden[0], orden.slice(1), {
    cwd: RAIZ,
    stdio: 'inherit',
    shell: process.platform === 'win32',
    ...opciones,
  })

  if (resultado.error) {
    console.error(`[empaquetado] no se pudo ejecutar: ${resultado.error.message}`)
    process.exit(1)
  }
  if (resultado.status !== 0) {
    console.error(`[empaquetado] falló: ${descripcion}`)
    process.exit(resultado.status ?? 1)
  }
}

/** Argumentos de electron-builder: plataforma y publicación. */
function argumentosDelConstructor(extra) {
  const plataformas = { linux: '--linux', win32: '--win', darwin: '--mac' }
  const pedidas = extra.filter((a) => ['--linux', '--win', '--mac'].includes(a))

  const orden = [
    'npx',
    '--no-install',
    'electron-builder',
    ...(pedidas.length ? pedidas : [plataformas[process.platform]].filter(Boolean)),
  ]

  // Sin `--publish always` explícito no se publica nada: construir y publicar
  // son cosas distintas, y publicar por accidente desde un portátil es peor
  // que no publicar.
  const publica = extra.includes('always')
  orden.push('--publish', publica ? 'always' : 'never')

  return orden
}

const extra = process.argv.slice(2)
const paquete = JSON.parse(readFileSync(path.join(RAIZ, 'package.json'), 'utf8'))

console.log(`[empaquetado] DatenJäger ${paquete.version}`)
console.log(`[empaquetado] intérprete de Python: ${PYTHON}`)

paso('preparando los iconos del instalador', [PYTHON, 'scripts/preparar_recursos.py'])
paso('congelando el backend Python', [PYTHON, 'scripts/empaquetar_backend.py'])

// Solo backend: útil para comprobar el congelado sin esperar al instalador.
if (extra.includes('--solo-backend')) {
  console.log('\n[empaquetado] backend congelado. Nada más que hacer (--solo-backend).')
  process.exit(0)
}

paso('compilando el renderer', ['npx', '--no-install', 'vite', 'build'])
paso('construyendo el instalador', argumentosDelConstructor(extra))

console.log(`\n[empaquetado] listo. Artefactos en release/${paquete.version}/`)