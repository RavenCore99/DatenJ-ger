import { useApp } from '../estado/ProveedorApp.jsx'

/**
 * Franja de telemetría inferior (SCRUM-28; iconos en SCRUM-65; estado con color
 * de las piezas del sistema en SCRUM-68).
 *
 * **Simplificada por hallazgo de Raven.** Antes cargaba con la dirección del
 * servicio (`http://127.0.0.1:8756`), el `servicio v1.0` del backend, la
 * insignia de cifrado y el texto «Servicio local conectado»: datos de depuración
 * que no aportan nada en el pie y competían con lo importante. Aquí quedan solo
 * las tres piezas cuyo estado importa —**BD**, **APIs** y **Chatbot**, cada una
 * con su punto de color— y, a la derecha, la versión del proyecto con el hash
 * del build. La versión sale de `package.json` (v2.1, la rama vigente).
 *
 * **Tres colores, un solo significado** (hallazgo de Raven): el punto no decora,
 * informa de la conexión **real**. Verde es óptimo (una comprobación real pasó),
 * amarillo es una conexión por confirmar —credencial guardada sin probar, o
 * comprobación en curso— y rojo es no conectado o fallando. El gris queda para
 * lo que todavía no tiene credencial: pintarlo de rojo alarmaría sin motivo.
 *
 * El detalle de **qué** se está midiendo viaja en el `title`, no en el texto del
 * pie: un punto de color con la etiqueta basta.
 */
export default function BarraEstado() {
  const { sesion, autenticado, componentes } = useApp()

  return (
    <footer className="flex h-telemetria shrink-0 items-center justify-between gap-4 border-t border-borde bg-superficie px-4 font-mono text-telemetria text-tenue">
      <div className="flex min-w-0 items-center gap-3">
        <ChipEstado
          etiqueta="BD"
          estado={componentes.baseDatos}
          detalle="Verde cuando una lectura real de la base responde (un conteo de documentos), no porque el servicio esté vivo. Rojo si la base no responde."
        />

        <Filete />

        <ChipEstado
          etiqueta="APIs"
          estado={componentes.apis}
          detalle="Verde solo si la última prueba real de conexión pasó. Amarillo si hay credencial guardada sin probar; rojo si la prueba falló; gris si aún no hay credencial."
        />

        <Filete />

        <ChipEstado
          etiqueta="Chatbot"
          estado={componentes.chatbot}
          detalle="El asistente usa la misma credencial que las APIs. Verde solo si la última prueba de generación respondió; tener la clave guardada no basta."
        />

        <Filete />

        <span className="truncate">
          {autenticado ? `sesión: ${sesion?.usuario_nombre ?? 'activa'}` : 'sin sesión'}
        </span>
      </div>

      <div className="flex shrink-0 items-center gap-3">
        <span className="text-primario">
          v{__VERSION__} ({__HASH__})
        </span>
      </div>
    </footer>
  )
}

/**
 * Punto de color por estado de una pieza del sistema (SCRUM-68).
 *
 * `ok` verde · `sin_verificar`/`verificando` amarillo · `error` rojo ·
 * `sin_configurar` gris neutro. Los estados desconocidos caen en gris para no
 * inventar una alarma.
 */
const PUNTO = {
  ok: 'bg-exito',
  verificando: 'bg-alerta',
  sin_verificar: 'bg-alerta',
  error: 'bg-peligro',
  sin_configurar: 'bg-borde-fuerte',
}

const LEYENDA = {
  ok: 'conexión óptima',
  verificando: 'comprobando',
  sin_verificar: 'sin verificar',
  error: 'no conectado',
  sin_configurar: 'sin configurar',
}

function Filete() {
  return <span aria-hidden="true" className="h-3 w-px shrink-0 bg-borde" />
}

/**
 * Pieza del sistema: punto de color **y** su nombre. El color dice el estado; el
 * `title` explica qué se mide, para que «verde» no obligue a adivinar si
 * significa conectado, configurado o probado.
 */
function ChipEstado({ etiqueta, estado, detalle }) {
  return (
    <span className="flex shrink-0 items-center gap-1.5" title={`${etiqueta}: ${detalle}`}>
      <span
        aria-hidden="true"
        className={`inline-block h-1.5 w-1.5 rounded-full ${PUNTO[estado] ?? 'bg-borde-fuerte'}`}
      />
      <span className="text-texto-2">{etiqueta}</span>
      <span className="sr-only">{LEYENDA[estado] ?? estado}</span>
    </span>
  )
}
