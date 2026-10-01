import { useEffect, useRef } from 'react'

import { useApp } from '../estado/ProveedorApp.jsx'
import MarcoAcceso from '../components/MarcoAcceso.jsx'
import BotonBiometrico from '../components/BotonBiometrico.jsx'
import logo from '../../assets/logo/logo.png'
import { entradaEscalonada, pulso } from '../lib/movimiento.js'

/**
 * Pantalla de bienvenida (SCRUM-29): portal previo al acceso, con la marca, el
 * estado del servicio y las dos rutas del sistema —entrar a la bóveda o
 * registrar un operador—.
 *
 * El registro ya está disponible (SCRUM-57): la segunda tarjeta lleva al alta
 * de operador, que encadena la configuración del segundo factor (SCRUM-58).
 *
 * **Movimiento (calidad de vida)**: la marca, el título y las dos tarjetas
 * entran escalonadas, y cada tarjeta late al pulsarla. Las secuencias usan
 * `lib/movimiento.js`, que respeta la preferencia del usuario y deja la pantalla
 * en su estado final si el movimiento está desactivado. El fondo de marca
 * —partículas y nombre— vive ahora en `MarcoAcceso`, así que también acompaña
 * al acceso y al registro.
 */
export default function Bienvenida({ onEntrar, onRegistrar }) {
  const { conectado, aviso, recargarSalud, limpiarAviso } = useApp()
  const escena = useRef(null)

  useEffect(() => {
    const piezas = escena.current?.querySelectorAll('[data-entrada]')
    if (piezas?.length) entradaEscalonada([...piezas], { retardo: 70, desde: 12 })
  }, [])

  return (
    <MarcoAcceso titulo="Entorno de seguridad minera">
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
            <p data-entrada className="text-cuerpo-lg text-texto-2">
              Sistema de Gestión Documental Seguro · Bóveda criptográfica AES-256-GCM
            </p>
            <p data-entrada className="max-w-xl text-cuerpo-sm text-tenue">
              Digitalización, cifrado y consulta de documentos del sector minero de la
              Villa de San Diego de Ubaté, con todo el procesamiento en este equipo.
            </p>
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

          <div className="grid w-full gap-4 sm:grid-cols-2">
            <Tarjeta
              etiqueta="PBKDF2-SHA256"
              titulo="Acceso con bóveda existente"
              descripcion="Ingresa con tu usuario y contraseña. Si tu cuenta tiene doble factor, se pedirá el código del autenticador."
              accion="Iniciar sesión"
              onAccion={onEntrar}
            />

            <Tarjeta
              etiqueta="2FA · TOTP"
              titulo="Registro de operador"
              descripcion="Crea una cuenta nueva y configura el doble factor con su código QR y los códigos de respaldo, sin salir de la aplicación."
              accion="Registrar operador"
              onAccion={onRegistrar}
            />
          </div>

          <p data-entrada className="flex items-center gap-2 text-cuerpo-sm text-tenue">
            <span
              aria-hidden="true"
              className={`inline-block h-1.5 w-1.5 rounded-full ${conectado ? 'bg-exito' : 'bg-peligro'}`}
            />
            {conectado
              ? 'Servicio local conectado · la llave no abandona este equipo'
              : 'Servicio local no disponible: no es posible iniciar sesión'}
          </p>
        </div>
      </main>
    </MarcoAcceso>
  )
}

function Tarjeta({ etiqueta, titulo, descripcion, accion, onAccion, desactivada }) {
  const tarjeta = useRef(null)

  return (
    <article
      ref={tarjeta}
      data-entrada
      onPointerDown={() => pulso(tarjeta.current)}
      className={[
        'flex flex-col gap-3 rounded-panel border bg-superficie p-5 text-left shadow-flotante',
        desactivada ? 'border-borde opacity-70' : 'border-borde transition-colors hover:border-primario',
      ].join(' ')}
    >
      <span className="w-fit rounded border border-borde bg-fondo px-2 py-0.5 font-mono text-telemetria text-primario">
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