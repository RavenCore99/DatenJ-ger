import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/** Versión del proyecto y hash del commit, para la franja de telemetría. */
function selloDeBuild() {
  const paquete = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8'))

  let hash = 'sin-git'
  try {
    // `execFileSync` con argumentos sueltos: no pasa por el shell, así que no
    // hay forma de que un valor se interprete como comando.
    hash = execFileSync('git', ['rev-parse', '--short', 'HEAD'], {
      stdio: ['ignore', 'pipe', 'ignore'],
    })
      .toString()
      .trim()
  } catch {
    // La aplicación empaquetada puede no tener git al lado: no es un error.
  }

  return { version: paquete.version ?? '0.0.0', hash }
}

const sello = selloDeBuild()

/**
 * Configuración de Vite para DatenJäger.
 *
 * `base: './'` es obligatorio: en producción Electron carga `dist/index.html`
 * con el protocolo `file://`, y con rutas absolutas (`/assets/...`) el
 * renderer no encontraría los archivos.
 */
export default defineConfig({
  base: './',
  plugins: [react()],
  // El `.env` del proyecto es del backend Python, no de Vite: la aplicación no
  // lee `import.meta.env` para nada que venga de ahí (el puerto se resuelve por
  // el puente de Electron). Sin esto, **Vite reinicia su servidor cada vez que
  // cambia el `.env`**, y el panel de modelos lo escribe al guardar la
  // credencial: el servidor se reiniciaba, el renderer recargaba y el usuario
  // aparecía en la pantalla de acceso con la sesión perdida.
  envDir: false,
  define: {
    __VERSION__: JSON.stringify(sello.version),
    __HASH__: JSON.stringify(sello.hash),
  },
  server: {
    host: '127.0.0.1',
    port: 5273,
    strictPort: true,
    // Los archivos que la aplicación **escribe mientras funciona** no son
    // código: no deben provocar recargas. Son el almacén de la conexión de
    // modelos, los tokens de confianza y la base de datos.
    watch: {
      ignored: [
        '**/modelos/**',
        '**/tokens_confianza/**',
        '**/*.db',
        '**/*.db-wal',
        '**/*.db-shm',
        '**/base_datos_pdfs.db*',
      ],
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true,
  },
})