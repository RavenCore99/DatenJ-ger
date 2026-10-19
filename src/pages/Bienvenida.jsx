import { useEffect, useRef, useState } from 'react'

import { useApp } from '../estado/ProveedorApp.jsx'
import MarcoAcceso from '../components/MarcoAcceso.jsx'
import BotonBiometrico from '../components/BotonBiometrico.jsx'
import logo from '../../assets/logo/logo.png'
import { entradaEscalonada, pulso } from '../lib/movimiento.js'

/** Presenta las opciones de acceso y registro del portal. */
export default function Bienvenida({ onEntrar, onRegistrar }) {
  const { conectado, aviso, recargarSalud, limpiarAviso } = useApp()
  const escena = useRef(null)
  const [desplegado, setDesplegado] = useState(false)

  useEffect(() => {
    const piezas = escena.current?.querySelectorAll('[data-entrada]')
    if (piezas?.length) entradaEscalonada([...piezas], { retardo: 70, desde: 12 })
  }, [])

  return (
    <MarcoAcceso>
      <main className="aparecer relative flex min-h-0 flex-1 items-center justify-center overflow-y-auto p-8">
        <div ref={escena} className="relative flex w-full max-w-3xl flex-col items-center gap-8">
          <header className="flex flex-col items-center gap-3 text-center">
            <img
              data-entrada
              src={logo}
              alt="DatenJäger"
              className="h-20 w-20 rounded-full object-contain ring-2 ring-primario/40"
            />
            <h1 data-entrada className="font-marca text-titulo-lg tracking-tight text-primario">
              DatenJäger
            </h1>
          </header>

          {/* El motivo real, no solo «sin conexión»: el proceso principal sabe
              por qué no arrancó el servicio (puerto ocupado, base caída…). */}
          {!conectado && (
            <div
              role="status"
              className="w-full rounded-lg border border-peligro/40 bg-peligro/5 px-4 py-3 text-left text-cuerpo-sm text-peligro"
            >
              <p className="font-medium">El servicio local no está disponible</p>
              <p className="mt-1 text-texto-2">
                {aviso
                  ? aviso
                  : 'Todavía se está comprobando. Si persiste, cierra cualquier instancia anterior de la aplicación y reintenta.'}
              </p>
              <button
                type="button"
                onClick={() => {
                  limpiarAviso()
                  recargarSalud()
                }}
                className="mt-2 rounded-md border border-peligro/40 px-3 py-1 text-etiqueta-sm font-medium transition-colors hover:bg-peligro/10"
              >
                Reintentar
              </button>
            </div>
          )}

          <div data-entrada className="flex flex-col items-center gap-2">
            <BotonBiometrico
              onCompletar={() => setDesplegado(true)}
              desactivado={!conectado || desplegado}
              className="px-10 py-3 text-cuerpo-lg"
            >
              Ingresar
            </BotonBiometrico>
            <span className="text-cuerpo-sm text-tenue">
              Acceso con bóveda existente o registro de un operador nuevo
            </span>
          </div>

          {/* Las dos secciones del portal se despliegan con una transición de
              rejilla (0fr → 1fr): sin alturas mágicas ni medidas en píxeles.
              Mientras están recogidas quedan fuera del foco (`inert`). */}
          <div
            aria-hidden={!desplegado}
            inert={!desplegado || undefined}
            className={`grid w-full transition-all duration-500 ease-out ${
              desplegado ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
            }`}
          >
            <div className="overflow-hidden">
              <div className="grid overflow-hidden rounded-panel bg-superficie shadow-flotante ring-1 ring-borde/50 sm:grid-cols-2">
                <Tarjeta
                  etiqueta="PBKDF2-SHA256"
                  titulo="Acceso con bóveda existente"
                  descripcion="Ingresa con tu usuario y contraseña. Si tu cuenta tiene doble factor, se pedirá el código del autenticador."
                  accion="Iniciar sesión"
                  onAccion={onEntrar}
                />

                <Tarjeta
                  separada
                  etiqueta="2FA · TOTP"
                  titulo="Registro de operador"
                  descripcion="Crea una cuenta nueva y configura el doble factor con su código QR y los códigos de respaldo, sin salir de la aplicación."
                  accion="Registrar operador"
                  onAccion={onRegistrar}
                />
              </div>
            </div>
          </div>
        </div>
      </main>
    </MarcoAcceso>
  )
}

function Tarjeta({ etiqueta, titulo, descripcion, accion, onAccion, desactivada, separada = false }) {
  const tarjeta = useRef(null)

  return (
    <article
      ref={tarjeta}
      data-entrada
      onPointerDown={() => pulso(tarjeta.current)}
      className={[
        'flex flex-col gap-3 p-6 text-left transition-colors',
        separada ? 'border-t border-borde/50 sm:border-l sm:border-t-0' : '',
        desactivada ? 'opacity-70' : 'hover:bg-fondo-2/60 focus-within:bg-fondo-2/60',
      ].join(' ')}
    >
      <span className="font-mono text-telemetria text-primario">
        {etiqueta}
      </span>

      <h2 className="font-marca text-titulo-sm">{titulo}</h2>
      <p className="flex-1 text-cuerpo-sm text-tenue">{descripcion}</p>

      {desactivada ? (
        <button
          type="button"
          disabled
          className="cursor-not-allowed rounded-md border border-borde px-4 py-2 text-etiqueta-md font-medium text-tenue"
        >
          {accion}
        </button>
      ) : (
        <BotonBiometrico onCompletar={onAccion}>{accion}</BotonBiometrico>
      )}
    </article>
  )
}
