import { useCallback, useEffect, useState } from 'react'

import Panel, { Esqueleto, EstadoError, EstadoVacio } from '../components/Panel.jsx'
import { useApp } from '../estado/ProveedorApp.jsx'
import { backend } from '../lib/api.js'
import { fechaCorta } from '../lib/formato.js'

/** Tamaño de página del historial, igual que el visor de CustomTkinter. */
const POR_PAGINA = 200

/**
 * Panel de auditoría (SCRUM-24).
 *
 * Migra el visor de historial: consulta filtrada por fecha y tipo de acción,
 * conteo, limpieza del historial (dejando constancia del vaciado) y consulta
 * del log del sistema.
 */
export default function Auditoria() {
  const { conectado, autenticado } = useApp()

  const [filtros, setFiltros] = useState({ desde: '', hasta: '', accion: '' })
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

  const limpiar = useCallback(async () => {
    if (!globalThis.confirm(
      'Se vaciará todo el historial de auditoría. Quedará registrada la limpieza. ¿Continuar?',
    )) return

    setOcupado(true)
    setAviso(null)
    try {
      const resultado = await backend.auditoria.limpiar()
      setAviso(`${resultado.eliminados} registro(s) eliminado(s)`)
      await cargar(filtros)
    } catch (fallo) {
      setAviso(`Error: ${fallo.message}`)
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
      setAviso(`Error: ${fallo.message}`)
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
              ? 'La pantalla de inicio de sesión todavía no está migrada (SCRUM-22).'
              : 'El historial se consulta contra el servicio de Python.'
          }
        />
      </Panel>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {aviso && (
        <div
          role="status"
          className={[
            'flex items-center justify-between gap-4 rounded-lg border px-4 py-2 text-xs',
            aviso.startsWith('Error')
              ? 'border-peligro/40 bg-peligro/5 text-peligro'
              : 'border-exito/40 bg-exito/5',
          ].join(' ')}
        >
          <span>{aviso}</span>
          <button type="button" onClick={() => setAviso(null)} className="font-mono">
            cerrar
          </button>
        </div>
      )}

      <Panel
        titulo="Filtros"
        descripcion="Fecha (desde y hasta) y tipo de acción"
        acciones={
          <>
            <button
              type="button"
              onClick={verLog}
              disabled={ocupado}
              className="rounded-lg border border-borde px-3 py-1.5 text-xs font-medium hover:border-primario hover:text-primario disabled:opacity-50"
            >
              Ver log del sistema
            </button>
            <button
              type="button"
              onClick={limpiar}
              disabled={ocupado}
              className="rounded-lg border border-peligro/40 px-3 py-1.5 text-xs font-medium text-peligro disabled:opacity-50"
            >
              Limpiar historial
            </button>
          </>
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
              <span className="text-[11px] uppercase tracking-wider text-tenue">{etiqueta}</span>
              <input
                type={tipo}
                value={filtros[campo]}
                onChange={(evento) =>
                  setFiltros((actual) => ({ ...actual, [campo]: evento.target.value }))
                }
                className="rounded-lg border border-borde bg-fondo px-3 py-1.5 text-xs outline-none focus:border-primario"
              />
            </label>
          ))}

          <div className="flex items-end gap-2">
            <button
              type="submit"
              className="rounded-lg bg-primario px-4 py-1.5 text-xs font-medium text-white"
            >
              Aplicar
            </button>
            <button
              type="button"
              onClick={() => {
                const limpios = { desde: '', hasta: '', accion: '' }
                setFiltros(limpios)
                cargar(limpios)
              }}
              className="rounded-lg border border-borde px-3 py-1.5 text-xs font-medium"
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
          <table className="w-full border-collapse text-xs">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wider text-tenue">
                <th className="pb-2 font-medium">Fecha</th>
                <th className="pb-2 font-medium">Acción</th>
                <th className="pb-2 font-medium">Usuario</th>
                <th className="pb-2 font-medium">Documento</th>
              </tr>
            </thead>
            <tbody>
              {eventos.map((evento) => (
                <tr key={evento.id} className="border-t border-borde">
                  <td className="py-2 pr-3 font-mono text-tenue">{fechaCorta(evento.fecha)}</td>
                  <td className="py-2 pr-3">{evento.accion}</td>
                  <td className="py-2 pr-3 text-tenue">{evento.usuario ?? '—'}</td>
                  <td className="py-2 font-mono text-tenue">
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
              className="rounded-lg border border-borde px-3 py-1.5 text-xs font-medium"
            >
              Cerrar
            </button>
          }
        >
          <pre className="max-h-96 overflow-auto rounded-lg bg-fondo px-4 py-3 font-mono text-[11px] leading-relaxed">
            {log.contenido || '(vacío)'}
          </pre>
        </Panel>
      )}
    </div>
  )
}