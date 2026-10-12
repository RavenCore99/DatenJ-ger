import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'

import { useCerrarConEscape } from '../lib/modal.js'

/** Confirmación de sesión compartida por la barra y Ctrl+Q. */
export default function ConfirmarCierreSesion({ onCancelar, onConfirmar }) {
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState('')
  const cancelar = useCerrarConEscape(() => {
    if (!ocupado) onCancelar()
  })

  useEffect(() => {
    const anterior = document.activeElement
    return () => anterior?.focus?.()
  }, [])

  const confirmar = async () => {
    if (ocupado) return
    setOcupado(true)
    setError('')
    try {
      await onConfirmar()
    } catch (fallo) {
      setError(fallo.message || 'No se pudo cerrar la sesión. Reintenta.')
    } finally {
      setOcupado(false)
    }
  }

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="cierre-sesion-titulo"
      aria-describedby="cierre-sesion-descripcion"
      className="fixed inset-0 z-[60] flex items-center justify-center p-5 text-texto"
    >
      <button
        type="button"
        tabIndex={-1}
        aria-label="Cancelar cierre de sesión"
        onClick={onCancelar}
        className="absolute inset-0 cursor-default bg-texto/40 backdrop-blur-sm"
      />
      <section className="superficie-cristal relative w-full max-w-sm rounded-panel border border-borde p-6 shadow-flotante">
        <h2 id="cierre-sesion-titulo" className="font-marca text-titulo-sm text-primario">
          Cerrar sesión
        </h2>
        <p id="cierre-sesion-descripcion" className="mt-2 text-cuerpo-sm text-texto-2">
          ¿Cerrar la sesión abierta? Puedes volver a entrar con tus credenciales.
        </p>
        {error && <p role="alert" className="mt-3 text-cuerpo-sm text-peligro">{error}</p>}
        <div className="mt-6 flex justify-end gap-2">
          <button
            ref={cancelar}
            type="button"
            disabled={ocupado}
            onClick={onCancelar}
            className="rounded-lg border border-borde bg-superficie px-4 py-2 text-etiqueta-md text-texto transition-colors hover:bg-fondo-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario"
          >
            Cancelar
          </button>
          <button
            type="button"
            disabled={ocupado}
            onClick={confirmar}
            className="rounded-lg bg-primario px-4 py-2 text-etiqueta-md font-medium text-sobre-primario transition-colors hover:bg-primario-enfasis disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario"
          >
            {ocupado ? 'Cerrando…' : 'Cerrar sesión'}
          </button>
        </div>
      </section>
    </div>,
    document.body,
  )
}
