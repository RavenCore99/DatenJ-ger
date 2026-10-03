import { useEffect, useRef, useState } from 'react'

import Icono from './Icono.jsx'
import { animar } from '../lib/movimiento.js'
import { elegirArchivo } from '../lib/escritorio.js'
import { tamanoLegible } from '../lib/formato.js'
import { useCerrarConEscape } from '../lib/modal.js'

/**
 * Formulario de alta de documento (calidad de vida).
 *
 * Antes, «Agregar documento» abría directamente el selector de archivos y
 * guardaba el PDF con su nombre y nada más: los metadatos —descripción,
 * titular, empresa— solo se podían rellenar después, entrando al detalle del
 * expediente. Ahora el botón abre este formulario, se elige el PDF aquí mismo y
 * **todo se guarda en el mismo acto**: el backend recibe los metadatos junto con
 * el archivo y crea o asocia la persona en la misma transacción.
 *
 * La empresa se ofrece como lista de las ya conocidas, para no sembrar
 * duplicados con variantes de escritura; aun así se puede escribir una nueva.
 */
export default function AltaDocumento({ empresas = [], ocupado, error, onGuardar, onCerrar }) {
  const panel = useRef(null)
  // Cerrar con Escape y llevar el foco al botón de cierre, sin robar el foco en
  // cada pulsación (ver `src/lib/modal.js`).
  const cerrar = useCerrarConEscape(onCerrar)

  const [archivo, setArchivo] = useState(null)
  const [campos, setCampos] = useState({
    nombre: '',
    descripcion: '',
    cedula: '',
    nombres: '',
    empresa: '',
  })
  const [errorLocal, setErrorLocal] = useState(null)
  const fallo = error ?? errorLocal

  useEffect(() => {
    animar(panel.current, {
      opacity: [0, 1],
      translateY: [14, 0],
      scale: [0.985, 1],
      duration: 240,
      ease: 'outQuad',
    })
  }, [])

  const cambiar = (campo) => (evento) =>
    setCampos((actual) => ({ ...actual, [campo]: evento.target.value }))

  const elegir = async () => {
    const elegido = await elegirArchivo()
    if (!elegido || elegido.cancelado) return
    if (elegido.error) {
      setErrorLocal(elegido.error)
      return
    }

    setErrorLocal(null)
    setArchivo(elegido)
    // El nombre del archivo propone el nombre del documento, pero se puede
    // cambiar: el nombre del expediente no tiene por qué ser el del PDF.
    setCampos((actual) => ({
      ...actual,
      nombre: actual.nombre || elegido.nombre.replace(/\.pdf$/i, ''),
    }))
  }

  const enviar = (evento) => {
    evento.preventDefault()
    if (!archivo) {
      setErrorLocal('Elige el PDF antes de guardar.')
      return
    }
    if (Boolean(campos.cedula) !== Boolean(campos.nombres)) {
      setErrorLocal('La cédula y los nombres del titular van juntos, o ninguno de los dos.')
      return
    }

    onGuardar({
      nombre: campos.nombre.trim(),
      contenido_b64: archivo.contenido_b64,
      descripcion: campos.descripcion.trim() || null,
      cedula: campos.cedula.trim() || null,
      nombres: campos.nombres.trim() || null,
      empresa: campos.empresa.trim() || null,
    })
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="alta-documento-titulo"
      className="fixed inset-0 z-50 flex items-center justify-center p-6"
    >
      <button
        type="button"
        aria-label="Cerrar el formulario"
        onClick={onCerrar}
        className="absolute inset-0 cursor-default bg-texto/40 backdrop-blur-sm"
      />

      <div
        ref={panel}
        className="superficie-cristal relative flex max-h-[86vh] w-full max-w-2xl flex-col overflow-hidden rounded-panel border border-borde shadow-flotante"
      >
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-borde px-6 py-4">
          <div className="min-w-0">
            <h2 id="alta-documento-titulo" className="font-marca text-titulo-sm tracking-tight">
              Registrar documento
            </h2>
            <p className="text-cuerpo-sm text-tenue">
              El PDF se cifra antes de guardarse; el original no se conserva
            </p>
          </div>

          <button
            ref={cerrar}
            type="button"
            onClick={onCerrar}
            aria-label="Cerrar"
            className="shrink-0 rounded px-1.5 text-tenue transition-colors hover:text-texto"
          >
            <Icono nombre="cerrar" tamano={16} />
          </button>
        </header>

        <form className="flex min-h-0 flex-1 flex-col" onSubmit={enviar}>
          <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
            <div className="flex flex-col gap-5">
              <section className="flex flex-col gap-2">
                <h3 className="text-etiqueta-sm uppercase tracking-wider text-tenue">Archivo</h3>

                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={elegir}
                    className="inline-flex items-center gap-2 rounded-lg border border-borde px-3.5 py-2 text-etiqueta-md font-medium transition-colors hover:border-primario hover:text-primario"
                  >
                    <Icono nombre="carpeta" tamano={15} />
                    {archivo ? 'Cambiar el PDF' : 'Elegir el PDF'}
                  </button>

                  {archivo ? (
                    <span className="flex min-w-0 items-center gap-2 text-cuerpo-sm">
                      <Icono nombre="check" tamano={14} className="text-exito" />
                      <span className="truncate font-mono" title={archivo.nombre}>
                        {archivo.nombre}
                      </span>
                    </span>
                  ) : (
                    <span className="text-cuerpo-sm text-tenue">Todavía no has elegido ninguno</span>
                  )}
                </div>
              </section>

              <section className="flex flex-col gap-4 border-t border-borde pt-5">
                <h3 className="text-etiqueta-sm uppercase tracking-wider text-tenue">
                  Datos del documento
                </h3>

                <Campo
                  etiqueta="Nombre"
                  valor={campos.nombre}
                  onCambio={cambiar('nombre')}
                  obligatorio
                  ayuda="Como aparecerá en el inventario"
                />

                <label className="flex flex-col gap-1">
                  <span className="text-etiqueta-sm text-texto">Descripción</span>
                  <textarea
                    value={campos.descripcion}
                    onChange={cambiar('descripcion')}
                    rows={2}
                    placeholder="De qué trata el documento"
                    className="resize-y rounded-lg border border-borde bg-fondo px-3 py-2 text-cuerpo-md outline-none transition-colors focus:border-primario"
                  />
                </label>
              </section>

              <section className="flex flex-col gap-4 border-t border-borde pt-5">
                <div>
                  <h3 className="text-etiqueta-sm uppercase tracking-wider text-tenue">
                    Titular y empresa
                  </h3>
                  <p className="mt-1 text-cuerpo-sm text-tenue">
                    Opcional, pero si lo rellenas el documento queda asociado a la persona y a su
                    empresa en el mismo paso.
                  </p>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <Campo
                    etiqueta="Cédula"
                    valor={campos.cedula}
                    onCambio={cambiar('cedula')}
                    mono
                  />
                  <Campo
                    etiqueta="Nombres"
                    valor={campos.nombres}
                    onCambio={cambiar('nombres')}
                  />
                </div>

                <label className="flex flex-col gap-1">
                  <span className="text-etiqueta-sm text-texto">Empresa</span>
                  <input
                    type="text"
                    list="empresas-conocidas"
                    value={campos.empresa}
                    onChange={cambiar('empresa')}
                    placeholder="Escribe una nueva o elige una de la lista"
                    className="rounded-lg border border-borde bg-fondo px-3 py-2 text-cuerpo-md outline-none transition-colors focus:border-primario"
                  />
                  <datalist id="empresas-conocidas">
                    {empresas.map((nombre) => (
                      <option key={nombre} value={nombre} />
                    ))}
                  </datalist>
                  <span className="text-cuerpo-sm text-tenue">
                    Se ofrecen las empresas que ya existen para no duplicarlas con otra escritura.
                  </span>
                </label>
              </section>

              {fallo && (
                <p role="alert" className="rounded-lg border border-peligro/40 bg-peligro/5 px-3 py-2 text-cuerpo-sm text-peligro">
                  {fallo}
                </p>
              )}
            </div>
          </div>

          {/* Pie del formulario: aquí vivía el rótulo «sin archivo». El botón
              abre el mismo selector que la sección Archivo y alimenta
              `contenido_b64` del alta. */}
          <footer className="flex shrink-0 items-center justify-between gap-4 border-t border-borde px-6 py-3">
            <span className="flex min-w-0 items-center gap-3">
              <button
                type="button"
                onClick={elegir}
                className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-borde px-3.5 py-2 text-etiqueta-md font-medium transition-colors hover:border-primario hover:text-primario"
              >
                <Icono nombre="carpeta" tamano={15} />
                {archivo ? 'Cambiar PDF' : 'Cargar PDF'}
              </button>
              {archivo ? (
                <span
                  className="min-w-0 truncate font-mono text-telemetria text-tenue"
                  title={archivo.nombre}
                >
                  {archivo.nombre} · {tamanoLegible(archivo.tamano)}
                </span>
              ) : (
                <span className="font-mono text-telemetria text-tenue">sin archivo</span>
              )}
            </span>

            <span className="flex shrink-0 items-center gap-3">
              <button
                type="button"
                onClick={onCerrar}
                className="rounded-lg border border-borde px-3.5 py-2 text-etiqueta-md font-medium transition-colors hover:border-primario hover:text-primario"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={ocupado || !archivo || !campos.nombre.trim()}
                className="inline-flex items-center gap-2 rounded-lg bg-primario px-3.5 py-2 text-etiqueta-md font-medium text-sobre-primario transition-colors hover:bg-primario-enfasis disabled:opacity-50"
              >
                <Icono nombre="guardar" tamano={14} />
                {ocupado ? 'Cifrando y guardando…' : 'Guardar documento'}
              </button>
            </span>
          </footer>
        </form>
      </div>
    </div>
  )
}

function Campo({ etiqueta, valor, onCambio, obligatorio = false, mono = false, ayuda }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-etiqueta-sm text-texto">{etiqueta}</span>
      <input
        type="text"
        value={valor}
        onChange={onCambio}
        required={obligatorio}
        className={[
          'rounded-lg border border-borde bg-fondo px-3 py-2 text-cuerpo-md outline-none transition-colors focus:border-primario',
          mono ? 'font-mono' : '',
        ].join(' ')}
      />
      {ayuda && <span className="text-cuerpo-sm text-tenue">{ayuda}</span>}
    </label>
  )
}