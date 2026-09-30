import { useCallback, useEffect, useRef, useState } from 'react'

import Panel, { CabeceraPagina, EstadoError, EstadoVacio, Esqueleto, Pill } from '../components/Panel.jsx'
import Icono from '../components/Icono.jsx'
import { useApp } from '../estado/ProveedorApp.jsx'
import { backend } from '../lib/api.js'

/**
 * Panel del asistente (SCRUM-59), con la barra lateral de botones del mockup.
 *
 * El servicio del chatbot ya existía (`chatbot.py`, expuesto por el puente en
 * SCRUM-21) y el backend recuerda la conversación por sesión: esta pantalla es
 * la que faltaba para poder usarlo. Las acciones de la izquierda son atajos que
 * escriben el mensaje por ti; la conversación vive a la derecha.
 *
 * La respuesta sigue siendo **bloqueante** —el streaming es RF-16 y llega en
 * la Fase 4—, así que se muestra un estado de espera explícito mientras el
 * modelo contesta. El chatbot funciona **solo por API**: si no hay credencial
 * configurada, se dice con esas palabras y se enlaza al panel de conexión.
 */
const ACCIONES = [
  {
    clave: 'resumen',
    titulo: 'Resumir el archivo',
    descripcion: 'Cuántos documentos hay y de qué empresas',
    icono: 'grafico',
    mensaje: 'Hazme un resumen del archivo documental: cuántos documentos hay y cómo se reparten por empresa.',
  },
  {
    clave: 'buscar',
    titulo: 'Cómo buscar',
    descripcion: 'Filtros del panel documental',
    icono: 'buscar',
    mensaje: '¿Cómo puedo encontrar un documento concreto dentro del sistema?',
  },
  {
    clave: 'seguridad',
    titulo: 'Cifrado y auditoría',
    descripcion: 'Qué protege el sistema',
    icono: 'escudo',
    mensaje: 'Explícame cómo protege DatenJäger los documentos y qué queda registrado en la auditoría.',
  },
  {
    clave: '2fa',
    titulo: 'Doble factor',
    descripcion: 'Códigos y respaldo',
    icono: 'llave',
    mensaje: '¿Cómo funciona el doble factor y para qué sirven los códigos de respaldo?',
  },
]

export default function Chatbot({ onNavegar }) {
  const { conectado, autenticado, componentes } = useApp()

  const [mensajes, setMensajes] = useState([])
  const [texto, setTexto] = useState('')
  const [estado, setEstado] = useState('inactivo') // inactivo | cargando | listo | esperando | error
  const [error, setError] = useState(null)
  const finDeLista = useRef(null)

  const hayCredencial = componentes.chatbot === 'ok'

  const iniciar = useCallback(async () => {
    setEstado('cargando')
    setError(null)
    try {
      const conversacion = await backend.chat.iniciar()
      setMensajes((conversacion?.mensajes ?? []).map(aMensaje))
      setEstado('listo')
    } catch (fallo) {
      setError(fallo.message)
      setEstado('error')
    }
  }, [])

  useEffect(() => {
    if (!conectado || !autenticado) return
    iniciar()
  }, [conectado, autenticado, iniciar])

  // El scroll baja solo cuando llega un mensaje nuevo, como en el mockup.
  useEffect(() => {
    finDeLista.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [mensajes, estado])

  const enviar = useCallback(
    async (contenido) => {
      const limpio = contenido.trim()
      if (!limpio || estado === 'esperando') return

      setTexto('')
      setMensajes((actuales) => [...actuales, { autor: 'usuario', texto: limpio }])
      setEstado('esperando')
      setError(null)

      try {
        const respuesta = await backend.chat.enviar(limpio)
        setMensajes((actuales) => [...actuales, { autor: 'modelo', texto: respuesta.respuesta }])
        setEstado('listo')
      } catch (fallo) {
        setError(fallo.message)
        setEstado('error')
      }
    },
    [estado],
  )

  const limpiar = useCallback(async () => {
    try {
      await backend.chat.limpiar()
    } catch {
      /* si el servicio no responde, la pantalla se vacía igual */
    }
    setMensajes([])
    setEstado('listo')
    setError(null)
  }, [])

  if (!conectado || !autenticado) {
    return (
      <EstadoVacio
        titulo={conectado ? 'Sesión no iniciada' : 'Sin conexión con el servicio local'}
        mensaje={
          conectado
            ? 'Vuelve a la pantalla de acceso para identificarte.'
            : 'El asistente se consulta contra el servicio de Python. Revisa la franja inferior.'
        }
      />
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <CabeceraPagina
        titulo="Asistente"
        descripcion="Conversación con el modelo configurado"
        acciones={
          <>
            <Pill tipo={hayCredencial ? 'exito' : 'alerta'}>
              {hayCredencial ? 'Modelo conectado' : 'Sin credencial'}
            </Pill>
            <button
              type="button"
              onClick={limpiar}
              disabled={mensajes.length === 0}
              className="rounded-lg border border-borde px-3 py-1.5 text-etiqueta-sm transition-colors hover:border-primario hover:text-primario disabled:opacity-50"
            >
              Nueva conversación
            </button>
          </>
        }
      />

      {!hayCredencial && (
        <Panel>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-cuerpo-sm text-tenue">
              No hay credencial de modelo configurada. El asistente funciona <strong>solo por
              API</strong>: carga la clave y el modelo en el panel de conexión.
            </p>
            <button
              type="button"
              onClick={() => onNavegar?.('modelos')}
              className="inline-flex items-center gap-2 rounded-lg border border-borde px-3 py-1.5 text-etiqueta-sm transition-colors hover:border-primario hover:text-primario"
            >
              <Icono nombre="globo" tamano={14} />
              Abrir conexión de modelos
            </button>
          </div>
        </Panel>
      )}

      <div className="flex min-h-[28rem] items-stretch gap-4">
        {/* Barra lateral por botones (SCRUM-59): atajos, no decoración. */}
        <nav
          aria-label="Acciones del asistente"
          className="flex w-64 shrink-0 flex-col gap-1.5 rounded-panel border border-borde bg-superficie p-2"
        >
          <p className="px-2 py-1 text-etiqueta-sm uppercase tracking-wider text-tenue">
            Consultas rápidas
          </p>
          {ACCIONES.map(({ clave, titulo, descripcion, icono, mensaje }) => (
            <button
              key={clave}
              type="button"
              onClick={() => enviar(mensaje)}
              disabled={estado === 'esperando'}
              className="flex items-start gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors hover:bg-fondo-2 disabled:opacity-50"
            >
              <span className="mt-0.5 text-primario">
                <Icono nombre={icono} tamano={16} />
              </span>
              <span className="min-w-0">
                <span className="block text-etiqueta-md font-medium">{titulo}</span>
                <span className="block text-cuerpo-sm text-tenue">{descripcion}</span>
              </span>
            </button>
          ))}
        </nav>

        <section className="flex min-w-0 flex-1 flex-col rounded-panel border border-borde bg-superficie">
          <header className="flex items-center gap-2 border-b border-borde px-4 py-3">
            <span className="flex h-7 w-7 items-center justify-center rounded-full border border-primario/40 bg-primario/5 text-primario">
              <Icono nombre="chatbot" tamano={15} />
            </span>
            <div className="min-w-0 leading-tight">
              <p className="text-etiqueta-md font-medium">Hermes IA</p>
              <p className="text-cuerpo-sm text-tenue">
                Respuesta completa, sin streaming (RF-16 llega en la Fase 4)
              </p>
            </div>
          </header>

          <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4 py-4">
            {estado === 'cargando' && <Esqueleto variante="texto" filas={4} />}

            {estado !== 'cargando' && mensajes.length === 0 && (
              <EstadoVacio
                icono="chatbot"
                titulo="Sin conversación todavía"
                mensaje="Escribe abajo o usa una de las consultas rápidas de la izquierda."
              />
            )}

            {mensajes.map((mensaje, indice) => (
              <Burbuja key={`${mensaje.role}-${indice}`} mensaje={mensaje} />
            ))}

            {estado === 'esperando' && (
              <div className="flex items-center gap-2 text-cuerpo-sm text-tenue" aria-live="polite">
                <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-primario" />
                El modelo está respondiendo…
              </div>
            )}

            {estado === 'error' && <EstadoError mensaje={error} onReintentar={iniciar} />}

            <div ref={finDeLista} />
          </div>

          <form
            className="flex items-end gap-2 border-t border-borde px-4 py-3"
            onSubmit={(evento) => {
              evento.preventDefault()
              enviar(texto)
            }}
          >
            <label className="min-w-0 flex-1">
              <span className="sr-only">Mensaje para el asistente</span>
              <textarea
                value={texto}
                rows={2}
                onChange={(evento) => setTexto(evento.target.value)}
                onKeyDown={(evento) => {
                  if (evento.key === 'Enter' && !evento.shiftKey) {
                    evento.preventDefault()
                    enviar(texto)
                  }
                }}
                placeholder="Escribe tu consulta… (Enter para enviar, Mayús+Enter para salto de línea)"
                className="w-full resize-none rounded-lg border border-borde bg-fondo px-3 py-2 text-cuerpo-md outline-none transition-colors focus:border-primario"
              />
            </label>
            <button
              type="submit"
              disabled={estado === 'esperando' || !texto.trim()}
              className="inline-flex items-center gap-2 rounded-lg bg-primario px-3.5 py-2.5 text-etiqueta-md font-medium text-sobre-primario transition-colors hover:bg-primario-enfasis disabled:opacity-50"
            >
              <Icono nombre="flecha-derecha" tamano={15} />
              Enviar
            </button>
          </form>
        </section>
      </div>
    </div>
  )
}

function Burbuja({ mensaje }) {
  const esUsuario = mensaje.autor === 'usuario'
  const esFallo = !esUsuario && /^\[(Error|Gemini)/.test(mensaje.texto)

  return (
    <div className={`animar-entrada flex ${esUsuario ? 'justify-end' : 'justify-start'}`}>
      <div
        className={[
          'max-w-[46rem] whitespace-pre-wrap rounded-panel px-3.5 py-2.5 text-cuerpo-md',
          esUsuario
            ? 'bg-primario text-sobre-primario'
            : esFallo
              ? 'border border-peligro/40 bg-peligro/5 text-peligro'
              : 'border border-borde bg-fondo text-texto',
        ].join(' ')}
      >
        {mensaje.texto}
      </div>
    </div>
  )
}

/**
 * El historial del backend guarda los turnos en el formato de Gemini
 * (`{role, parts:[{text}]}`). Aquí se traduce al de la pantalla, sin tocar el
 * servicio ni su formato.
 */
function aMensaje(entrada) {
  const texto = (entrada?.parts ?? []).map((parte) => parte.text ?? '').join('')
  return { autor: entrada?.role === 'user' ? 'usuario' : 'modelo', texto }
}