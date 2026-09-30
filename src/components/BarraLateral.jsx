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
 */
export default function BarraLateral({ seccion, onSeleccionar, plegada, onPlegar }) {
  return (
    <nav
      aria-label="Secciones del sistema"
      className={[
        'flex shrink-0 flex-col border-r border-borde bg-superficie',
        'transition-[width] duration-200 ease-out',
        plegada ? 'w-lateral-min' : 'w-lateral',
      ].join(' ')}
    >
      <div className="flex h-cabecera shrink-0 items-center gap-2 border-b border-borde px-3">
        <img
          src={logo}
          alt="DatenJäger"
          className="h-8 w-8 shrink-0 rounded-full object-contain"
        />

        {!plegada && (
          <div className="min-w-0 leading-tight">
            <p className="truncate font-marca text-cuerpo-md font-semibold tracking-tight">
              DatenJäger
            </p>
            <p className="truncate text-etiqueta-sm text-tenue">Gestión documental</p>
          </div>
        )}

        <button
          type="button"
          onClick={onPlegar}
          aria-expanded={!plegada}
          aria-label={plegada ? 'Desplegar la barra lateral' : 'Recoger la barra lateral'}
          title={plegada ? 'Desplegar la barra lateral' : 'Recoger la barra lateral'}
          className="ml-auto flex h-7 w-7 shrink-0 items-center justify-center rounded border border-borde text-tenue transition-colors hover:border-primario hover:text-primario"
        >
          <Icono nombre={plegada ? 'chevron-derecha' : 'chevron-izquierda'} />
        </button>
      </div>

      <ul className="flex flex-1 flex-col gap-space-xs overflow-y-auto px-2 py-3">
        {SECCIONES.map(({ clave, titulo, descripcion, icono }) => {
          const activa = clave === seccion
          return (
            <li key={clave}>
              <button
                type="button"
                onClick={() => onSeleccionar(clave)}
                aria-current={activa ? 'page' : undefined}
                title={plegada ? titulo : undefined}
                className={[
                  'flex h-9 w-full items-center rounded-md px-3 text-left transition-colors',
                  plegada ? 'justify-center' : 'gap-2.5',
                  activa
                    ? 'bg-primario-suave font-medium text-primario'
                    : 'text-texto hover:bg-fondo-2',
                ].join(' ')}
              >
                <Icono nombre={icono} tamano={18} />
                {!plegada && (
                  <>
                    <span className="truncate text-etiqueta-md">{titulo}</span>
                    <span className="ml-auto truncate text-etiqueta-sm text-tenue">
                      {descripcion}
                    </span>
                  </>
                )}
              </button>
            </li>
          )
        })}
      </ul>

      <div className="border-t border-borde px-2 py-3">
        <BotonTema plegada={plegada} />
      </div>
    </nav>
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
      className="flex h-9 w-full items-center justify-center gap-2 rounded-md border border-borde px-3 text-etiqueta-md text-tenue transition-colors hover:border-primario hover:text-primario"
    >
      <Icono nombre={tema === 'oscuro' ? 'sol' : 'luna'} tamano={16} />
      {!plegada && etiqueta}
    </button>
  )
}