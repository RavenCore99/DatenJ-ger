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
 * Panel de conexión de APIs y modelos (SCRUM-64 / SCRUM-62).
 *
 * **El usuario solo pega su clave.** De su forma se deduce el proveedor —Gemini
 * empieza por `AIza` o `AQ`, NVIDIA lleva `nvapi-`— y del proveedor salen la URL
 * base y la variable de entorno. Nadie tiene que saber que NVIDIA vive en
 * `integrate.api.nvidia.com/v1`: el punto de conexión se muestra, no se pide.
 * Solo el proveedor «compatible con OpenAI» necesita una URL escrita, porque es,
 * por definición, el que no conocemos.
 *
 * **La clave no pasa por el renderer.** Se envía al backend, que la cifra con
 * AES-256-GCM en su almacén local (`modelos/`, 0600/0700) y la deja además en el
 * `.env` del proyecto (0600), que es de donde la lee el asistente. Al volver a
 * entrar, el campo llega vacío: no hay forma de releerla desde aquí.
 *
 * **El estado no se supone.** Tener una credencial guardada no es tener una
 * conexión que funcione: la clave puede ser de otro proveedor y no servir para
 * nada. Por eso el panel distingue «sin credencial», «sin verificar» y el
 * resultado de la última prueba real —la de conexión y la de generación—, y ese
 * mismo estado es el que pinta la franja de telemetría.
 *
 * La adopción es **sin reiniciar**: el servicio resuelve la credencial cada vez
 * que se inicia una conversación, así que basta con abrir una nueva en el panel
 * del asistente.
 */
export default function Modelos({ onNavegar, nivelTitulo = 1 }) {
  const { conectado, autenticado, modelos, recargarModelos } = useApp()

  const [estado, setEstado] = useState(null)
  const [error, setError] = useState(null)
  const [aviso, setAviso] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  // Resultado de la prueba real contra el proveedor.
  const [prueba, setPrueba] = useState(null)
  const [probando, setProbando] = useState(false)
  // Resultado de la prueba de **generación**: que el modelo responda, no solo
  // que la credencial exista (SCRUM-62).
  const [respuestaPrueba, setRespuestaPrueba] = useState(null)
  const [probandoRespuesta, setProbandoRespuesta] = useState(false)

  const [proveedor, setProveedor] = useState('')
  const [modelo, setModelo] = useState('')
  const [endpoint, setEndpoint] = useState('')
  const [clave, setClave] = useState('')
  // Lo que el backend reconoce en la clave que se está escribiendo, antes de
  // guardarla. `null` mientras no se ha reconocido nada.
  const [detectado, setDetectado] = useState(null)

  // El estado llega del sondeo global; aquí se toma una foto editable.
  useEffect(() => {
    if (!modelos) return
    setEstado(modelos)
    setProveedor(modelos.proveedor ?? '')
    setModelo(modelos.modelo ?? '')
    setEndpoint(modelos.endpoint ?? '')
    setClave('')
  }, [modelos])

  // Reconocimiento en vivo: en cuanto se pega una clave, se pregunta al backend
  // a qué proveedor pertenece. Así el usuario ve «reconocida: NVIDIA NIM» antes
  // de guardar nada, en vez de descubrirlo cuando ya falló.
  useEffect(() => {
    const limpia = clave.trim()
    if (limpia.length < 8) {
      setDetectado(null)
      return undefined
    }
    let vigente = true
    const temporizador = setTimeout(async () => {
      try {
        const reconocido = await backend.modelos.identificar(limpia)
        if (vigente) setDetectado(reconocido)
      } catch {
        // Un fallo al reconocer no debe interrumpir la escritura: siempre se
        // puede guardar igual y elegir el proveedor a mano.
        if (vigente) setDetectado(null)
      }
    }, 450)
    return () => {
      vigente = false
      clearTimeout(temporizador)
    }
  }, [clave])

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
        // El proveedor solo se envía si la detección no reconoció la clave: si
        // la reconoce, manda ella y el usuario no puede equivocarse de opción.
        proveedor: detectado?.detectado ? null : proveedor || null,
        modelo,
        // La URL base solo se envía cuando hay que escribirla (endpoint propio).
        // Con un proveedor conocido la fija el catálogo, y mandar la que hubiera
        // en pantalla la pisaría sin motivo.
        endpoint: endpointEditable ? endpoint || null : null,
        api_key: clave || null,
      })
      setEstado(nuevo)
      setClave('')
      setDetectado(null)
      setAviso(
        clave
          ? 'Credencial guardada y cifrada, y dejada en el .env del proyecto. Pulsa «Probar conexión» para saber si sirve.'
          : 'Conexión guardada.',
      )
      recargarModelos()
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  /**
   * Prueba la credencial contra el proveedor antes de usarla. La petición la
   * hace el backend —el renderer nunca ve la clave— y devuelve lo que el
   * proveedor responda de verdad. El resultado queda anotado en el servicio, así
   * que la franja de telemetría deja de suponer.
   */
  const probarConexion = async () => {
    setProbando(true)
    setPrueba(null)
    setError(null)

    try {
      setPrueba(await backend.modelos.probar())
      await cargar()
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setProbando(false)
    }
  }

  /**
   * Prueba de extremo a extremo (SCRUM-62): pide al modelo una respuesta de
   * verdad. Es lo que demuestra que el asistente funciona —listar modelos solo
   * prueba que la credencial existe—.
   */
  const probarRespuesta = async () => {
    setProbandoRespuesta(true)
    setRespuestaPrueba(null)
    setError(null)

    try {
      setRespuestaPrueba(await backend.chat.probar())
      await cargar()
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setProbandoRespuesta(false)
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
      setDetectado(null)
      setAviso('Credencial eliminada del almacén local y del .env.')
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
  const tieneClave = Boolean(estado?.clave_configurada)
  const salud = estado?.salud ?? 'sin_configurar'

  // Lo que se muestra en «Proveedor» y «Punto de conexión»: lo reconocido en la
  // clave que se está escribiendo manda sobre lo guardado, porque es lo que
  // ocurrirá si se guarda.
  const proveedorVisible = detectado?.detectado ? detectado.proveedor : proveedor
  const endpointVisible = detectado?.detectado ? detectado.endpoint : endpoint
  const fichaVisible = proveedores.find(({ clave: valor }) => valor === proveedorVisible)
  const endpointEditable = Boolean(fichaVisible?.endpoint_editable)

  // Modelos que se ofrecen: los del catálogo del proveedor, los que la cuenta
  // tiene de verdad —de la última prueba de conexión— y lo que ya esté elegido.
  const modelosOfrecidos = [
    ...new Set([
      ...(fichaVisible?.modelos ?? []),
      ...(estado?.modelos_conocidos ?? []),
      ...(prueba?.modelos_disponibles ?? []),
      ...(modelo ? [modelo] : []),
    ]),
  ]

  return (
    <div className="flex flex-col gap-4">
      <CabeceraPagina
        nivel={nivelTitulo}
        titulo="Conexión de modelos"
        descripcion="Proveedor, modelo y credencial del asistente"
        acciones={
          <>
            <Pill tipo={TIPO_PILL[salud] ?? 'alerta'}>
              {ETIQUETA_SALUD[salud] ?? 'Sin credencial'}
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

      {estado?.permisos_env_corregidos && (
        <Aviso tipo="exito" onCerrar={() => setAviso(null)}>
          El archivo <span className="font-mono">.env</span> estaba legible por otros usuarios y se
          ha dejado en <span className="font-mono">0600</span>: contiene la credencial en claro.
        </Aviso>
      )}

      {!estado && !error && (
        <Panel titulo="Conexión">
          <Esqueleto variante="texto" filas={5} />
        </Panel>
      )}

      {estado && (
        <>
          <Panel
            titulo="Credencial de API"
            descripcion="Pega solo la clave: el proveedor y la URL base se deducen"
          >
            <form className="flex flex-col gap-4" onSubmit={guardar}>
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
                  placeholder={
                    tieneClave ? 'Escribe una nueva para reemplazarla' : 'Pega aquí tu clave de API'
                  }
                  className="max-w-md rounded-lg border border-borde bg-fondo px-3 py-2 font-mono text-cuerpo-md outline-none transition-colors focus:border-primario"
                />
                <span className="text-cuerpo-sm text-tenue">
                  Se cifra en el almacén local del servicio, se deja en el{' '}
                  <span className="font-mono">.env</span> del proyecto y no se vuelve a mostrar.
                </span>
              </label>

              {/* Reconocimiento en vivo: la clave se identifica antes de guardarla. */}
              {clave.trim().length >= 8 && (
                <div
                  role="status"
                  className={[
                    'flex flex-col gap-1 rounded-lg border px-3.5 py-3 text-cuerpo-sm',
                    detectado?.detectado
                      ? 'border-exito/40 bg-exito/5'
                      : 'border-alerta/40 bg-alerta/5',
                  ].join(' ')}
                >
                  {detectado?.detectado ? (
                    <>
                      <p className="font-medium text-exito">Reconocida: {detectado.nombre}</p>
                      <p className="text-texto-2">
                        Punto de conexión: <span className="font-mono">{detectado.endpoint}</span>
                      </p>
                      <p className="text-tenue">
                        Se guardará en{' '}
                        <span className="font-mono">{detectado.variable_entorno}</span>.
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="font-medium text-alerta">
                        Esta clave no sigue el formato de ningún proveedor conocido.
                      </p>
                      <p className="text-tenue">
                        Elige el proveedor a mano más abajo. Formatos: {FORMATOS}
                      </p>
                    </>
                  )}
                </div>
              )}

              {/* Solo se pide lo que no se puede deducir. */}
              {(!detectado?.detectado || endpointEditable) && (
                <label className="flex flex-col gap-1">
                  <span className="text-etiqueta-sm text-texto">Proveedor</span>
                  <select
                    value={proveedor}
                    onChange={(evento) => {
                      const elegido = evento.target.value
                      setProveedor(elegido)
                      const descripcion = proveedores.find(({ clave: valor }) => valor === elegido)
                      setEndpoint(descripcion?.endpoint ?? '')
                      if (!modelo) setModelo(descripcion?.modelos?.[0] ?? '')
                    }}
                    className="max-w-md rounded-lg border border-borde bg-fondo px-3 py-2 text-cuerpo-md outline-none focus:border-primario"
                  >
                    {proveedores.map(({ clave: valor, nombre }) => (
                      <option key={valor} value={valor}>
                        {nombre}
                      </option>
                    ))}
                  </select>
                  {fichaVisible?.identificador && (
                    <span className="text-cuerpo-sm text-tenue">
                      Su clave {fichaVisible.identificador.toLowerCase()}.
                    </span>
                  )}
                </label>
              )}

              <label className="flex flex-col gap-1">
                <span className="text-etiqueta-sm text-texto">Punto de conexión</span>
                <input
                  type="url"
                  value={endpointVisible}
                  readOnly={!endpointEditable}
                  onChange={(evento) => setEndpoint(evento.target.value)}
                  placeholder="https://…"
                  className={[
                    'max-w-md rounded-lg border px-3 py-2 font-mono text-cuerpo-md outline-none',
                    endpointEditable
                      ? 'border-borde bg-fondo focus:border-primario'
                      : 'border-borde bg-superficie text-tenue',
                  ].join(' ')}
                />
                <span className="text-cuerpo-sm text-tenue">
                  {endpointEditable
                    ? 'Tu endpoint no es de ningún proveedor conocido: aquí sí hay que escribirlo.'
                    : 'Lo fija el proveedor. No hace falta escribirlo ni recordarlo.'}
                </span>
              </label>

              <label className="flex flex-col gap-1">
                <span className="text-etiqueta-sm text-texto">Modelo</span>
                {modelosOfrecidos.length ? (
                  <select
                    value={modelo}
                    onChange={(evento) => setModelo(evento.target.value)}
                    className="max-w-md rounded-lg border border-borde bg-fondo px-3 py-2 font-mono text-cuerpo-md outline-none focus:border-primario"
                  >
                    {modelosOfrecidos.map((nombre) => (
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
                <span className="text-cuerpo-sm text-tenue">
                  Los alias <span className="font-mono">-latest</span> no caducan; una versión fija
                  se retira y deja de responder. Tras probar la conexión aparecen aquí los modelos
                  que tu cuenta tiene de verdad.
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

                {tieneClave && (
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

                <button
                  type="button"
                  onClick={probarConexion}
                  disabled={probando || !tieneClave}
                  title={
                    tieneClave
                      ? 'Hace una petición real al proveedor con la credencial guardada'
                      : 'Guarda una credencial antes de probarla'
                  }
                  className="inline-flex items-center gap-1.5 rounded-lg border border-borde px-3.5 py-2 text-etiqueta-md font-medium transition-colors hover:border-primario hover:text-primario disabled:opacity-50"
                >
                  <Icono
                    nombre="refrescar"
                    tamano={14}
                    className={probando ? 'animate-spin' : ''}
                  />
                  {probando ? 'Probando…' : 'Probar conexión'}
                </button>

                <button
                  type="button"
                  onClick={probarRespuesta}
                  disabled={probandoRespuesta || !tieneClave}
                  title={
                    tieneClave
                      ? 'Pide al modelo una respuesta de verdad: es lo que prueba que el asistente funciona'
                      : 'Guarda una credencial antes de probarla'
                  }
                  className="inline-flex items-center gap-1.5 rounded-lg border border-borde px-3.5 py-2 text-etiqueta-md font-medium transition-colors hover:border-primario hover:text-primario disabled:opacity-50"
                >
                  <Icono
                    nombre="chispa"
                    tamano={14}
                    className={probandoRespuesta ? 'animate-pulse' : ''}
                  />
                  {probandoRespuesta ? 'Generando…' : 'Probar respuesta'}
                </button>
              </div>

              {prueba && (
                <div
                  role="status"
                  className={[
                    'flex flex-col gap-1 rounded-lg border px-3.5 py-3 text-cuerpo-sm',
                    prueba.ok
                      ? 'border-exito/40 bg-exito/5 text-exito'
                      : 'border-peligro/40 bg-peligro/5 text-peligro',
                  ].join(' ')}
                >
                  <p className="font-medium">{prueba.mensaje}</p>
                  {prueba.detalle && (
                    <p className="break-all font-mono text-codigo text-texto-2">{prueba.detalle}</p>
                  )}
                  {prueba.modelos_disponibles?.length > 0 && (
                    <p className="text-tenue">
                      {prueba.modelos_disponibles.length} modelo(s) disponibles en la cuenta, entre
                      ellos <span className="font-mono">{prueba.modelos_disponibles[0]}</span>.
                    </p>
                  )}
                </div>
              )}

              {respuestaPrueba && (
                <div
                  role="status"
                  className={[
                    'flex flex-col gap-1.5 rounded-lg border px-3.5 py-3 text-cuerpo-sm',
                    respuestaPrueba.ok
                      ? 'border-exito/40 bg-exito/5 text-exito'
                      : 'border-peligro/40 bg-peligro/5 text-peligro',
                  ].join(' ')}
                >
                  <p className="font-medium">{respuestaPrueba.mensaje}</p>
                  {respuestaPrueba.modelo && (
                    <p className="text-tenue">
                      Modelo que respondió:{' '}
                      <span className="font-mono">{respuestaPrueba.modelo}</span>
                    </p>
                  )}
                  {respuestaPrueba.respuesta && (
                    <p className="rounded-lg border border-borde bg-fondo px-3 py-2 text-texto">
                      {respuestaPrueba.respuesta}
                    </p>
                  )}
                  {respuestaPrueba.detalle && (
                    <p className="break-all font-mono text-codigo text-texto-2">
                      {respuestaPrueba.detalle}
                    </p>
                  )}
                </div>
              )}
            </form>
          </Panel>

          <Panel titulo="Estado de la conexión" descripcion="Lo que muestra la franja de telemetría">
            <div className="flex flex-col gap-3 text-cuerpo-sm">
              <p className="flex items-start gap-2 text-texto-2">
                <span
                  className={`mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full ${PUNTO[salud]}`}
                />
                <span>
                  <strong>{ETIQUETA_SALUD[salud]}</strong>.{' '}
                  {estado.ultima_prueba ? (
                    <>
                      Última prueba (
                      {TIPO_PRUEBA[estado.ultima_prueba.tipo] ?? estado.ultima_prueba.tipo}), el{' '}
                      {String(estado.ultima_prueba.momento).replace('T', ' a las ')}:{' '}
                      {estado.ultima_prueba.mensaje}
                    </>
                  ) : tieneClave ? (
                    'Hay credencial guardada, pero no se ha probado todavía: el verde solo lo pone una prueba real.'
                  ) : (
                    'Sin credencial: el asistente no puede conversar.'
                  )}
                </span>
              </p>
              {estado.modelos_conocidos?.length > 0 && (
                <p className="text-tenue">
                  {estado.modelos_conocidos.length} modelo(s) de tu cuenta conocidos por la última
                  prueba de conexión.
                </p>
              )}
            </div>
          </Panel>

          <Panel titulo="Cómo se aplica" descripcion="Activación sin reiniciar">
            <ul className="flex flex-col gap-2 text-cuerpo-sm text-texto-2">
              <li className="flex items-start gap-2">
                <Icono nombre="guardar" tamano={14} />
                Al guardar, la credencial se cifra en el almacén local y se deja también en el{' '}
                <span className="font-mono">.env</span> del proyecto (permisos{' '}
                <span className="font-mono">0600</span>), que es de donde la lee el asistente. Se
                aplica al abrir una conversación nueva, sin reiniciar.
              </li>
              <li className="flex items-start gap-2">
                <Icono nombre="basura" tamano={14} />
                «Quitar la credencial» la retira de los dos sitios. Si solo se quitara del almacén,
                el <span className="font-mono">.env</span> seguiría sirviendo la clave anterior y el
                panel diría que hay credencial.
              </li>
              <li className="flex items-start gap-2">
                <Icono nombre="refrescar" tamano={14} />
                «Probar conexión» hace una petición real al proveedor. Deja además la lista de
                modelos de tu cuenta, que pasa a ser el respaldo del modelo elegido: si el tuyo se
                retiró, el asistente cae en uno que existe en vez de devolver un error.
              </li>
              <li className="flex items-start gap-2">
                <Icono nombre="chispa" tamano={14} />
                «Probar respuesta» va más allá: pide al modelo una respuesta de verdad. Listar
                modelos prueba que la credencial existe; esto prueba que el asistente genera texto.
              </li>
              <li className="flex items-start gap-2">
                <Icono nombre="escudo" tamano={14} />
                El asistente responde <strong>solo sobre este proyecto</strong> y con las cifras
                reales del sistema. Nunca recibe datos personales, contenido de documentos ni
                secretos, así que no puede filtrarlos.
              </li>
            </ul>
          </Panel>
        </>
      )}
    </div>
  )
}

/** Salud de la conexión → cómo se pinta. Ningún verde sin una prueba detrás. */
const TIPO_PILL = {
  ok: 'exito',
  error: 'peligro',
  sin_verificar: 'alerta',
  sin_configurar: 'alerta',
}

const ETIQUETA_SALUD = {
  ok: 'Verificada',
  error: 'La última prueba falló',
  sin_verificar: 'Sin verificar',
  sin_configurar: 'Sin credencial',
}

const PUNTO = {
  ok: 'bg-exito',
  error: 'bg-peligro',
  sin_verificar: 'bg-alerta',
  sin_configurar: 'bg-borde-fuerte',
}

const TIPO_PRUEBA = {
  conexion: 'conexión',
  respuesta: 'generación',
}

const FORMATOS = 'Google «AIza»/«AQ», NVIDIA «nvapi-», OpenRouter «sk-or-», OpenAI «sk-».'