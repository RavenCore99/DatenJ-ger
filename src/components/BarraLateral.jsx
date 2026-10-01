import { useApp } from '../estado/ProveedorApp.jsx'
import { SECCIONES } from '../App.jsx'
import Icono from './Icono.jsx'
import logo from '../../assets/logo/logo.png'

/**
 * Barra lateral de navegación (SCRUM-28, iconos en SCRUM-65).
 *
 * Ancho del sistema de diseño: `240px`, que se recoge a `64px` cuando el
 * usuario la pliega. Cada sección ocupa `36px` de alto, como pide el spec, y
 * lleva el icono del set del sistema; plegada, el icono es el único distintivo
 * y el título viaja en el atributo accesible.
 *
 * **El logo es el control de plegado** (calidad de vida): había dos botones
 * para lo mismo —uno aquí y otro en la sub-cabecera—, así que se retiraron
 * ambos y el gesto quedó donde el usuario lo busca: sobre la marca. El atajo
 * `Ctrl/⌘+B` sigue funcionando y se anuncia en el `title` y en
 * `aria-keyshortcuts`.
 *
 * **Ajustes vive al pie, junto al tema**: no es una sección de trabajo como las
 * demás —no se entra a ella para operar sobre documentos—, sino el lugar donde
 * se configura la aplicación. Bajarla al pie, pegada al conmutador de tema, la
 * separa del flujo y la deja donde se espera.
 */
export default function BarraLateral({ seccion, onSeleccionar, plegada, onPlegar }) {
  const ajustes = SECCIONES.find(({ clave }) => clave === 'cuenta')
  const principales = SECCIONES.filter(({ clave }) => clave !== 'cuenta')

  return (
    <nav
      aria-label="Secciones del sistema"
      className={[
        'flex shrink-0 flex-col border-r border-borde bg-superficie',
        'transition-[width] duration-200 ease-out',
        plegada ? 'w-lateral-min' : 'w-lateral',
      ].join(' ')}
    >
      <div className="flex h-cabecera shrink-0 items-center border-b border-borde px-3">
        <button
          type="button"
          onClick={onPlegar}
          aria-expanded={!plegada}
          aria-keyshortcuts="Control+B"
          aria-label={plegada ? 'Desplegar la barra lateral' : 'Recoger la barra lateral'}
          title={`${plegada ? 'Desplegar' : 'Recoger'} la barra lateral (Ctrl+B)`}
          className="group flex min-w-0 items-center gap-2 rounded-md text-left outline-none focus-visible:ring-2 focus-visible:ring-primario"
        >
          <img
            src={logo}
            alt=""
            className="h-8 w-8 shrink-0 rounded-full object-contain ring-2 ring-transparent transition-all duration-200 group-hover:ring-primario/40"
          />

          {!plegada && (
            <span className="min-w-0 leading-tight">
              <span className="block truncate font-marca text-cuerpo-md font-semibold tracking-tight">
                DatenJäger
              </span>
              <span className="block truncate text-etiqueta-sm text-tenue">
                Gestión documental
              </span>
            </span>
          )}
        </button>
      </div>

      <ul className="flex flex-1 flex-col gap-space-xs overflow-y-auto px-2 py-3">
        {principales.map((entrada) => (
          <li key={entrada.clave}>
            <BotonSeccion
              {...entrada}
              activa={entrada.clave === seccion}
              plegada={plegada}
              onSeleccionar={onSeleccionar}
            />
          </li>
        ))}
      </ul>

      <div className="flex flex-col gap-space-xs border-t border-borde px-2 py-3">
        <BotonTema plegada={plegada} />
        {ajustes && (
          <BotonSeccion
            {...ajustes}
            activa={ajustes.clave === seccion}
            plegada={plegada}
            onSeleccionar={onSeleccionar}
          />
        )}
      </div>
    </nav>
  )
}

/** Entrada de navegación: la misma pieza arriba y al pie. */
function BotonSeccion({ clave, titulo, descripcion, icono, activa, plegada, onSeleccionar }) {
  return (
    <button
      type="button"
      onClick={() => onSeleccionar(clave)}
      aria-current={activa ? 'page' : undefined}
      title={plegada ? titulo : undefined}
      className={[
        'flex h-9 w-full items-center rounded-md px-3 text-left transition-colors',
        plegada ? 'justify-center' : 'gap-2.5',
        activa ? 'bg-primario-suave font-medium text-primario' : 'text-texto hover:bg-fondo-2',
      ].join(' ')}
    >
      <Icono nombre={icono} tamano={18} />
      {!plegada && (
        <>
          <span className="truncate text-etiqueta-md">{titulo}</span>
          <span className="ml-auto truncate text-etiqueta-sm text-tenue">{descripcion}</span>
        </>
      )}
    </button>
  )
}

function BotonTema({ plegada }) {
  const { tema, alternarTema } = useApp()
  const etiqueta = tema === 'oscuro' ? 'Tema claro' : 'Tema oscuro'

  return (
    <button
      type="button"
      onClick={alternarTema}
      title={etiqueta}
      aria-label={etiqueta}
      className="group flex h-9 w-full items-center justify-center gap-2 rounded-md border border-borde px-3 text-etiqueta-md text-tenue transition-colors hover:border-primario hover:text-primario"
    >
      <span className="transition-transform duration-300 group-hover:rotate-45">
        <Icono nombre={tema === 'oscuro' ? 'sol' : 'luna'} tamano={16} />
      </span>
      {!plegada && etiqueta}
    </button>
  )
}