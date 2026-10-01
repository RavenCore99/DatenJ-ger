import { useEffect, useState } from 'react'

import { useApp } from '../estado/ProveedorApp.jsx'
import { backend } from '../lib/api.js'
import MarcoAcceso from '../components/MarcoAcceso.jsx'
import TerminosUso from '../components/TerminosUso.jsx'
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
  // Restablecimiento (SCRUM-84): la contraseña nueva y su confirmación, más el
  // acuse de recibo que se muestra al volver al acceso.
  const [nueva, setNueva] = useState('')
  const [confirmar, setConfirmar] = useState('')
  const [restablecido, setRestablecido] = useState(false)

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

  /**
   * Paso 1 del restablecimiento: verifica un código de respaldo. Es lo único
   * que puede autenticar a quien olvidó la contraseña, porque el secreto del
   * autenticador está cifrado con una clave derivada de esa misma contraseña.
   */
  const solicitarRestablecimiento = async (evento) => {
    evento.preventDefault()
    setOcupado(true)
    setError(null)

    try {
      const respuesta = await backend.sesion.solicitarRestablecimiento(nombre, codigo)
      setCodigo('')
      setNombre(respuesta?.nombre ?? nombre)
      setPaso('restablecer_contrasena')
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  /** Paso 2: fija la contraseña nueva. El backend reinicia el segundo factor. */
  const fijarContrasena = async (evento) => {
    evento.preventDefault()

    if (nueva !== confirmar) {
      setError('Las dos contraseñas no coinciden')
      return
    }

    setOcupado(true)
    setError(null)

    try {
      await backend.sesion.fijarContrasenaRestablecida(nueva)
      setNueva('')
      setConfirmar('')
      setContrasena('')
      setPaso('credenciales')
      setRestablecido(true)
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
      <main className="aparecer relative flex min-h-0 flex-1">
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

              {restablecido && paso === 'credenciales' && (
                <Aviso tipo="exito">
                  Contraseña restablecida. El segundo factor se reinició: al entrar,
                  vuelve a configurarlo desde Ajustes con un autenticador nuevo.
                </Aviso>
              )}

              {paso === 'credenciales' && (
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

                  <div className="flex items-center justify-between gap-3 border-t border-borde pt-3 text-etiqueta-sm">
                    <button
                      type="button"
                      onClick={() => {
                        setPaso('restablecer')
                        setCodigo('')
                        setError(null)
                        setRestablecido(false)
                      }}
                      className="text-primario transition-colors hover:underline"
                    >
                      ¿Olvidaste la contraseña?
                    </button>
                    <span className="text-tenue">Se recupera con un código de respaldo</span>
                  </div>
                </form>
              )}

              {paso === 'segundo_factor' && (
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

              {paso === 'restablecer' && (
                <form className="flex flex-col gap-4" onSubmit={solicitarRestablecimiento}>
                  <p className="text-cuerpo-sm text-tenue">
                    Escribe tu usuario y uno de los códigos de respaldo que el sistema te
                    entregó al configurar el segundo factor. El código se consume.
                  </p>

                  <Campo
                    etiqueta="Usuario"
                    valor={nombre}
                    autoFocus
                    autoComplete="username"
                    onCambio={setNombre}
                  />

                  <Campo
                    etiqueta="Código de respaldo"
                    valor={codigo}
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    mono
                    centrado
                    ayuda="Cada código sirve una sola vez"
                    onCambio={(valor) => setCodigo(valor.replace(/\s/g, ''))}
                  />

                  <Boton
                    ocupado={ocupado}
                    inhabilitado={!nombre || codigo.length < 6 || !conectado}
                    texto="Verificar código"
                    textoOcupado="Comprobando…"
                  />

                  <div className="flex items-center justify-end border-t border-borde pt-3 text-etiqueta-sm">
                    <button
                      type="button"
                      onClick={() => {
                        setPaso('credenciales')
                        setCodigo('')
                        setError(null)
                      }}
                      className="text-tenue transition-colors hover:text-texto"
                    >
                      Volver al acceso
                    </button>
                  </div>
                </form>
              )}

              {paso === 'restablecer_contrasena' && (
                <form className="flex flex-col gap-4" onSubmit={fijarContrasena}>
                  <p className="text-cuerpo-sm text-tenue">
                    Identidad verificada para <span className="font-mono">{nombre}</span>. Elige la
                    contraseña nueva; al guardarla, el segundo factor se reinicia y tendrás que
                    volver a configurarlo con tu autenticador.
                  </p>

                  <Campo
                    etiqueta="Contraseña nueva"
                    tipo="password"
                    valor={nueva}
                    autoFocus
                    autoComplete="new-password"
                    mono
                    ayuda="Mínimo 8 caracteres, con mayúsculas, números y símbolos"
                    onCambio={setNueva}
                  />

                  <Campo
                    etiqueta="Repite la contraseña nueva"
                    tipo="password"
                    valor={confirmar}
                    autoComplete="new-password"
                    mono
                    onCambio={setConfirmar}
                  />

                  <Boton
                    ocupado={ocupado}
                    inhabilitado={!nueva || !confirmar || !conectado}
                    texto="Guardar contraseña"
                    textoOcupado="Guardando…"
                  />
                </form>
              )}

              <div className="flex items-center justify-center border-t border-borde pt-3">
                <TerminosUso />
              </div>
            </div>
          </div>
        </section>
      </main>
    </MarcoAcceso>
  )
}

/* ------------------------------------------------------------------ */

function Cabecera({ paso }) {
  const titulos = {
    credenciales: 'Iniciar sesión en DatenJäger',
    segundo_factor: 'Verificación en dos pasos',
    restablecer: 'Restablecer la contraseña',
    restablecer_contrasena: 'Elige la contraseña nueva',
  }

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
          {titulos[paso] ?? titulos.credenciales}
        </h1>
        <p className="text-cuerpo-sm text-tenue">
          Sector minero de la Villa de San Diego de Ubaté
        </p>
      </div>
    </header>
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

function Aviso({ tipo, children }) {
  const clases = {
    peligro: 'border-peligro/40 bg-peligro/5 text-peligro',
    alerta: 'border-alerta/40 bg-alerta/5 text-alerta',
    exito: 'border-exito/40 bg-exito/5 text-exito',
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