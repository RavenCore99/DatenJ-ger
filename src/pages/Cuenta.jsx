import { useCallback, useEffect, useState } from 'react'

import Panel, { EstadoError, Esqueleto } from '../components/Panel.jsx'
import { useApp } from '../estado/ProveedorApp.jsx'
import { backend } from '../lib/api.js'

/**
 * Panel de cuenta (SCRUM-25): contraseña, doble factor, códigos de respaldo,
 * confianza del dispositivo y apariencia.
 *
 * Solo se construyen las secciones que tienen lógica real en el sistema; el
 * resto de la referencia visual de configuración no es alcance (CLAUDE.md
 * sección 6). La verificación y el cifrado ocurren siempre en el backend: esta
 * pantalla no calcula códigos ni maneja claves.
 */
export default function Cuenta() {
  const { tema, alternarTema } = useApp()
  const [estado, setEstado] = useState(null)
  const [error, setError] = useState(null)

  const recargar = useCallback(async () => {
    try {
      setEstado(await backend.cuenta.estado())
      setError(null)
    } catch (fallo) {
      setError(fallo.message)
    }
  }, [])

  useEffect(() => {
    recargar()
  }, [recargar])

  return (
    <div className="flex flex-col gap-6">
      <Panel titulo="Apariencia" descripcion="Tema de la interfaz">
        <div className="flex items-center justify-between gap-4">
          <p className="text-xs text-tenue">
            Tema activo: <span className="font-mono">{tema}</span>
          </p>
          <button
            type="button"
            onClick={alternarTema}
            className="rounded-lg border border-borde px-3 py-1.5 text-xs font-medium transition-colors hover:border-primario hover:text-primario"
          >
            Alternar tema
          </button>
        </div>
      </Panel>

      {error && <EstadoError mensaje={error} onReintentar={recargar} />}

      {!estado && !error && <Esqueleto lineas={3} />}

      {estado && (
        <>
          <Panel titulo="Doble factor" descripcion="Segundo paso al iniciar sesión">
            <SegundoFactor estado={estado} onCambio={recargar} />
          </Panel>

          <Panel
            titulo="Contraseña"
            descripcion="Cambiarla vuelve a cifrar tus secretos y revoca la confianza"
          >
            <CambiarContrasena tieneSegundoFactor={estado.segundo_factor_habilitado}
                               onCambio={recargar} />
          </Panel>

          <Panel titulo="Dispositivos de confianza"
                 descripcion="Permiten omitir el segundo factor en este equipo">
            <Confianza estado={estado} onCambio={recargar} />
          </Panel>
        </>
      )}
    </div>
  )
}

/* -------------------------------------------------------------------- */

function SegundoFactor({ estado, onCambio }) {
  const [preparacion, setPreparacion] = useState(null)
  const [codigo, setCodigo] = useState('')
  const [codigos, setCodigos] = useState(null)
  const [pide, setPide] = useState(null) // 'activar' | 'desactivar' | 'regenerar'
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState(null)

  const ejecutar = async (accion) => {
    setOcupado(true)
    setError(null)
    try {
      await accion()
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  const empezar = () =>
    ejecutar(async () => {
      setPreparacion(await backend.cuenta.prepararSegundoFactor())
      setPide('activar')
      setCodigo('')
      setCodigos(null)
    })

  const activar = (evento) => {
    evento.preventDefault()
    ejecutar(async () => {
      const resultado = await backend.cuenta.activarSegundoFactor(preparacion.secreto, codigo)
      setCodigos(resultado.codigos_de_respaldo)
      setPide(null)
      setPreparacion(null)
      setCodigo('')
      await onCambio()
    })
  }

  const conCodigo = (nombre) => (evento) => {
    evento.preventDefault()
    ejecutar(async () => {
      const resultado =
        nombre === 'desactivar'
          ? await backend.cuenta.desactivarSegundoFactor(codigo)
          : await backend.cuenta.regenerarCodigos(codigo)

      if (resultado?.codigos_de_respaldo) setCodigos(resultado.codigos_de_respaldo)
      setPide(null)
      setCodigo('')
      await onCambio()
    })
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <Insignia activo={estado.segundo_factor_habilitado} />
        <div className="flex-1" />
        {estado.segundo_factor_habilitado ? (
          <>
            <BotonSecundario onClick={() => { setPide('regenerar'); setCodigo('') }} disabled={ocupado}>
              Regenerar códigos
            </BotonSecundario>
            <BotonSecundario onClick={() => { setPide('desactivar'); setCodigo('') }} disabled={ocupado}>
              Desactivar
            </BotonSecundario>
          </>
        ) : (
          <BotonPrincipal onClick={empezar} disabled={ocupado} texto="Activar doble factor" />
        )}
      </div>

      {error && <Aviso tipo="error">{error}</Aviso>}

      {pide === 'activar' && preparacion && (
        <form className="flex flex-col gap-4" onSubmit={activar}>
          <p className="text-xs text-tenue">
            Escanea el código con tu aplicación de autenticación y confirma con el
            código de 6 dígitos que genera.
          </p>

          <div className="flex flex-wrap items-start gap-6">
            <img
              src={`data:image/png;base64,${preparacion.qr}`}
              alt="Código QR para configurar el doble factor"
              className="h-44 w-44 rounded-lg border border-borde bg-white p-2"
            />
            <div className="flex min-w-0 flex-col gap-2">
              <span className="text-[11px] uppercase tracking-wider text-tenue">
                Si no puedes escanearlo
              </span>
              <code className="break-all rounded-lg border border-borde bg-fondo px-3 py-2 font-mono text-[11px]">
                {preparacion.secreto}
              </code>
            </div>
          </div>

          <CampoCodigo valor={codigo} onCambio={setCodigo} autoFocus />
          <div className="flex gap-3">
            <BotonPrincipal ocupado={ocupado} texto="Confirmar y activar" />
            <BotonSecundario
              onClick={() => { setPide(null); setPreparacion(null); setError(null) }}
              type="button"
            >
              Cancelar
            </BotonSecundario>
          </div>
        </form>
      )}

      {(pide === 'desactivar' || pide === 'regenerar') && (
        <form className="flex flex-col gap-3" onSubmit={conCodigo(pide)}>
          <p className="text-xs text-tenue">
            {pide === 'desactivar'
              ? 'Desactivar el doble factor deja la cuenta protegida solo por la contraseña.'
              : 'Los códigos actuales dejarán de servir en cuanto se emitan los nuevos.'}
          </p>
          <CampoCodigo valor={codigo} onCambio={setCodigo} autoFocus etiqueta="Código del autenticador" />
          <div className="flex gap-3">
            <BotonPrincipal
              ocupado={ocupado}
              texto={pide === 'desactivar' ? 'Desactivar' : 'Generar códigos nuevos'}
            />
            <BotonSecundario onClick={() => { setPide(null); setError(null) }} type="button">
              Cancelar
            </BotonSecundario>
          </div>
        </form>
      )}

      {codigos && <ListaDeCodigos codigos={codigos} />}
    </div>
  )
}

function Confianza({ estado, onCambio }) {
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState(null)

  const revocar = async () => {
    setOcupado(true)
    setError(null)
    try {
      await backend.cuenta.revocarConfianza()
      await onCambio()
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <Insignia activo={estado.confianza_guardada}
                  activoTexto="Este equipo está en confianza"
                  inactivoTexto="Este equipo pedirá el doble factor" />
        <div className="flex-1" />
        <BotonSecundario onClick={revocar} disabled={ocupado || !estado.confianza_guardada}>
          Olvidar este equipo
        </BotonSecundario>
      </div>
      {error && <Aviso tipo="error">{error}</Aviso>}
      <p className="text-[11px] text-tenue">
        El token se guarda cifrado en el almacén local del servicio; la interfaz
        solo informa de si existe y permite revocarlo.
      </p>
    </div>
  )
}

function CambiarContrasena({ tieneSegundoFactor, onCambio }) {
  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [repetida, setRepetida] = useState('')
  const [codigo, setCodigo] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const [hecho, setHecho] = useState(false)
  const [error, setError] = useState(null)

  const distinto = repetida.length > 0 && nueva !== repetida
  const corta = nueva.length > 0 && nueva.length < 8

  const enviar = async (evento) => {
    evento.preventDefault()
    setOcupado(true)
    setError(null)
    setHecho(false)

    try {
      await backend.cuenta.cambiarContrasena(actual, nueva, codigo)
      setActual('')
      setNueva('')
      setRepetida('')
      setCodigo('')
      setHecho(true)
      await onCambio()
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  if (!tieneSegundoFactor) {
    return (
      <p className="text-xs text-tenue">
        El cambio de contraseña exige tener el doble factor activo: es lo que impide
        que una sesión abierta en un equipo ajeno se apropie de la cuenta.
      </p>
    )
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={enviar}>
      <Campo etiqueta="Contraseña actual" tipo="password" valor={actual}
             onCambio={setActual} autoComplete="current-password" />
      <Campo etiqueta="Nueva contraseña" tipo="password" valor={nueva}
             onCambio={setNueva} autoComplete="new-password" />
      <Campo etiqueta="Repite la nueva contraseña" tipo="password" valor={repetida}
             onCambio={setRepetida} autoComplete="new-password" />
      <CampoCodigo valor={codigo} onCambio={setCodigo} />

      {corta && <Aviso tipo="alerta">La contraseña debe tener al menos 8 caracteres.</Aviso>}
      {distinto && <Aviso tipo="alerta">Las contraseñas nuevas no coinciden.</Aviso>}
      {error && <Aviso tipo="error">{error}</Aviso>}
      {hecho && (
        <Aviso tipo="exito">
          Contraseña actualizada. Se volvieron a cifrar tus secretos y se revocó la
          confianza de este equipo.
        </Aviso>
      )}

      <div>
        <BotonPrincipal
          ocupado={ocupado}
          texto="Cambiar contraseña"
          inhabilitado={corta || distinto || !actual || !codigo}
        />
      </div>
    </form>
  )
}

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
    <div className="flex flex-col gap-3 rounded-lg border border-alerta/40 bg-alerta/5 px-4 py-3">
      <p className="text-xs text-alerta">
        Guarda estos códigos ahora: no se vuelven a mostrar y cada uno sirve una sola vez.
      </p>
      <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {codigos.map((codigo) => (
          <li key={codigo} className="rounded-lg border border-borde bg-fondo px-3 py-2
                                      text-center font-mono text-sm tracking-widest">
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

/* ---------------------------- piezas sueltas --------------------------- */

function Insignia({ activo, activoTexto = 'Activado', inactivoTexto = 'Desactivado' }) {
  return (
    <span
      className={`rounded-full border px-2.5 py-1 text-[11px] font-medium ${
        activo
          ? 'border-exito/40 bg-exito/10 text-exito'
          : 'border-borde bg-fondo text-tenue'
      }`}
    >
      {activo ? activoTexto : inactivoTexto}
    </span>
  )
}

function Aviso({ tipo, children }) {
  const clases = {
    error: 'border-peligro/40 bg-peligro/5 text-peligro',
    alerta: 'border-alerta/40 bg-alerta/5 text-alerta',
    exito: 'border-exito/40 bg-exito/5 text-exito',
  }[tipo]

  return (
    <p role={tipo === 'error' ? 'alert' : undefined}
       className={`rounded-lg border px-3 py-2 text-xs ${clases}`}>
      {children}
    </p>
  )
}

function Campo({ etiqueta, valor, onCambio, tipo = 'text', ...resto }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] uppercase tracking-wider text-tenue">{etiqueta}</span>
      <input
        type={tipo}
        value={valor}
        onChange={(evento) => onCambio(evento.target.value)}
        className="rounded-lg border border-borde bg-fondo px-3 py-2 text-sm outline-none focus:border-primario"
        {...resto}
      />
    </label>
  )
}

function CampoCodigo({ valor, onCambio, etiqueta = 'Código del autenticador', ...resto }) {
  return (
    <div className="max-w-[16rem]">
      <Campo
        etiqueta={etiqueta}
        valor={valor}
        inputMode="numeric"
        maxLength={6}
        placeholder="6 dígitos"
        onCambio={(texto) => onCambio(texto.replace(/\s/g, ''))}
        {...resto}
      />
    </div>
  )
}

function BotonPrincipal({ ocupado, texto, inhabilitado, ...resto }) {
  return (
    <button
      type="submit"
      disabled={ocupado || inhabilitado}
      {...resto}
      className="rounded-lg bg-primario px-3 py-1.5 text-xs font-medium text-white
                 transition-opacity disabled:opacity-50"
    >
      {ocupado ? 'Procesando…' : texto}
    </button>
  )
}

function BotonSecundario({ children, ...resto }) {
  return (
    <button
      type="button"
      className="rounded-lg border border-borde px-3 py-1.5 text-xs font-medium
                 transition-colors hover:border-primario hover:text-primario
                 disabled:opacity-50"
      {...resto}
    >
      {children}
    </button>
  )
}