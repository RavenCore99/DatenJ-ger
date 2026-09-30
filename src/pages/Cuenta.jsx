import { useCallback, useEffect, useState } from 'react'

import Panel, { Aviso, CabeceraPagina, Esqueleto, EstadoError, Pill } from '../components/Panel.jsx'
import { useApp } from '../estado/ProveedorApp.jsx'
import { backend } from '../lib/api.js'

/**
 * Panel de cuenta y ajustes (SCRUM-31).
 *
 * Reúne las secciones que tienen lógica real en el sistema —apariencia, doble
 * factor, códigos de respaldo, contraseña y confianza del dispositivo— con la
 * composición del mockup de configuración: navegación de secciones a la
 * izquierda y contenido a la derecha. El resto de secciones del mockup son
 * referencia de estilo, no alcance (CLAUDE.md sección 6).
 *
 * La verificación y el cifrado ocurren siempre en el backend: esta pantalla no
 * calcula códigos ni maneja claves.
 */
const SECCIONES = [
  { clave: 'apariencia', titulo: 'Apariencia', descripcion: 'Tema de la interfaz' },
  { clave: 'doble_factor', titulo: 'Doble factor', descripcion: 'Segundo paso al entrar' },
  { clave: 'codigos', titulo: 'Códigos de respaldo', descripcion: 'Acceso de emergencia' },
  { clave: 'contrasena', titulo: 'Contraseña', descripcion: 'Cambio y re-cifrado' },
  { clave: 'confianza', titulo: 'Dispositivos', descripcion: 'Equipos de confianza' },
]

export default function Cuenta() {
  const [seccion, setSeccion] = useState('apariencia')
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

  const activa = SECCIONES.find(({ clave }) => clave === seccion) ?? SECCIONES[0]

  return (
    <div className="flex flex-col gap-6">
      <CabeceraPagina
        titulo="Cuenta y ajustes"
        descripcion="Seguridad de la sesión, doble factor y apariencia"
        acciones={
          estado && (
            <Pill tipo={estado.segundo_factor_habilitado ? 'exito' : 'alerta'}>
              {estado.segundo_factor_habilitado ? '2FA activo' : '2FA inactivo'}
            </Pill>
          )
        }
      />

      {error && <EstadoError mensaje={error} onReintentar={recargar} />}

      <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
        <nav
          aria-label="Secciones de la cuenta"
          className="flex shrink-0 flex-row gap-1 overflow-x-auto rounded-panel border border-borde bg-superficie p-2 lg:w-60 lg:flex-col"
        >
          {SECCIONES.map(({ clave, titulo, descripcion }) => {
            const activaEsta = clave === seccion
            return (
              <button
                key={clave}
                type="button"
                onClick={() => setSeccion(clave)}
                aria-current={activaEsta ? 'true' : undefined}
                className={[
                  'flex flex-col rounded-lg px-3 py-2 text-left transition-colors',
                  activaEsta
                    ? 'bg-primario-suave text-primario'
                    : 'text-texto hover:bg-fondo-2',
                ].join(' ')}
              >
                <span className="text-etiqueta-md font-medium">{titulo}</span>
                <span className="hidden text-cuerpo-sm text-tenue lg:block">{descripcion}</span>
              </button>
            )
          })}
        </nav>

        <div className="min-w-0 flex-1">
          {!estado && !error && (
            <Panel titulo={activa.titulo} descripcion={activa.descripcion}>
              <Esqueleto variante="texto" filas={4} />
            </Panel>
          )}

          {estado && (
            <Panel titulo={activa.titulo} descripcion={activa.descripcion}>
              {seccion === 'apariencia' && <Apariencia />}
              {seccion === 'doble_factor' && <SegundoFactor estado={estado} onCambio={recargar} />}
              {seccion === 'codigos' && <CodigosRespaldo estado={estado} onCambio={recargar} />}
              {seccion === 'contrasena' && (
                <CambiarContrasena
                  tieneSegundoFactor={estado.segundo_factor_habilitado}
                  onCambio={recargar}
                />
              )}
              {seccion === 'confianza' && <Confianza estado={estado} onCambio={recargar} />}
            </Panel>
          )}
        </div>
      </div>
    </div>
  )
}

/* -------------------------------------------------------------------- */

function Apariencia() {
  const { tema, alternarTema, animaciones, alternarAnimaciones } = useApp()

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-cuerpo-md">Tema de la interfaz</p>
          <p className="text-cuerpo-sm text-tenue">
            Tema activo: <span className="font-mono">{tema}</span>
          </p>
        </div>
        <button
          type="button"
          onClick={alternarTema}
          className="rounded-lg border border-borde px-3 py-2 text-etiqueta-md font-medium transition-colors hover:border-primario hover:text-primario"
        >
          {tema === 'oscuro' ? 'Usar tema claro' : 'Usar tema oscuro'}
        </button>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-4 border-t border-borde pt-4">
        <div>
          <p className="text-cuerpo-md">Animaciones y transiciones</p>
          <p className="text-cuerpo-sm text-tenue">
            Desactivarlas reduce el movimiento en toda la aplicación.
          </p>
        </div>
        <button
          type="button"
          onClick={alternarAnimaciones}
          aria-pressed={animaciones}
          className={[
            'rounded-lg border px-3 py-2 text-etiqueta-md font-medium transition-colors',
            animaciones
              ? 'border-primario/40 bg-primario/5 text-primario'
              : 'border-borde text-tenue hover:border-primario hover:text-primario',
          ].join(' ')}
        >
          {animaciones ? 'Activadas' : 'Desactivadas'}
        </button>
      </div>
    </div>
  )
}

function SegundoFactor({ estado, onCambio }) {
  const [preparacion, setPreparacion] = useState(null)
  const [codigo, setCodigo] = useState('')
  const [pide, setPide] = useState(null) // 'activar' | 'desactivar'
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
    })

  const activar = (evento) => {
    evento.preventDefault()
    ejecutar(async () => {
      await backend.cuenta.activarSegundoFactor(preparacion.secreto, codigo)
      setPide(null)
      setPreparacion(null)
      setCodigo('')
      await onCambio()
    })
  }

  const desactivar = (evento) => {
    evento.preventDefault()
    ejecutar(async () => {
      await backend.cuenta.desactivarSegundoFactor(codigo)
      setPide(null)
      setCodigo('')
      await onCambio()
    })
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <Pill tipo={estado.segundo_factor_habilitado ? 'exito' : 'alerta'}>
          {estado.segundo_factor_habilitado ? 'Activado' : 'Desactivado'}
        </Pill>
        <div className="flex-1" />
        {estado.segundo_factor_habilitado ? (
          <BotonSecundario
            onClick={() => {
              setPide('desactivar')
              setCodigo('')
            }}
            disabled={ocupado}
          >
            Desactivar
          </BotonSecundario>
        ) : (
          <BotonPrincipal onClick={empezar} disabled={ocupado} texto="Activar doble factor" />
        )}
      </div>

      {error && <Aviso tipo="error">{error}</Aviso>}

      {pide === 'activar' && preparacion && (
        <form className="flex flex-col gap-4" onSubmit={activar}>
          <p className="text-cuerpo-sm text-tenue">
            Escanea el código con tu aplicación de autenticación y confirma con el código de 6
            dígitos que genera.
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
            </div>
          </div>

          <CampoCodigo valor={codigo} onCambio={setCodigo} autoFocus />
          <div className="flex gap-3">
            <BotonPrincipal ocupado={ocupado} texto="Confirmar y activar" />
            <BotonSecundario
              onClick={() => {
                setPide(null)
                setPreparacion(null)
                setError(null)
              }}
              type="button"
            >
              Cancelar
            </BotonSecundario>
          </div>
        </form>
      )}

      {pide === 'desactivar' && (
        <form className="flex flex-col gap-3" onSubmit={desactivar}>
          <p className="text-cuerpo-sm text-tenue">
            Desactivar el doble factor deja la cuenta protegida solo por la contraseña.
          </p>
          <CampoCodigo valor={codigo} onCambio={setCodigo} autoFocus etiqueta="Código del autenticador" />
          <div className="flex gap-3">
            <BotonPrincipal ocupado={ocupado} texto="Desactivar" />
            <BotonSecundario
              onClick={() => {
                setPide(null)
                setError(null)
              }}
              type="button"
            >
              Cancelar
            </BotonSecundario>
          </div>
        </form>
      )}
    </div>
  )
}

function CodigosRespaldo({ estado, onCambio }) {
  const [codigo, setCodigo] = useState('')
  const [codigos, setCodigos] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState(null)

  if (!estado.segundo_factor_habilitado) {
    return (
      <p className="text-cuerpo-sm text-tenue">
        Los códigos de respaldo se emiten al activar el doble factor. Actívalo primero en la
        sección «Doble factor».
      </p>
    )
  }

  const regenerar = async (evento) => {
    evento.preventDefault()
    setOcupado(true)
    setError(null)
    try {
      const resultado = await backend.cuenta.regenerarCodigos(codigo)
      setCodigos(resultado?.codigos_de_respaldo ?? null)
      setCodigo('')
      await onCambio()
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-cuerpo-sm text-tenue">
        Cada código sirve una sola vez y permite entrar sin el autenticador. Regenerarlos invalida
        los anteriores de inmediato.
      </p>

      {error && <Aviso tipo="error">{error}</Aviso>}

      <form className="flex flex-col gap-3" onSubmit={regenerar}>
        <CampoCodigo valor={codigo} onCambio={setCodigo} autoFocus />
        <div>
          <BotonPrincipal ocupado={ocupado} texto="Generar códigos nuevos" />
        </div>
      </form>

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
        <Pill tipo={estado.confianza_guardada ? 'exito' : 'neutro'}>
          {estado.confianza_guardada ? 'Este equipo está en confianza' : 'Este equipo pedirá el 2FA'}
        </Pill>
        <div className="flex-1" />
        <BotonSecundario onClick={revocar} disabled={ocupado || !estado.confianza_guardada}>
          Olvidar este equipo
        </BotonSecundario>
      </div>
      {error && <Aviso tipo="error">{error}</Aviso>}
      <p className="text-cuerpo-sm text-tenue">
        El token se guarda cifrado en el almacén local del servicio; la interfaz solo informa de si
        existe y permite revocarlo.
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
      <p className="text-cuerpo-sm text-tenue">
        El cambio de contraseña exige tener el doble factor activo: es lo que impide que una sesión
        abierta en un equipo ajeno se apropie de la cuenta.
      </p>
    )
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={enviar}>
      <Campo
        etiqueta="Contraseña actual"
        tipo="password"
        valor={actual}
        onCambio={setActual}
        autoComplete="current-password"
      />
      <Campo
        etiqueta="Nueva contraseña"
        tipo="password"
        valor={nueva}
        onCambio={setNueva}
        autoComplete="new-password"
      />
      <Campo
        etiqueta="Repite la nueva contraseña"
        tipo="password"
        valor={repetida}
        onCambio={setRepetida}
        autoComplete="new-password"
      />
      <CampoCodigo valor={codigo} onCambio={setCodigo} />

      {corta && <Aviso tipo="alerta">La contraseña debe tener al menos 8 caracteres.</Aviso>}
      {distinto && <Aviso tipo="alerta">Las contraseñas nuevas no coinciden.</Aviso>}
      {error && <Aviso tipo="error">{error}</Aviso>}
      {hecho && (
        <Aviso tipo="exito">
          Contraseña actualizada. Se volvieron a cifrar tus secretos y se revocó la confianza de
          este equipo.
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
    <div className="aparecer flex flex-col gap-3 rounded-lg border border-alerta/40 bg-alerta/5 px-4 py-3">
      <p className="text-cuerpo-sm text-alerta">
        Guarda estos códigos ahora: no se vuelven a mostrar y cada uno sirve una sola vez.
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

/* ---------------------------- piezas sueltas --------------------------- */

function Campo({ etiqueta, valor, onCambio, tipo = 'text', ...resto }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-etiqueta-sm text-texto">{etiqueta}</span>
      <input
        type={tipo}
        value={valor}
        onChange={(evento) => onCambio(evento.target.value)}
        className="rounded-lg border border-borde bg-fondo px-3 py-2 text-cuerpo-md outline-none transition-colors focus:border-primario"
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
      className="rounded-lg bg-primario px-3.5 py-2 text-etiqueta-md font-medium text-sobre-primario transition-colors hover:bg-primario-enfasis disabled:opacity-50"
    >
      {ocupado ? 'Procesando…' : texto}
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