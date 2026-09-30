/**
 * Operaciones de disco, con respaldo para el navegador de desarrollo.
 *
 * Dentro de Electron las resuelve el proceso principal con diálogos nativos.
 * En el navegador (`npm run dev:web`) se usan las alternativas del propio
 * navegador, para no tener que bifurcar las pantallas.
 */

export const enEscritorio = () => Boolean(globalThis.datenjager?.elegirArchivo)

/** Lee un PDF. Devuelve `{cancelado}` o `{nombre, tamano, contenido_b64}`. */
export async function elegirArchivo() {
  if (enEscritorio()) return globalThis.datenjager.elegirArchivo()

  return new Promise((resolver) => {
    const entrada = document.createElement('input')
    entrada.type = 'file'
    entrada.accept = 'application/pdf,.pdf'

    entrada.onchange = async () => {
      const archivo = entrada.files?.[0]
      if (!archivo) {
        resolver({ cancelado: true })
        return
      }
      resolver({
        cancelado: false,
        nombre: archivo.name,
        tamano: archivo.size,
        contenido_b64: await aBase64(archivo),
      })
    }

    // Si se cierra el diálogo sin elegir, `onchange` no se dispara.
    entrada.oncancel = () => resolver({ cancelado: true })
    entrada.click()
  })
}

/** Guarda un archivo recibido en base64. */
export async function guardarArchivo({ nombre, contenido_b64: contenidoB64 }) {
  if (enEscritorio()) return globalThis.datenjager.guardarArchivo({ nombre, contenido_b64: contenidoB64 })

  const binario = Uint8Array.from(atob(contenidoB64), (caracter) => caracter.charCodeAt(0))
  const enlace = document.createElement('a')
  enlace.href = URL.createObjectURL(new Blob([binario], { type: 'application/pdf' }))
  enlace.download = nombre
  enlace.click()
  URL.revokeObjectURL(enlace.href)

  return { cancelado: false, destino: nombre }
}

function aBase64(archivo) {
  return new Promise((resolver, rechazar) => {
    const lector = new FileReader()
    lector.onload = () => resolver(String(lector.result).split(',')[1] ?? '')
    lector.onerror = () => rechazar(new Error(`No se pudo leer ${archivo.name}`))
    lector.readAsDataURL(archivo)
  })
}