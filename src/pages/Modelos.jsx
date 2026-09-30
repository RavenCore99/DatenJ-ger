import { useEffect, useState } from 'react'

import Panel, {
  Aviso,
  CabeceraPagina,
  Esqueleto,
  EstadoError,
  EstadoVacio,
  Pill,
} from '../components/Panel.jsx'
import Icono from '../components/Icono.jsx'
import { useApp } from '../estado/ProveedorApp.jsx'
import { backend } from '../lib/api.js'

/**
 * Panel de conexión de APIs y modelos (SCRUM-64).
 *
 * Es la pantalla dedicada —no un ajuste suelto— para elegir el modelo de IA y
 * cargar sus credenciales. El chatbot se queda **solo por API** hasta que el
 * frontend y el backend estén completos: aquí no se configura ningún modelo
 * local, y el proveedor «compatible con OpenAI» aparece marcado como no
 * implementado para que el hueco sea explícito y no una promesa.
 *
 * **La clave no pasa por el renderer.** Se envía una vez al backend, que la
 * cifra con AES-256-GCM en su almacén local (`modelos/`, 0600/0700) y solo
 * informa de *si* hay credencial y de dónde sale. Al volver a entrar, el campo
 * llega vacío: no hay forma de releerla desde aquí.
 *
 * La adopción es **sin reiniciar**: el servicio resuelve la credencial cada vez
 * que se inicia una conversación, así que basta con abrir una nueva en el panel
 * del asistente.
 */
export default function Modelos({ onNavegar }) {
  const { conectado, autenticado, modelos, recargarModelos } = useApp()

  const [estado, setEstado] = useState(null)
  const [error, setError] = useState(null)
  const [aviso, setAviso] = useState(null)
  const [ocupado, setOcupado] = useState(false)

  const [proveedor, setProveedor] = useState('')
  const [modelo, setModelo] = useState('')
  const [endpoint, setEndpoint] = useState('')
  const [clave, setClave] = useState('')

  // El estado llega del sondeo global; aquí se toma una foto editable.
  useEffect(() => {
    if (!modelos) return
    setEstado(modelos)
    setProveedor(modelos.proveedor ?? '')
    setModelo(modelos.modelo ?? '')
    setEndpoint(modelos.endpoint ?? '')
    setClave('')
  }, [modelos])

  const cargar = async () => {
    setError(null)
    try {
      const actual = await backend.modelos.estado()
      setEstado(actual)
      setProveedor(actual.proveedor ?? '')
      setModelo(actual.modelo ?? '')
      setEndpoint(actual.endpoint ?? '')
      setClave('')
      recargarModelos()
    } catch (fallo) {
      setError(fallo.message)
    }
  }

  const guardar = async (evento) => {
    evento.preventDefault()
    setOcupado(true)
    setAviso(null)
    setError(null)

    try {
      const nuevo = await backend.modelos.guardar({
        proveedor,
        modelo,
        endpoint,
        api_key: clave || null,
      })
      setEstado(nuevo)
      setClave('')
      setAviso(
        clave
          ? 'Conexión guardada y credencial cifrada. El asistente la usará en la próxima conversación.'
          : 'Conexión guardada.',
      )
      recargarModelos()
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  const quitarClave = async () => {
    setOcupado(true)
    setAviso(null)
    setError(null)
    try {
      const nuevo = await backend.modelos.guardar({ quitar_clave: true })
      setEstado(nuevo)
      setClave('')
      setAviso('Credencial eliminada del almacén local.')
      recargarModelos()
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  if (!conectado || !autenticado) {
    return (
      <EstadoVacio
        titulo={conectado ? 'Sesión no iniciada' : 'Sin conexión con el servicio local'}
        mensaje={
          conectado
            ? 'La conexión de modelos se guarda contra el servicio: identifícate primero.'
            : 'Revisa la franja inferior para ver el estado del servicio.'
        }
      />
    )
  }

  const proveedores = estado?.proveedores ?? []
  const descrito = proveedores.find(({ clave: valor }) => valor === proveedor)
  const tieneClave = Boolean(estado?.clave_configurada)

  return (
    <div className="flex flex-col gap-4">
      <CabeceraPagina
        titulo="Conexión de modelos"
        descripcion="Proveedor, modelo y credencial del asistente"
        acciones={
          <>
            <Pill tipo={tieneClave ? 'exito' : 'alerta'}>
              {tieneClave ? `Credencial activa (${origenLegible(estado?.origen_clave)})` : 'Sin credencial'}
            </Pill>
            <button
              type="button"
              onClick={() => onNavegar?.('chatbot')}
              className="inline-flex items-center gap-1.5 rounded-lg border border-borde px-3 py-1.5 text-etiqueta-sm transition-colors hover:border-primario hover:text-primario"
            >
              <Icono nombre="chatbot" tamano={13} />
              Ir al asistente
            </button>
          </>
        }
      />

      {aviso && (
        <Aviso tipo="exito" onCerrar={() => setAviso(null)}>
          {aviso}
        </Aviso>
      )}
      {error && <EstadoError mensaje={error} onReintentar={cargar} />}

      {!estado && !error && (
        <Panel titulo="Conexión">
          <Esqueleto variante="texto" filas={5} />
        </Panel>
      )}

      {estado && (
        <>
          <Panel titulo="Proveedor y modelo" descripcion="Solo por API: sin modelos locales">
            <form className="flex flex-col gap-4" onSubmit={guardar}>
              <label className="flex flex-col gap-1">
                <span className="text-etiqueta-sm text-texto">Proveedor</span>
                <select
                  value={proveedor}
                  onChange={(evento) => {
                    const elegido = evento.target.value
                    setProveedor(elegido)
                    const descripcion = proveedores.find(({ clave }) => clave === elegido)
                    setEndpoint(descripcion?.endpoint ?? '')
                    setModelo(descripcion?.modelos?.[0] ?? '')
                  }}
                  className="max-w-md rounded-lg border border-borde bg-fondo px-3 py-2 text-cuerpo-md outline-none focus:border-primario"
                >
                  {proveedores.map(({ clave, nombre, implementado }) => (
                    <option key={clave} value={clave}>
                      {nombre}
                      {implementado ? '' : ' — no implementado todavía'}
                    </option>
                  ))}
                </select>
                {descrito && !descrito.implementado && (
                  <span className="text-cuerpo-sm text-alerta">
                    Este proveedor queda como punto de extensión: el asistente todavía no lo
                    implementa.
                  </span>
                )}
              </label>

              <label className="flex flex-col gap-1">
                <span className="text-etiqueta-sm text-texto">Modelo</span>
                {descrito?.modelos?.length ? (
                  <select
                    value={modelo}
                    onChange={(evento) => setModelo(evento.target.value)}
                    className="max-w-md rounded-lg border border-borde bg-fondo px-3 py-2 text-cuerpo-md outline-none focus:border-primario"
                  >
                    {descrito.modelos.map((nombre) => (
                      <option key={nombre} value={nombre}>
                        {nombre}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    value={modelo}
                    onChange={(evento) => setModelo(evento.target.value)}
                    placeholder="nombre del modelo"
                    className="max-w-md rounded-lg border border-borde bg-fondo px-3 py-2 font-mono text-cuerpo-md outline-none focus:border-primario"
                  />
                )}
              </label>

              <label className="flex flex-col gap-1">
                <span className="text-etiqueta-sm text-texto">Punto de conexión</span>
                <input
                  type="url"
                  value={endpoint}
                  onChange={(evento) => setEndpoint(evento.target.value)}
                  placeholder="https://…"
                  className="max-w-md rounded-lg border border-borde bg-fondo px-3 py-2 font-mono text-cuerpo-md outline-none focus:border-primario"
                />
                <span className="text-cuerpo-sm text-tenue">
                  Se guarda como referencia del proveedor; el asistente usa el suyo propio.
                </span>
              </label>

              <label className="flex flex-col gap-1">
                <span className="flex items-center gap-2 text-etiqueta-sm text-texto">
                  Credencial de API
                  {tieneClave && <Pill tipo="exito">Ya configurada</Pill>}
                </span>
                <input
                  type="password"
                  value={clave}
                  autoComplete="off"
                  onChange={(evento) => setClave(evento.target.value)}
                  placeholder={tieneClave ? 'Escribe una nueva para reemplazarla' : 'Pega la clave del proveedor'}
                  className="max-w-md rounded-lg border border-borde bg-fondo px-3 py-2 font-mono text-cuerpo-md outline-none transition-colors focus:border-primario"
                />
                <span className="text-cuerpo-sm text-tenue">
                  La clave se cifra en el almacén local del servicio y no se vuelve a mostrar.
                </span>
              </label>

              <div className="flex flex-wrap gap-3">
                <button
                  type="submit"
                  disabled={ocupado}
                  className="inline-flex items-center gap-2 rounded-lg bg-primario px-3.5 py-2 text-etiqueta-md font-medium text-sobre-primario transition-colors hover:bg-primario-enfasis disabled:opacity-50"
                >
                  <Icono nombre="guardar" tamano={14} />
                  {ocupado ? 'Guardando…' : 'Guardar conexión'}
                </button>

                {tieneClave && estado.origen_clave === 'almacen' && (
                  <button
                    type="button"
                    onClick={quitarClave}
                    disabled={ocupado}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-peligro/40 px-3.5 py-2 text-etiqueta-md font-medium text-peligro transition-colors hover:bg-peligro/5 disabled:opacity-50"
                  >
                    <Icono nombre="basura" tamano={13} />
                    Quitar la credencial
                  </button>
                )}
              </div>
            </form>
          </Panel>

          <Panel titulo="Cómo se aplica" descripcion="Activación sin reiniciar">
            <ul className="flex flex-col gap-2 text-cuerpo-sm text-texto-2">
              <li className="flex items-start gap-2">
                <Icono nombre="refrescar" tamano={14} />
                El servicio lee la credencial cada vez que se inicia una conversación, así que un
                cambio se aplica al abrir una nueva en el panel del asistente.
              </li>
              <li className="flex items-start gap-2">
                <Icono nombre="llave" tamano={14} />
                El proveedor del entorno (<span className="font-mono">GEMINI_API_KEY</span>) tiene
                prioridad si existe: en ese caso el panel lo indica y la credencial guardada queda
                como respaldo.
              </li>
              <li className="flex items-start gap-2">
                <Icono nombre="escudo" tamano={14} />
                El streaming de respuestas y el respaldo local (Ollama) son la Fase 4: aquí no se
                configuran modelos locales.
              </li>
            </ul>
          </Panel>
        </>
      )}
    </div>
  )
}

function origenLegible(origen) {
  if (origen === 'entorno') return 'variable de entorno'
  if (origen === 'almacen') return 'almacén local'
  return 'sin origen'
}