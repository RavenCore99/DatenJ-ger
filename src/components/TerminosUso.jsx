import { useEffect, useRef, useState } from 'react'

import Icono from './Icono.jsx'
import { animar } from '../lib/movimiento.js'

/**
 * Términos y uso (calidad de vida).
 *
 * Sustituye a la nota legal que vivía incrustada en la pantalla de acceso: un
 * párrafo suelto sobre «Ley 1581 de 2012 / Hábeas Data» que no decía nada
 * completo y ocupaba sitio permanente. Ahora hay un enlace accesible que abre
 * un subpanel con lo legal del proyecto entero, y la pantalla de acceso queda
 * limpia.
 *
 * Todo lo que dice el subpanel es verificable en el repositorio: el cifrado, las
 * rondas de PBKDF2 y el destino de cada dato salen del código real
 * (`encryption.py`, `backend/services/autenticacion.py`, `database.py`), no de
 * una plantilla genérica. Lo único que sale del equipo es el texto de la
 * conversación del asistente, y se dice explícitamente.
 */
export default function TerminosUso({ className = '' }) {
  const [abierto, setAbierto] = useState(false)

  return (
    <>
      <button
        type="button"
        onClick={() => setAbierto(true)}
        className={[
          'inline-flex items-center gap-2 rounded-md px-2 py-1 text-cuerpo-sm text-primario',
          'transition-colors hover:bg-primario/5 hover:underline',
          className,
        ].join(' ')}
      >
        <Icono nombre="libro" tamano={15} />
        Términos y uso
      </button>

      {abierto && <Subpanel onCerrar={() => setAbierto(false)} />}
    </>
  )
}

function Subpanel({ onCerrar }) {
  const panel = useRef(null)
  const cerrar = useRef(null)

  // Entrada del subpanel. Si el movimiento está desactivado, `animar` no hace
  // nada y el panel ya está en su posición final: nunca se anima «hacia» la
  // visibilidad.
  useEffect(() => {
    animar(panel.current, {
      opacity: [0, 1],
      translateY: [14, 0],
      scale: [0.985, 1],
      duration: 240,
      ease: 'outQuad',
    })
  }, [])

  // Escape cierra, y el foco entra en el subpanel para que el teclado no se
  // quede detrás.
  useEffect(() => {
    const alPulsar = (evento) => {
      if (evento.key === 'Escape') onCerrar()
    }

    globalThis.addEventListener('keydown', alPulsar)
    cerrar.current?.focus()
    return () => globalThis.removeEventListener('keydown', alPulsar)
  }, [onCerrar])

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="terminos-titulo"
      className="fixed inset-0 z-50 flex items-center justify-center p-6"
    >
      {/* El fondo cierra al pulsarlo: es la salida más natural. */}
      <button
        type="button"
        aria-label="Cerrar los términos y uso"
        onClick={onCerrar}
        className="absolute inset-0 cursor-default bg-texto/40 backdrop-blur-sm"
      />

      <div
        ref={panel}
        className="superficie-cristal relative flex max-h-[80vh] w-full max-w-2xl flex-col overflow-hidden rounded-panel border border-borde shadow-flotante"
      >
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-borde px-6 py-4">
          <div className="min-w-0">
            <h2 id="terminos-titulo" className="font-marca text-titulo-sm tracking-tight">
              Términos y uso
            </h2>
            <p className="text-cuerpo-sm text-tenue">
              Cómo trata DatenJäger tus datos, y qué marco legal le aplica
            </p>
          </div>

          <button
            ref={cerrar}
            type="button"
            onClick={onCerrar}
            aria-label="Cerrar"
            className="shrink-0 rounded px-1.5 text-tenue transition-colors hover:text-texto"
          >
            <Icono nombre="cerrar" tamano={16} />
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
          <div className="flex flex-col gap-5">
            {APARTADOS.map(({ titulo, parrafos, puntos }) => (
              <section key={titulo} className="flex flex-col gap-2">
                <h3 className="text-cuerpo-md font-semibold text-primario">{titulo}</h3>

                {parrafos?.map((texto) => (
                  <p key={texto} className="text-cuerpo-sm text-texto-2">
                    {texto}
                  </p>
                ))}

                {puntos && (
                  <ul className="flex flex-col gap-1.5">
                    {puntos.map((texto) => (
                      <li key={texto} className="flex items-start gap-2 text-cuerpo-sm text-texto-2">
                        <span aria-hidden="true" className="mt-2 shrink-0 text-primario">
                          <Icono nombre="check" tamano={13} />
                        </span>
                        <span>{texto}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            ))}
          </div>
        </div>

        <footer className="flex shrink-0 items-center justify-between gap-4 border-t border-borde px-6 py-3">
          <p className="font-mono text-telemetria text-tenue">
            Ley 1581 de 2012 · Decreto 1377 de 2013
          </p>
          <button
            type="button"
            onClick={onCerrar}
            className="rounded-lg bg-primario px-3.5 py-2 text-etiqueta-md font-medium text-sobre-primario transition-colors hover:bg-primario-enfasis"
          >
            Entendido
          </button>
        </footer>
      </div>
    </div>
  )
}

/**
 * Contenido legal. Cada afirmación corresponde a algo que el sistema hace de
 * verdad; si algún día deja de ser cierto, este texto tiene que cambiar con él.
 */
const APARTADOS = [
  {
    titulo: 'Quién trata los datos y con qué marco',
    parrafos: [
      'DatenJäger es un sistema de gestión documental para pequeñas y medianas empresas del sector minero de la Villa de San Diego de Ubaté, desarrollado como trabajo de grado de la Universidad de Cundinamarca (seccional Ubaté).',
      'El tratamiento de datos personales se rige por la Ley 1581 de 2012 (régimen general de protección de datos personales, «Hábeas Data») y por el Decreto 1377 de 2013, que la reglamenta.',
    ],
  },
  {
    titulo: 'Qué datos se tratan',
    puntos: [
      'Credenciales del operador: nombre de usuario y contraseña. La contraseña nunca se guarda en claro: se almacena como derivación PBKDF2-SHA256 con 260.000 rondas y una sal por cuenta.',
      'Segundo factor: el secreto TOTP y los códigos de respaldo, guardados cifrados con AES-256-GCM.',
      'Metadatos de los documentos: nombre, descripción, titular, empresa, tamaño y fecha de carga.',
      'Registro de auditoría: qué acción se hizo, sobre qué registro y cuándo.',
    ],
  },
  {
    titulo: 'Dónde viven los datos',
    parrafos: [
      'Todo vive en este equipo. La base de datos es un archivo SQLite local y los documentos se guardan cifrados en la bóveda del propio directorio del servicio. No hay servidores intermedios ni copias en la nube.',
      'La clave de sesión se deriva de tu contraseña y no sale nunca del proceso de Python: la interfaz gráfica no la recibe en ningún momento.',
    ],
  },
  {
    titulo: 'Cómo se protegen',
    puntos: [
      'Documentos y secretos: AES-256-GCM, con la clave derivada de la contraseña del operador.',
      'Contraseña: PBKDF2-SHA256, 260.000 rondas, sal única por cuenta.',
      'Segundo factor: TOTP de 6 dígitos renovado cada 30 segundos, más códigos de respaldo de un solo uso.',
      'Equipos de confianza: los tokens se guardan cifrados en un almacén aparte, con su llave en un archivo de permisos restringidos.',
    ],
  },
  {
    titulo: 'Para qué se usan',
    parrafos: [
      'Los datos se tratan con una sola finalidad: digitalizar, cifrar, organizar y consultar la documentación de la empresa. No se usan para publicidad, no se perfilan y no se ceden ni se venden a terceros.',
    ],
  },
  {
    titulo: 'Qué sale de este equipo',
    parrafos: [
      'Nada, salvo el texto que escribes en el asistente. Al usar el chatbot, el contenido de la conversación viaja al proveedor de API que hayas configurado en «Conexión de modelos», porque es ese proveedor quien genera la respuesta. Si no configuras ninguna credencial, el asistente no envía nada.',
      'Los documentos y sus metadatos no se envían a ningún servicio externo en ninguna circunstancia.',
    ],
  },
  {
    titulo: 'Tus derechos como titular',
    puntos: [
      'Conocer, actualizar, rectificar y suprimir los datos que el sistema guarda sobre ti.',
      'Revocar la autorización de tratamiento, en los casos que la ley permite.',
      'Presentar consultas y reclamos sobre el manejo de tus datos.',
      'Solicitar prueba de la autorización otorgada.',
    ],
  },
  {
    titulo: 'Auditoría y trazabilidad',
    parrafos: [
      'Cada acción sobre el sistema queda registrada en el panel de auditoría —alta, edición, descarga, eliminación y los eventos de autenticación—, con su fecha y el operador que la realizó. Es la trazabilidad exigible para el tratamiento de datos y para el control interno de la empresa.',
    ],
  },
  {
    titulo: 'Cuánto tiempo se conservan',
    parrafos: [
      'Mientras exista la bóveda. El sistema no borra datos por su cuenta ni por vencimiento: la conservación y la supresión dependen de quien administra la instalación, que es también el responsable del tratamiento.',
    ],
  },
]