import { useApp } from '../estado/ProveedorApp.jsx'
import MarcoAcceso from '../components/MarcoAcceso.jsx'
import BotonBiometrico from '../components/BotonBiometrico.jsx'
import Particulas from '../components/Particulas.jsx'
import logo from '../../assets/logo/logo.png'

/**
 * Pantalla de bienvenida (SCRUM-29): portal previo al acceso, con la marca, el
 * estado del servicio y las dos rutas del sistema —entrar a la bóveda o
 * registrar un operador—.
 *
 * El registro ya está disponible (SCRUM-57): la segunda tarjeta lleva al alta
 * de operador, que encadena la configuración del segundo factor (SCRUM-58).
 */
export default function Bienvenida({ onEntrar, onRegistrar }) {
  const { conectado } = useApp()

  return (
    <MarcoAcceso titulo="Entorno de seguridad minera">
      <main className="aparecer relative flex min-h-0 flex-1 items-center justify-center overflow-y-auto p-8">
        {/* Fondo de partículas (SCRUM-71): decorativo, no captura el puntero. */}
        <Particulas className="pointer-events-none absolute inset-0 h-full w-full" />

        {/* Marca de agua tenue del fondo, como en el mockup. */}
        <span
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 flex select-none items-center justify-center font-marca text-[16vw] font-bold tracking-tighter text-primario opacity-[0.03]"
        >
          DATENJÄGER
        </span>

        <div className="relative flex w-full max-w-3xl flex-col items-center gap-8">
          <header className="flex flex-col items-center gap-3 text-center">
            <img
              src={logo}
              alt="DatenJäger"
              className="h-20 w-20 rounded-full object-contain ring-2 ring-primario/40"
            />
            <h1 className="font-marca text-titulo-lg tracking-tight text-primario">
              DatenJäger
            </h1>
            <p className="text-cuerpo-lg text-texto-2">
              Sistema de Gestión Documental Seguro · Bóveda criptográfica AES-256-GCM
            </p>
            <p className="max-w-xl text-cuerpo-sm text-tenue">
              Digitalización, cifrado y consulta de documentos del sector minero de la
              Villa de San Diego de Ubaté, con todo el procesamiento en este equipo.
            </p>
          </header>

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

          <p className="flex items-center gap-2 text-cuerpo-sm text-tenue">
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
  return (
    <article
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