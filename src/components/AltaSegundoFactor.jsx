import { useState } from 'react'

import { Aviso } from './Panel.jsx'
import Icono from './Icono.jsx'
import { backend } from '../lib/api.js'

/**
 * Alta del segundo factor (SCRUM-58): secreto, QR, confirmación y códigos de
 * respaldo.
 *
 * Es la pieza que faltaba para completar un alta de cuenta: el backend ya
 * exponía `preparar`, `activar` y la emisión de códigos, pero solo se podía
 * llegar a ellas desde la sección de cuenta de un usuario ya dentro del
 * sistema. Aquí se monta el paso a paso tal cual lo hacía `main.py`
 * (`mostrar_setup_2fa` + `_mostrar_codigos_respaldo`), con la misma regla: el
 * secreto no se activa hasta que el usuario demuestra que su autenticador lo
 * acepta.
 *
 * El secreto, el QR y los códigos los produce el backend; esta pantalla no
 * calcula nada criptográfico ni conserva material sensible.
 */
export default function AltaSegundoFactor({ onTerminar, textoTerminar = 'Continuar' }) {
  const [paso, setPaso] = useState('inicio')
  const [preparacion, setPreparacion] = useState(null)
  const [codigo, setCodigo] = useState('')
  const [codigos, setCodigos] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState(null)

  const empezar = async () => {
    setOcupado(true)
    setError(null)
    try {
      setPreparacion(await backend.cuenta.prepararSegundoFactor())
      setPaso('confirmar')
      setCodigo('')
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  const confirmar = async (evento) => {
    evento.preventDefault()
    setOcupado(true)
    setError(null)
    try {
      const resultado = await backend.cuenta.activarSegundoFactor(preparacion.secreto, codigo)
      setCodigos(resultado?.codigos_de_respaldo ?? [])
      setPaso('codigos')
      setCodigo('')
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {error && <Aviso tipo="error">{error}</Aviso>}

      {paso === 'inicio' && (
        <>
          <p className="text-cuerpo-sm text-tenue">
            El segundo factor añade un código temporal al acceso: sin él, una contraseña
            filtrada no basta para entrar. Necesitas una aplicación de autenticación
            (Google Authenticator, Aegis, 1Password…).
          </p>
          <div className="flex flex-wrap gap-3">
            <BotonPrincipal ocupado={ocupado} onClick={empezar} texto="Configurar el segundo factor" />
            {onTerminar && (
              <BotonSecundario onClick={onTerminar}>Dejarlo para después</BotonSecundario>
            )}
          </div>
        </>
      )}

      {paso === 'confirmar' && preparacion && (
        <form className="flex flex-col gap-4" onSubmit={confirmar}>
          <p className="text-cuerpo-sm text-tenue">
            Escanea el código con tu aplicación y confirma con los 6 dígitos que genera. El
            secreto no se activa hasta que el código sea correcto.
          </p>

          <div className="flex flex-wrap items-start gap-6">
            <img
              src={`data:image/png;base64,${preparacion.qr}`}
              alt="Código QR para configurar el doble factor"
              className="h-44 w-44 rounded-lg border border-borde bg-white p-2"
            />
            <div className="flex min-w-0 flex-col gap-2">
              <span className="text-etiqueta-sm text-texto">Si no puedes escanearlo</span>
              <code className="break-all rounded-lg border border-borde bg-fondo px-3 py-2 font-mono text-codigo">
                {preparacion.secreto}
              </code>
              <span className="text-cuerpo-sm text-tenue">
                Emisor: <span className="font-mono">DatenJäger</span>
              </span>
            </div>
          </div>

          <CampoCodigo valor={codigo} onCambio={setCodigo} autoFocus />

          <div className="flex flex-wrap gap-3">
            <BotonPrincipal
              ocupado={ocupado}
              texto="Confirmar y activar"
              inhabilitado={codigo.length !== 6}
            />
            <BotonSecundario onClick={() => setPaso('inicio')} type="button">
              Volver
            </BotonSecundario>
          </div>
        </form>
      )}

      {paso === 'codigos' && codigos && (
        <div className="flex flex-col gap-4">
          <ListaDeCodigos codigos={codigos} />
          <div className="flex flex-wrap gap-3">
            <BotonPrincipal
              ocupado={false}
              onClick={onTerminar}
              texto={textoTerminar}
            />
          </div>
        </div>
      )}
    </div>
  )
}

/** Códigos de respaldo: se muestran una sola vez. */
function ListaDeCodigos({ codigos }) {
  const [copiado, setCopiado] = useState(false)

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(codigos.join('\n'))
      setCopiado(true)
    } catch {
      setCopiado(false)
    }
  }

  return (
    <div className="aparecer flex flex-col gap-3 rounded-lg border border-alerta/40 bg-alerta/5 px-4 py-3">
      <p className="text-cuerpo-sm text-alerta">
        Guarda estos códigos ahora: no se vuelven a mostrar y cada uno sirve una sola vez
        para entrar si pierdes el autenticador.
      </p>
      <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {codigos.map((codigo) => (
          <li
            key={codigo}
            className="rounded-lg border border-borde bg-fondo px-3 py-2 text-center font-mono text-cuerpo-md tracking-widest"
          >
            {codigo}
          </li>
        ))}
      </ul>
      <div>
        <BotonSecundario type="button" onClick={copiar}>
          {copiado ? 'Copiados' : 'Copiar todos'}
        </BotonSecundario>
      </div>
    </div>
  )
}

function CampoCodigo({ valor, onCambio, ...resto }) {
  return (
    <label className="flex max-w-[16rem] flex-col gap-1">
      <span className="text-etiqueta-sm text-texto">Código del autenticador</span>
      <input
        type="text"
        value={valor}
        inputMode="numeric"
        maxLength={6}
        placeholder="6 dígitos"
        autoComplete="one-time-code"
        onChange={(evento) => onCambio(evento.target.value.replace(/\s/g, ''))}
        className="rounded-lg border border-borde bg-fondo px-3 py-2 text-center font-mono text-cuerpo-md tracking-widest outline-none transition-colors focus:border-primario"
        {...resto}
      />
    </label>
  )
}

function BotonPrincipal({ ocupado, texto, inhabilitado, ...resto }) {
  return (
    <button
      type="submit"
      disabled={ocupado || inhabilitado}
      {...resto}
      className="inline-flex items-center gap-2 rounded-lg bg-primario px-3.5 py-2 text-etiqueta-md font-medium text-sobre-primario transition-colors hover:bg-primario-enfasis disabled:opacity-50"
    >
      {ocupado ? 'Procesando…' : texto}
      {!ocupado && <Icono nombre="flecha-derecha" tamano={15} />}
    </button>
  )
}

function BotonSecundario({ children, ...resto }) {
  return (
    <button
      type="button"
      className="rounded-lg border border-borde px-3.5 py-2 text-etiqueta-md font-medium transition-colors hover:border-primario hover:text-primario disabled:opacity-50"
      {...resto}
    >
      {children}
    </button>
  )
}