import { useCallback, useEffect, useState } from 'react'

import Panel, {
  CabeceraPagina,
  Esqueleto,
  EstadoError,
  EstadoVacio,
  Tarjeta,
} from '../components/Panel.jsx'
import { useApp } from '../estado/ProveedorApp.jsx'
import { backend } from '../lib/api.js'

/**
 * Recopilador de datos y estadísticas (SCRUM-62).
 *
 * La **lógica** de las métricas vive en Python (`backend/services/reportes.py`:
 * conteos, distribución por empresa y serie temporal) y en el frontend solo se
 * dibuja, con la paleta del sistema —el reparto acordado para esta fase—. Los
 * gráficos se componen con `div`s y los tokens de color en lugar de traer una
 * librería de charts: son barras, y Tailwind ya sabe hacerlas.
 *
 * Todo lo que se muestra sale de una consulta real. Si el archivo está vacío,
 * se dice que está vacío en vez de dibujar ejes sin datos.
 */
const COLORES_BARRA = ['bg-primario', 'bg-acento', 'bg-exito', 'bg-alerta', 'bg-peligro']

export default function Estadisticas({ onNavegar }) {
  const { conectado, autenticado } = useApp()

  const [estado, setEstado] = useState('cargando')
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)

  const cargar = useCallback(async () => {
    setEstado('cargando')
    setError(null)
    try {
      const [estadisticas, porEmpresa, porDia, eventos] = await Promise.all([
        backend.reportes.estadisticas(),
        backend.reportes.porEmpresa(),
        backend.reportes.porDia(),
        backend.auditoria.contar(),
      ])
      setDatos({ estadisticas, porEmpresa, porDia, eventos: eventos?.total ?? 0 })
      setEstado('listo')
    } catch (fallo) {
      setError(fallo.message)
      setEstado('error')
    }
  }, [])

  useEffect(() => {
    if (!conectado || !autenticado) return
    cargar()
  }, [conectado, autenticado, cargar])

  if (!conectado || !autenticado) {
    return (
      <EstadoVacio
        titulo={conectado ? 'Sesión no iniciada' : 'Sin conexión con el servicio local'}
        mensaje={
          conectado
            ? 'Vuelve a la pantalla de acceso para identificarte.'
            : 'Las métricas se calculan en el servicio de Python. Revisa la franja inferior.'
        }
      />
    )
  }

  const metricas = datos?.estadisticas ?? {}
  const porEmpresa = datos?.porEmpresa ?? []
  const porDia = datos?.porDia ?? []
  const vacio = (metricas.total_pdfs ?? 0) === 0 && estado === 'listo'

  return (
    <div className="flex flex-col gap-4">
      <CabeceraPagina
        titulo="Datos y estadísticas"
        descripcion="Métricas del archivo cifrado, calculadas en el backend"
        acciones={
          <button
            type="button"
            onClick={cargar}
            disabled={estado === 'cargando'}
            className="rounded-lg border border-borde px-3 py-1.5 text-etiqueta-sm text-tenue transition-colors hover:border-primario hover:text-primario disabled:opacity-50"
          >
            {estado === 'cargando' ? 'Calculando…' : 'Recalcular'}
          </button>
        }
      />

      {estado === 'cargando' && <Esqueleto filas={4} variante="tarjetas" />}
      {estado === 'error' && <EstadoError mensaje={error} onReintentar={cargar} />}

      {estado === 'listo' && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Tarjeta etiqueta="Documentos" valor={metricas.total_pdfs ?? 0} acento="primario" />
            <Tarjeta etiqueta="Titulares" valor={metricas.total_personas ?? 0} />
            <Tarjeta etiqueta="Empresas" valor={metricas.total_empresas ?? 0} />
            <Tarjeta etiqueta="Eventos auditados" valor={datos.eventos} acento="acento" />
          </div>

          {vacio ? (
            <Panel titulo="Distribución" descripcion="Sin datos todavía">
              <EstadoVacio
                titulo="El archivo está vacío"
                mensaje="Las estadísticas se construyen con los documentos cifrados. Agrega alguno y vuelve a recalcular."
                accion={
                  <button
                    type="button"
                    onClick={() => onNavegar?.('documentos')}
                    className="mt-2 rounded-lg border border-borde px-3 py-1.5 text-etiqueta-sm hover:border-primario hover:text-primario"
                  >
                    Ir a documentos
                  </button>
                }
              />
            </Panel>
          ) : (
            <div className="grid gap-4 xl:grid-cols-2">
              <Panel
                titulo="Documentos por empresa"
                descripcion={`${porEmpresa.length} empresa(s) con expedientes`}
              >
                <BarrasHorizontales
                  elementos={porEmpresa.map((fila) => ({
                    etiqueta: fila.empresa,
                    valor: fila.total,
                  }))}
                />
              </Panel>

              <Panel
                titulo="Documentos por día"
                descripcion={`${porDia.length} día(s) con altas registradas`}
              >
                <BarrasVerticales
                  elementos={porDia.map((fila) => ({ etiqueta: fila.dia, valor: fila.total }))}
                />
              </Panel>
            </div>
          )}

          <Panel titulo="Volumen" descripcion="Ocupación del archivo cifrado">
            <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Dato etiqueta="Tamaño total" valor={metricas.total_size_str ?? '0 B'} mono />
              <Dato
                etiqueta="Media por documento"
                valor={mediaPorDocumento(metricas)}
                mono
              />
              <Dato etiqueta="Eventos en auditoría" valor={String(datos.eventos)} mono />
            </dl>
            <p className="mt-3 border-t border-borde pt-3 text-cuerpo-sm text-tenue">
              Los tamaños son los del documento cifrado en reposo. La media se calcula aquí a
              partir de los totales que devuelve el backend.
            </p>
          </Panel>
        </>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */

function Dato({ etiqueta, valor, mono }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-etiqueta-sm uppercase tracking-wider text-tenue">{etiqueta}</dt>
      <dd className={`text-titulo-sm ${mono ? 'font-mono' : ''}`}>{valor}</dd>
    </div>
  )
}

/** Barras horizontales: una por empresa, con el nombre a la izquierda. */
function BarrasHorizontales({ elementos }) {
  const maximo = Math.max(...elementos.map(({ valor }) => valor), 1)

  return (
    <ul className="flex flex-col gap-2.5">
      {elementos.map(({ etiqueta, valor }, indice) => (
        <li key={etiqueta} className="animar-entrada flex items-center gap-3">
          <span className="w-32 shrink-0 truncate text-cuerpo-sm text-texto-2" title={etiqueta}>
            {etiqueta}
          </span>
          <span className="h-2.5 min-w-0 flex-1 overflow-hidden rounded-full bg-fondo-2">
            <span
              className={`block h-full rounded-full ${COLORES_BARRA[indice % COLORES_BARRA.length]}`}
              style={{ width: `${Math.max((valor / maximo) * 100, 2)}%` }}
            />
          </span>
          <span className="w-10 shrink-0 text-right font-mono text-cuerpo-sm">{valor}</span>
        </li>
      ))}
    </ul>
  )
}

/** Barras verticales: la serie temporal, con la fecha en el pie. */
function BarrasVerticales({ elementos }) {
  const maximo = Math.max(...elementos.map(({ valor }) => valor), 1)

  return (
    <div className="flex h-48 items-end gap-1.5 overflow-x-auto">
      {elementos.map(({ etiqueta, valor }, indice) => (
        <div
          key={etiqueta}
          className="animar-entrada flex h-full min-w-[2.2rem] flex-1 flex-col items-center justify-end gap-1"
          title={`${etiqueta}: ${valor}`}
        >
          <span className="font-mono text-telemetria text-tenue">{valor}</span>
          <span
            className={`w-full rounded-t ${COLORES_BARRA[indice % COLORES_BARRA.length]}`}
            style={{ height: `${Math.max((valor / maximo) * 100, 4)}%` }}
          />
          <span className="rotate-0 whitespace-nowrap font-mono text-[10px] text-tenue">
            {etiqueta?.slice(5) ?? ''}
          </span>
        </div>
      ))}
    </div>
  )
}

/**
 * Media por documento a partir del texto del tamaño total. Se calcula aquí
 * porque el backend entrega el total ya formateado para la vista, no en bytes.
 */
function mediaPorDocumento(metricas) {
  const total = metricas.total_pdfs ?? 0
  if (!total) return '—'

  const bytes = aBytes(metricas.total_size_str)
  if (bytes === null) return '—'

  return tamanoLegible(bytes / total)
}

const UNIDADES = { B: 1, KB: 1024, MB: 1024 ** 2, GB: 1024 ** 3, TB: 1024 ** 4 }

function aBytes(texto) {
  const coincidencia = /^([\d.]+)\s*(B|KB|MB|GB|TB)$/.exec((texto ?? '').trim())
  if (!coincidencia) return null
  return Number(coincidencia[1]) * UNIDADES[coincidencia[2]]
}

function tamanoLegible(bytes) {
  const unidades = ['B', 'KB', 'MB', 'GB']
  let valor = bytes
  let indice = 0
  while (valor >= 1024 && indice < unidades.length - 1) {
    valor /= 1024
    indice += 1
  }
  return `${valor.toFixed(1)} ${unidades[indice]}`
}