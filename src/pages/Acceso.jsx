import { useEffect, useState } from 'react'

import { useApp } from '../estado/ProveedorApp.jsx'
import { backend, urlBase } from '../lib/api.js'
import MarcoAcceso from '../components/MarcoAcceso.jsx'
import Icono from '../components/Icono.jsx'
import logo from '../../assets/logo/logo.png'

/**
 * Pantalla de acceso (SCRUM-29): credenciales y segundo factor, con la
 * identidad visual del sistema de diseño.
 *
 * Todo lo que se muestra es dato real del sistema: la dirección del servicio y
 * el cifrado en uso salen de la propia aplicación. Los mockups pedían un
 * semáforo de ventana, un token de hardware, un contador de operadores en turno
 * y unas cifras de iteraciones que no corresponden con este sistema
 * (dicen 600.000 rondas PBKDF2-HMAC-SHA512; aquí son 260.000 con SHA-256): no se
 * inventan, se muestran las reales o se omiten.
 *
 * La verificación ocurre en el backend de Python; esta pantalla solo envía las
 * credenciales y reacciona al estado que devuelve el servicio. La clave de
 * sesión no llega nunca al renderer.
 */
export default function Acceso({ onVolver }) {
  const { conectado, recargarSalud, aviso, limpiarAviso } = useApp()

  const [paso, setPaso] = useState('credenciales')
  const [nombre, setNombre] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [mostrar, setMostrar] = useState(false)
  const [codigo, setCodigo] = useState('')
  const [conRespaldo, setConRespaldo] = useState(false)
  const [error, setError] = useState(null)
  const [ocupado, setOcupado] = useState(false)

  const entrar = async (evento) => {
    evento.preventDefault()
    setOcupado(true)
    setError(null)

    try {
      const respuesta = await backend.sesion.entrar(nombre, contrasena)

      if (respuesta.estado === 'segundo_factor') {
        setPaso('segundo_factor')
        setCodigo('')
        setConRespaldo(false)
      } else {
        setContrasena('')
        recargarSalud()
      }
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  const verificar = async (evento) => {
    evento.preventDefault()
    setOcupado(true)
    setError(null)

    try {
      const respuesta = conRespaldo
        ? await backend.sesion.usarCodigoDeRespaldo(codigo)
        : await backend.sesion.verificarCodigo(codigo)

      if (respuesta?.autenticado) {
        setCodigo('')
        setContrasena('')
        recargarSalud()
      }
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <MarcoAcceso
      titulo="Autenticación de operador"
      subtitulo="Volver a la bienvenida"
      onVolver={onVolver}
    >
      <main className="aparecer flex min-h-0 flex-1">
        <PanelContexto conectado={conectado} />

        <section className="flex flex-1 items-center justify-center overflow-y-auto p-8">
          <div className="w-full max-w-[30rem] overflow-hidden rounded-panel border border-borde bg-superficie shadow-flotante">
            {/* Filete de acento superior, como en el mockup. */}
            <div
              aria-hidden="true"
              className="h-1 bg-gradient-to-r from-primario-enfasis via-primario to-acento"
            />

            <div className="flex flex-col gap-5 p-7">
              <Cabecera paso={paso} />

              {!conectado && (
                <Aviso tipo="peligro">
                  Sin conexión con el servicio local: no es posible iniciar sesión.
                  {aviso && (
                    <>
                      <br />
                      <span className="font-mono text-codigo">{aviso}</span>
                    </>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      limpiarAviso()
                      recargarSalud()
                    }}
                    className="ml-2 font-medium underline underline-offset-2"
                  >
                    Reintentar
                  </button>
                </Aviso>
              )}

              {error && <Aviso tipo="peligro">{error}</Aviso>}

              {paso === 'credenciales' ? (
                <form className="flex flex-col gap-4" onSubmit={entrar}>
                  <Campo
                    etiqueta="Usuario"
                    valor={nombre}
                    autoComplete="username"
                    autoFocus
                    ayuda="El nombre con el que te registraste"
                    onCambio={setNombre}
                  />

                  <Campo
                    etiqueta="Contraseña"
                    tipo={mostrar ? 'text' : 'password'}
                    valor={contrasena}
                    autoComplete="current-password"
                    mono
                    accion={
                      <button
                        type="button"
                        onClick={() => setMostrar((valor) => !valor)}
                        aria-label={mostrar ? 'Ocultar la contraseña' : 'Mostrar la contraseña'}
                        className="text-etiqueta-sm text-tenue transition-colors hover:text-primario"
                      >
                        {mostrar ? 'Ocultar' : 'Mostrar'}
                      </button>
                    }
                    onCambio={setContrasena}
                  />

                  <Boton
                    ocupado={ocupado}
                    inhabilitado={!nombre || !contrasena || !conectado}
                    texto="Continuar"
                    textoOcupado="Verificando credenciales…"
                  />

                  <p className="border-t border-borde pt-3 text-cuerpo-sm text-tenue">
                    ¿Olvidaste la contraseña? El restablecimiento con códigos de respaldo
                    llega en la sección de cuenta.
                  </p>
                </form>
              ) : (
                <form className="flex flex-col gap-4" onSubmit={verificar}>
                  <p className="text-cuerpo-sm text-tenue">
                    {conRespaldo
                      ? 'Escribe uno de tus códigos de respaldo. Cada código sirve una sola vez.'
                      : 'Escribe el código de 6 dígitos de tu aplicación de autenticación.'}
                  </p>

                  <Campo
                    etiqueta={conRespaldo ? 'Código de respaldo' : 'Código del autenticador'}
                    valor={codigo}
                    autoFocus
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    mono
                    centrado
                    onCambio={(valor) => setCodigo(valor.replace(/\s/g, ''))}
                  />

                  {!conRespaldo && <CuentaRegresiva />}

                  <Boton
                    ocupado={ocupado}
                    inhabilitado={codigo.length < 6 || !conectado}
                    texto={conRespaldo ? 'Usar código de respaldo' : 'Verificar'}
                    textoOcupado="Comprobando…"
                  />

                  <div className="flex items-center justify-between border-t border-borde pt-3 text-etiqueta-sm">
                    <button
                      type="button"
                      onClick={() => {
                        setConRespaldo((valor) => !valor)
                        setCodigo('')
                        setError(null)
                      }}
                      className="text-primario transition-colors hover:underline"
                    >
                      {conRespaldo ? 'Usar el autenticador' : 'Usar un código de respaldo'}
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        setPaso('credenciales')
                        setCodigo('')
                        setError(null)
                      }}
                      className="text-tenue transition-colors hover:text-texto"
                    >
                      Volver
                    </button>
                  </div>
                </form>
              )}

              <NotaLegal />
            </div>
          </div>
        </section>
      </main>
    </MarcoAcceso>
  )
}

/* ------------------------------------------------------------------ */

function Cabecera({ paso }) {
  return (
    <header className="flex flex-col items-center gap-3 text-center">
      <div className="relative">
        <img
          src={logo}
          alt="DatenJäger"
          className="h-16 w-16 rounded-full object-contain ring-2 ring-primario/40"
        />
        <span
          title="Servicio local verificado"
          className="absolute -bottom-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full border-2 border-superficie bg-exito text-white"
        >
          <Icono nombre="check" tamano={13} />
        </span>
      </div>

      <div>
        <h1 className="font-marca text-titulo-md tracking-tight text-primario">
          {paso === 'credenciales' ? 'Iniciar sesión en DatenJäger' : 'Verificación en dos pasos'}
        </h1>
        <p className="text-cuerpo-sm text-tenue">
          Bóveda local segura · Sector minero de Ubaté
        </p>
      </div>
    </header>
  )
}

/** Panel izquierdo con datos reales del sistema (oculto en ventanas estrechas). */
function PanelContexto({ conectado }) {
  return (
    <aside className="hidden w-[20rem] shrink-0 flex-col justify-between border-r border-borde bg-fondo-2 p-6 lg:flex">
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-panel border border-borde bg-superficie text-primario">
            <Icono nombre="candado" tamano={18} />
          </span>
          <div className="leading-tight">
            <p className="font-marca text-cuerpo-md font-semibold">Bóveda local</p>
            <p className="font-mono text-telemetria text-tenue">sin conexión externa</p>
          </div>
        </div>

        <div className="flex flex-col gap-3 rounded-panel border border-borde bg-superficie p-4">
          <span className="flex items-center justify-between gap-2">
            <span className="flex items-center gap-1.5 font-mono text-telemetria font-medium text-texto">
              <span
                aria-hidden="true"
                className={`inline-block h-1.5 w-1.5 rounded-full ${conectado ? 'bg-exito' : 'bg-peligro'}`}
              />
              SERVICIO LOCAL
            </span>
            <span className="rounded border border-borde bg-fondo px-1.5 py-0.5 font-mono text-[10px] text-tenue">
              {urlBase()}
            </span>
          </span>

          <p className="text-cuerpo-sm text-texto-2">
            Instancia local para la gestión documental cifrada del sector minero y la
            auditoría conforme a la Ley 1581.
          </p>

          <div className="flex items-center justify-between border-t border-borde pt-2 font-mono text-telemetria text-tenue">
            <span>AES-256-GCM</span>
            <span>PBKDF2-SHA256</span>
          </div>
        </div>

        <div className="flex flex-col gap-2 rounded-panel border border-primario/30 bg-primario/5 p-3.5">
          <p className="text-etiqueta-sm font-medium text-primario">
            Cumplimiento Ley 1581 / Hábeas Data
          </p>
          <p className="text-cuerpo-sm text-texto-2">
            Los documentos se cifran y se descifran en memoria en este equipo. La llave
            simétrica no sale de la estación.
          </p>
        </div>
      </div>

      <p className="border-t border-borde pt-4 text-cuerpo-sm text-tenue">
        Los documentos se guardan cifrados en disco y solo se descifran cuando los abres.
      </p>
    </aside>
  )
}

/**
 * Cuenta regresiva de la ventana del código. Es información real: el TOTP se
 * renueva cada 30 segundos, así que un código está a punto de caducar o de
 * nacer, y conviene saberlo antes de escribirlo.
 */
function CuentaRegresiva() {
  const [restante, setRestante] = useState(() => 30 - (Math.floor(Date.now() / 1000) % 30))

  useEffect(() => {
    const reloj = setInterval(() => {
      setRestante(30 - (Math.floor(Date.now() / 1000) % 30))
    }, 1000)

    return () => clearInterval(reloj)
  }, [])

  const color = restante <= 5 ? 'text-peligro' : restante <= 12 ? 'text-alerta' : 'text-exito'

  return (
    <p className={`flex items-center gap-2 font-mono text-telemetria ${color}`}>
      <span aria-hidden="true" className="inline-block h-1.5 w-1.5 rounded-full bg-current" />
      El código se renueva en {restante} s
    </p>
  )
}

function NotaLegal() {
  return (
    <p className="flex items-start gap-2.5 rounded-lg border border-borde bg-fondo px-3 py-2.5 text-cuerpo-sm text-texto-2">
      <span aria-hidden="true" className="shrink-0 text-primario">
        <Icono nombre="escudo" tamano={16} />
      </span>
      <span>
        <span className="font-semibold text-texto">Ley 1581 de 2012 / Hábeas Data:</span> tus
        credenciales se verifican en este equipo con PBKDF2. Ninguna clave viaja por la red.
      </span>
    </p>
  )
}

function Aviso({ tipo, children }) {
  const clases = {
    peligro: 'border-peligro/40 bg-peligro/5 text-peligro',
    alerta: 'border-alerta/40 bg-alerta/5 text-alerta',
  }[tipo]

  return (
    <p role="alert" className={`rounded-lg border px-3 py-2 text-cuerpo-sm ${clases}`}>
      {children}
    </p>
  )
}

function Campo({
  etiqueta,
  valor,
  onCambio,
  tipo = 'text',
  ayuda,
  accion,
  mono,
  centrado,
  ...resto
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="flex items-center justify-between gap-2">
        <span className="text-etiqueta-sm text-texto">{etiqueta}</span>
        {accion}
      </span>

      <input
        type={tipo}
        value={valor}
        required
        onChange={(evento) => onCambio(evento.target.value)}
        className={[
          'rounded-lg border border-borde bg-fondo px-3 py-2 text-cuerpo-md outline-none',
          'transition-colors focus:border-primario focus:ring-1 focus:ring-primario',
          mono ? 'font-mono tracking-widest' : '',
          centrado ? 'text-center' : '',
        ].join(' ')}
        {...resto}
      />

      {ayuda && <span className="text-cuerpo-sm text-tenue">{ayuda}</span>}
    </label>
  )
}

function Boton({ ocupado, inhabilitado, texto, textoOcupado }) {
  return (
    <button
      type="submit"
      disabled={ocupado || inhabilitado}
      className="flex items-center justify-center gap-2 rounded-lg bg-primario px-4 py-2.5 text-etiqueta-md font-medium text-sobre-primario transition-colors hover:bg-primario-enfasis disabled:opacity-50"
    >
      {ocupado ? textoOcupado : texto}
      {!ocupado && <Icono nombre="flecha-derecha" tamano={15} />}
    </button>
  )
}