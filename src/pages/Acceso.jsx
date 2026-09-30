import { useState } from 'react'

import { useApp } from '../estado/ProveedorApp.jsx'
import { backend } from '../lib/api.js'
import { enEscritorio } from '../lib/escritorio.js'

/**
 * Pantalla de acceso (SCRUM-22): credenciales y segundo factor.
 *
 * La verificación ocurre en el backend de Python; esta pantalla solo envía
 * las credenciales y reacciona al estado que devuelve el servicio. La clave
 * de sesión no llega nunca al renderer: se queda en el proceso Python.
 */
export default function Acceso() {
  const { conectado, recargarSalud } = useApp()

  const [paso, setPaso] = useState('credenciales')
  const [nombre, setNombre] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [codigo, setCodigo] = useState('')
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
      await backend.sesion.verificarCodigo(codigo)
      setCodigo('')
      setContrasena('')
      recargarSalud()
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  const usarRespaldo = async () => {
    setOcupado(true)
    setError(null)

    try {
      await backend.sesion.usarCodigoDeRespaldo(codigo)
      setCodigo('')
      setContrasena('')
      recargarSalud()
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <div className="flex h-full w-full items-center justify-center bg-fondo px-6">
      <div className="w-full max-w-sm">
        <header className="mb-6 text-center">
          <Logo />
          <h1 className="mt-3 text-lg font-semibold tracking-tight">DatenJäger</h1>
          <p className="text-xs text-tenue">
            {paso === 'credenciales'
              ? 'Acceso al sistema de gestión documental'
              : 'Verificación en dos pasos'}
          </p>
        </header>

        <div className="rounded-panel border border-borde bg-superficie px-6 py-6">
          {!conectado && (
            <p className="mb-4 rounded-lg border border-peligro/40 bg-peligro/5 px-3 py-2 text-xs text-peligro">
              Sin conexión con el servicio local: no es posible iniciar sesión.
            </p>
          )}

          {error && (
            <p
              role="alert"
              className="mb-4 rounded-lg border border-peligro/40 bg-peligro/5 px-3 py-2 text-xs text-peligro"
            >
              {error}
            </p>
          )}

          {paso === 'credenciales' ? (
            <form className="flex flex-col gap-4" onSubmit={entrar}>
              <Campo
                etiqueta="Usuario"
                valor={nombre}
                autoComplete="username"
                autoFocus
                onCambio={(evento) => setNombre(evento.target.value)}
              />
              <Campo
                etiqueta="Contraseña"
                tipo="password"
                valor={contrasena}
                autoComplete="current-password"
                onCambio={(evento) => setContrasena(evento.target.value)}
              />
              <Boton ocupado={ocupado} texto="Ingresar" textoOcupado="Verificando…" />
            </form>
          ) : (
            <form className="flex flex-col gap-4" onSubmit={verificar}>
              <p className="text-xs text-tenue">
                Ingresa el código de 6 dígitos de tu aplicación de autenticación, o uno
                de tus códigos de respaldo.
              </p>
              <Campo
                etiqueta="Código"
                valor={codigo}
                autoFocus
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                onCambio={(evento) => setCodigo(evento.target.value.replace(/\s/g, ''))}
              />
              <Boton ocupado={ocupado} texto="Verificar" textoOcupado="Comprobando…" />
              <button
                type="button"
                onClick={usarRespaldo}
                disabled={ocupado || codigo.length < 6}
                className="text-[11px] text-tenue underline-offset-2 hover:text-primario hover:underline disabled:opacity-50"
              >
                Usar como código de respaldo
              </button>
              <button
                type="button"
                onClick={() => {
                  setPaso('credenciales')
                  setError(null)
                  setCodigo('')
                }}
                className="text-[11px] text-tenue underline-offset-2 hover:text-primario hover:underline"
              >
                Volver
              </button>
            </form>
          )}
        </div>

        <p className="mt-4 text-center font-mono text-[10px] text-tenue">
          {enEscritorio() ? 'aplicación de escritorio' : 'navegador de desarrollo'}
        </p>
      </div>
    </div>
  )
}

function Campo({ etiqueta, valor, onCambio, tipo = 'text', ...resto }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] uppercase tracking-wider text-tenue">{etiqueta}</span>
      <input
        type={tipo}
        value={valor}
        onChange={onCambio}
        required
        className="rounded-lg border border-borde bg-fondo px-3 py-2 text-sm outline-none focus:border-primario"
        {...resto}
      />
    </label>
  )
}

function Boton({ ocupado, texto, textoOcupado }) {
  return (
    <button
      type="submit"
      disabled={ocupado}
      className="rounded-lg bg-primario px-4 py-2 text-sm font-medium text-white transition-opacity disabled:opacity-50"
    >
      {ocupado ? textoOcupado : texto}
    </button>
  )
}

function Logo() {
  return (
    <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#0D0F1A] ring-2 ring-primario">
      <svg viewBox="0 0 24 24" className="h-6 w-6 text-white" aria-hidden="true">
        <path
          fill="currentColor"
          d="M4 14c3.2-.4 5.6-1.9 7.4-4.4.5-.7.9-1.5 1.2-2.3 1.6 1 2.5 2.2 2.8 3.6.3 1.5-.1 3-1.2 4.4-1.9 2.4-4.9 3.4-8.4 3l-1.8-4.3Z"
        />
      </svg>
    </span>
  )
}