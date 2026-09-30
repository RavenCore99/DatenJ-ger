import { useCallback, useEffect, useMemo, useState } from 'react'

import Panel, {
  Aviso,
  CabeceraPagina,
  Esqueleto,
  EstadoError,
  EstadoVacio,
  Pill,
  Tarjeta,
} from '../components/Panel.jsx'
import { useApp } from '../estado/ProveedorApp.jsx'
import { backend } from '../lib/api.js'
import { fechaCorta } from '../lib/formato.js'

/** Tamaño de página del historial, igual que el visor de CustomTkinter. */
const POR_PAGINA = 200

const FILTROS_VACIOS = { desde: '', hasta: '', accion: '' }

/**
 * Panel de auditoría (SCRUM-30): trazabilidad de las acciones sobre el archivo.
 *
 * Conserva la funcionalidad del visor anterior —consulta filtrada por fecha y
 * tipo de acción, conteo, limpieza del historial y consulta del log— y adopta
 * la composición de los mockups: fila de métricas, filtros en una tarjeta,
 * tabla con la acción en pill coloreada y visor de log tipo terminal en
 * monoespaciada.
 */
export default function Auditoria() {
  const { conectado, autenticado } = useApp()

  const [filtros, setFiltros] = useState(FILTROS_VACIOS)
  const [estado, setEstado] = useState('cargando')
  const [eventos, setEventos] = useState([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState(null)
  const [aviso, setAviso] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  const [log, setLog] = useState(null)

  const cargar = useCallback(async (aplicados) => {
    setEstado('cargando')
    setError(null)

    try {
      const [historial, conteo] = await Promise.all([
        backend.auditoria.listar({ ...aplicados, limite: POR_PAGINA }),
        backend.auditoria.contar(),
      ])
      setEventos(historial)
      setTotal(conteo?.total ?? historial.length)
      setEstado('listo')
    } catch (fallo) {
      setError(fallo.message)
      setEstado('error')
    }
  }, [])

  useEffect(() => {
    if (!conectado || !autenticado) return
    cargar(filtros)
    // Solo al montar y al conectarse: los filtros se aplican con el botón.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conectado, autenticado, cargar])

  /** Reparto por tipo de acción del historial visible, para las métricas. */
  const resumen = useMemo(() => {
    const porTipo = new Map()
    for (const evento of eventos) {
      const clave = clasificarAccion(evento.accion)
      porTipo.set(clave, (porTipo.get(clave) ?? 0) + 1)
    }
    return { porTipo, tipos: porTipo.size }
  }, [eventos])

  const limpiar = useCallback(async () => {
    if (
      !globalThis.confirm(
        'Se vaciará todo el historial de auditoría. Quedará registrada la limpieza. ¿Continuar?',
      )
    )
      return

    setOcupado(true)
    setAviso(null)
    try {
      const resultado = await backend.auditoria.limpiar()
      setAviso({ tipo: 'exito', texto: `${resultado.eliminados} registro(s) eliminado(s)` })
      await cargar(filtros)
    } catch (fallo) {
      setAviso({ tipo: 'error', texto: fallo.message })
    } finally {
      setOcupado(false)
    }
  }, [cargar, filtros])

  const verLog = useCallback(async () => {
    setOcupado(true)
    setAviso(null)
    try {
      setLog(await backend.auditoria.log())
    } catch (fallo) {
      setAviso({ tipo: 'error', texto: fallo.message })
    } finally {
      setOcupado(false)
    }
  }, [])

  if (!conectado || !autenticado) {
    return (
      <Panel titulo="Auditoría" descripcion="Historial de acciones sobre el archivo">
        <EstadoVacio
          titulo={conectado ? 'Sesión no iniciada' : 'Sin conexión con el servicio local'}
          mensaje={
            conectado
              ? 'Vuelve a la pantalla de acceso para identificarte.'
              : 'El historial se consulta contra el servicio de Python.'
          }
        />
      </Panel>
    )
  }

  return (
    <div className="aparecer flex flex-col gap-6">
      <CabeceraPagina
        titulo="Auditoría"
        descripcion="Trazabilidad de acciones · Ley 1581 de 2012"
        acciones={
          <>
            <button
              type="button"
              onClick={verLog}
              disabled={ocupado}
              className="rounded-lg border border-borde px-3 py-2 text-etiqueta-md font-medium transition-colors hover:border-primario hover:text-primario disabled:opacity-50"
            >
              Ver log del sistema
            </button>
            <button
              type="button"
              onClick={limpiar}
              disabled={ocupado}
              className="rounded-lg border border-peligro/40 px-3 py-2 text-etiqueta-md font-medium text-peligro transition-colors hover:bg-peligro/5 disabled:opacity-50"
            >
              Limpiar historial
            </button>
          </>
        }
      />

      {aviso && (
        <Aviso tipo={aviso.tipo} onCerrar={() => setAviso(null)}>
          {aviso.texto}
        </Aviso>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Tarjeta etiqueta="Registros totales" valor={total} acento="primario" />
        <Tarjeta etiqueta="Mostrados" valor={eventos.length} nota={`últimos ${POR_PAGINA}`} />
        <Tarjeta etiqueta="Tipos de acción" valor={resumen.tipos} />
        <Tarjeta
          etiqueta="Rango consultado"
          valor={filtros.desde || filtros.hasta ? 'filtrado' : 'completo'}
          nota={rangoLegible(filtros)}
        />
      </div>

      <Panel
        titulo="Filtros"
        descripcion="Fecha (desde y hasta) y tipo de acción"
        acciones={
          <span className="font-mono text-telemetria text-tenue">Ley 1581 · hábeas data</span>
        }
      >
        <form
          className="grid grid-cols-2 gap-4 lg:grid-cols-4"
          onSubmit={(evento) => {
            evento.preventDefault()
            cargar(filtros)
          }}
        >
          {[
            ['desde', 'Desde', 'date'],
            ['hasta', 'Hasta', 'date'],
            ['accion', 'Acción contiene', 'text'],
          ].map(([campo, etiqueta, tipo]) => (
            <label key={campo} className="flex flex-col gap-1">
              <span className="text-etiqueta-sm text-texto">{etiqueta}</span>
              <input
                type={tipo}
                value={filtros[campo]}
                onChange={(evento) =>
                  setFiltros((actual) => ({ ...actual, [campo]: evento.target.value }))
                }
                className="rounded-lg border border-borde bg-fondo px-3 py-2 text-cuerpo-md outline-none transition-colors focus:border-primario"
              />
            </label>
          ))}

          <div className="flex items-end gap-2">
            <button
              type="submit"
              className="rounded-lg bg-primario px-4 py-2 text-etiqueta-md font-medium text-sobre-primario transition-colors hover:bg-primario-enfasis"
            >
              Aplicar
            </button>
            <button
              type="button"
              onClick={() => {
                setFiltros(FILTROS_VACIOS)
                cargar(FILTROS_VACIOS)
              }}
              className="rounded-lg border border-borde px-3 py-2 text-etiqueta-md font-medium transition-colors hover:border-primario hover:text-primario"
            >
              Limpiar
            </button>
          </div>
        </form>
      </Panel>

      <Panel
        titulo="Historial"
        descripcion={`${eventos.length} mostrados de ${total} registro(s)`}
      >
        {estado === 'cargando' && <Esqueleto filas={6} />}
        {estado === 'error' && <EstadoError mensaje={error} onReintentar={() => cargar(filtros)} />}

        {estado === 'listo' && eventos.length === 0 && (
          <EstadoVacio
            titulo="Sin registros"
            mensaje="Ninguna acción coincide con los filtros aplicados."
          />
        )}

        {estado === 'listo' && eventos.length > 0 && (
          <table className="w-full border-collapse text-cuerpo-md">
            <thead>
              <tr className="text-left text-etiqueta-sm uppercase tracking-wider text-tenue">
                <th className="pb-2 font-medium">Fecha</th>
                <th className="pb-2 font-medium">Acción</th>
                <th className="pb-2 font-medium">Usuario</th>
                <th className="pb-2 font-medium">Documento</th>
              </tr>
            </thead>
            <tbody>
              {eventos.map((evento) => (
                <tr key={evento.id} className="border-t border-borde transition-colors hover:bg-fondo-2">
                  <td className="py-2.5 pr-3 font-mono text-cuerpo-sm text-tenue">
                    {fechaCorta(evento.fecha)}
                  </td>
                  <td className="py-2.5 pr-3">
                    <Pill tipo={colorDeAccion(evento.accion)}>{evento.accion}</Pill>
                  </td>
                  <td className="py-2.5 pr-3 text-texto-2">{evento.usuario ?? '—'}</td>
                  <td className="py-2.5 font-mono text-cuerpo-sm text-tenue">
                    {evento.documento_id ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      {log && (
        <Panel
          titulo="Log del sistema"
          descripcion={log.origen}
          acciones={
            <button
              type="button"
              onClick={() => setLog(null)}
              className="rounded-lg border border-borde px-3 py-2 text-etiqueta-md font-medium transition-colors hover:border-primario hover:text-primario"
            >
              Cerrar
            </button>
          }
        >
          <div className="flex flex-col overflow-hidden rounded-lg border border-borde bg-lienzo">
            <div className="flex items-center gap-1.5 border-b border-borde px-3 py-2">
              <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full bg-trafico-cerrar" />
              <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full bg-trafico-minimizar" />
              <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full bg-trafico-expandir" />
              <span className="ml-2 truncate font-mono text-telemetria text-tenue">{log.origen}</span>
            </div>
            <pre className="max-h-96 overflow-auto px-4 py-3 font-mono text-codigo leading-relaxed text-texto-2">
              {log.contenido || '(vacío)'}
            </pre>
          </div>
        </Panel>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */

/** Clasifica una acción en una familia, para el reparto de las métricas. */
function clasificarAccion(accion = '') {
  const texto = accion.toLowerCase()
  if (/(elimin|borr|purga|vacia|limpieza)/.test(texto)) return 'eliminacion'
  if (/(crea|alta|agrega|registr|sube|cifra)/.test(texto)) return 'alta'
  if (/(acceso|sesion|login|autentic|2fa|token|confianza)/.test(texto)) return 'acceso'
  if (/(descarga|exporta|abre|lectura|consulta)/.test(texto)) return 'lectura'
  return 'otro'
}

const COLORES = {
  eliminacion: 'peligro',
  alta: 'exito',
  acceso: 'primario',
  lectura: 'info',
  otro: 'neutro',
}

function colorDeAccion(accion) {
  return COLORES[clasificarAccion(accion)] ?? 'neutro'
}

function rangoLegible({ desde, hasta }) {
  if (!desde && !hasta) return 'sin filtro de fecha'
  return `${desde || 'inicio'} → ${hasta || 'hoy'}`
}