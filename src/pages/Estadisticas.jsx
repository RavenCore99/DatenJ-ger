import { useCallback, useEffect, useState } from 'react'

import Panel, {
  CabeceraPagina,
  Esqueleto,
  EstadoError,
  EstadoVacio,
} from '../components/Panel.jsx'
import { Donut, LineaTendencia, Medidor } from '../components/Graficos.jsx'
import { useApp } from '../estado/ProveedorApp.jsx'
import { backend } from '../lib/api.js'

/**
 * Dashboard de datos y estadísticas (SCRUM-82).
 *
 * La **lógica** vive en Python (`backend/services/reportes.py`): métricas,
 * distribución por empresa y la serie temporal con regresión, predicción y R²
 * (`GET /api/reportes/tendencia`). Aquí solo se dibuja, con la paleta del
 * sistema y sin librería de charts: medidores, anillo y línea de tendencia son
 * SVG propio (`src/components/Graficos.jsx`).
 *
 * Todo lo que se muestra sale de una consulta real. Si el archivo está vacío se
 * dice que está vacío, en vez de dibujar ejes sin datos.
 */
export default function Estadisticas({ onNavegar }) {
  const { conectado, autenticado } = useApp()

  const [estado, setEstado] = useState('cargando')
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)

  const cargar = useCallback(async () => {
    setEstado('cargando')
    setError(null)
    try {
      const [estadisticas, porEmpresa, tendencia, eventos] = await Promise.all([
        backend.reportes.estadisticas(),
        backend.reportes.porEmpresa(),
        backend.reportes.tendencia(),
        backend.auditoria.contar(),
      ])
      setDatos({ estadisticas, porEmpresa, tendencia, eventos: eventos?.total ?? 0 })
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
  const tendencia = datos?.tendencia ?? null
  const eventos = datos?.eventos ?? 0
  const vacio = (metricas.total_pdfs ?? 0) === 0 && estado === 'listo'

  const medidores = [
    { etiqueta: 'Documentos', valor: metricas.total_pdfs ?? 0, rol: 'primario' },
    { etiqueta: 'Titulares', valor: metricas.total_personas ?? 0, rol: 'acento' },
    { etiqueta: 'Empresas', valor: metricas.total_empresas ?? 0, rol: 'exito' },
    { etiqueta: 'Eventos', valor: eventos, rol: 'alerta' },
  ]
  // Los medidores comparten escala para poder compararse entre sí; el valor
  // real va dentro del arco, así que la escala relativa no oculta la cifra.
  const maximoMedidores = Math.max(...medidores.map(({ valor }) => valor), 1)

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
          <Panel
            titulo="Resumen"
            descripcion="Escala relativa entre las métricas del archivo"
          >
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              {medidores.map((medidor) => (
                <Medidor
                  key={medidor.etiqueta}
                  etiqueta={medidor.etiqueta}
                  valor={medidor.valor}
                  maximo={maximoMedidores}
                  rol={medidor.rol}
                />
              ))}
            </div>
          </Panel>

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
                <Donut elementos={porEmpresa.map((fila) => ({
                  etiqueta: fila.empresa,
                  valor: fila.total,
                }))} />
              </Panel>

              <Panel
                titulo="Actividad temporal"
                descripcion="Subidas por día con regresión lineal"
              >
                <LineaTendencia tendencia={tendencia} />
              </Panel>
            </div>
          )}

          <Panel titulo="Volumen" descripcion="Ocupación del archivo cifrado">
            <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Dato etiqueta="Tamaño total" valor={metricas.total_size_str ?? '0 B'} mono />
              <Dato etiqueta="Media por documento" valor={mediaPorDocumento(metricas)} mono />
              <Dato etiqueta="Eventos en auditoría" valor={String(eventos)} mono />
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