import { useEffect, useRef, useState } from 'react'

import { useApp } from '../estado/ProveedorApp.jsx'
import Icono from './Icono.jsx'

/**
 * Botón de desbloqueo con lectura biométrica (SCRUM-71).
 *
 * Portado del complemento `assets/assets/boton biometrico`: al pulsarlo se
 * reproduce una lectura del sensor —barrido y trazado de la huella— y, al
 * terminar, dispara `onCompletar`. Es un adorno de transición, no una
 * autenticación biométrica real: el sistema verifica con contraseña y TOTP, y
 * eso no cambia aquí.
 *
 * Con el movimiento desactivado, el botón actúa de inmediato, sin animación.
 */
export default function BotonBiometrico({
  children,
  onCompletar,
  desactivado = false,
  className = '',
  ...resto
}) {
  const { animaciones } = useApp()
  const [leyendo, setLeyendo] = useState(false)
  const temporizador = useRef(null)

  useEffect(() => () => clearTimeout(temporizador.current), [])

  const activar = () => {
    if (desactivado || leyendo) return

    if (!animaciones) {
      onCompletar?.()
      return
    }

    setLeyendo(true)
    temporizador.current = setTimeout(() => {
      setLeyendo(false)
      onCompletar?.()
    }, 1300)
  }

  return (
    <button
      type="button"
      onClick={activar}
      disabled={desactivado || leyendo}
      aria-busy={leyendo}
      className={[
        'relative flex items-center justify-center gap-2 overflow-hidden rounded-md px-4 py-2 text-etiqueta-md font-medium transition-colors',
        desactivado
          ? 'cursor-not-allowed border border-borde text-tenue'
          : 'bg-primario text-sobre-primario hover:bg-primario-enfasis disabled:opacity-90',
        className,
      ].join(' ')}
      {...resto}
    >
      <span className="relative flex h-5 w-5 items-center justify-center">
        <span
          aria-hidden="true"
          className={`absolute inset-0 rounded-full border border-current ${leyendo ? 'bio-anillo' : 'opacity-0'}`}
        />
        <Icono nombre={leyendo ? 'huella' : 'candado'} tamano={16} className={leyendo ? 'bio-trazo' : ''} />
      </span>

      <span className="relative">{leyendo ? 'Verificando…' : children}</span>

      {leyendo && (
        <span
          aria-hidden="true"
          className="bio-varrido pointer-events-none absolute inset-x-2 top-1/2 h-px bg-sobre-primario/70"
        />
      )}
    </button>
  )
}