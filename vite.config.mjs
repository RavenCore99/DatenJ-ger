import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

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
  server: {
    host: '127.0.0.1',
    port: 5273,
    strictPort: true,
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true,
  },
})