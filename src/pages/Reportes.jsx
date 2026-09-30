import { useCallback, useEffect, useState } from 'react'

import Panel, {
  Aviso,
  CabeceraPagina,
  Esqueleto,
  EstadoError,
  EstadoVacio,
  Tarjeta,
} from '../components/Panel.jsx'
import Icono from '../components/Icono.jsx'
import { useApp } from '../estado/ProveedorApp.jsx'
import { backend } from '../lib/api.js'
import { elegirDestino } from '../lib/escritorio.js'
import { fechaCorta, tamanoLegible } from '../lib/formato.js'

/**
 * Panel de reportes (SCRUM-61).
 *
 * Recoge lo que ya hacía `reporter.py` —inventario de documentos con su titular
 * y el resumen de cifras— y lo viste con la paleta del sistema. El reparto de
 * responsabilidades es el acordado para esta fase: **el PDF y el CSV los genera
 * Python** (`ReporteInventario`), y aquí solo se elige el destino y se muestra
 * el resultado; la estructura del documento —portada, inventario y gráfico por
 * empresa— se conserva tal cual.
 *
 * La ruta de destino la resuelve el diálogo nativo de Electron (`elegirDestino`):
 * el archivo lo escribe el servicio, no el renderer.
 */
export default function Reportes({ onNavegar }) {
  const { conectado, autenticado } = useApp()

  const [estado, setEstado] = useState('cargando')
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)
  const [aviso, setAviso] = useState(null)
  const [ocupado, setOcupado] = useState(null)

  const cargar = useCallback(async () => {
    setEstado('cargando')
    setError(null)
    try {
      const [inventario, estadisticas] = await Promise.all([
        backend.reportes.inventario(),
        backend.reportes.estadisticas(),
      ])
      setDatos({ filas: inventario?.filas ?? [], metricas: inventario?.metricas ?? {}, estadisticas })
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

  const exportar = useCallback(
    async (formato) => {
      setOcupado(formato)
      setAviso(null)
      try {
        const destino = await elegirDestino({
          nombre: `inventario-datenjager.${formato}`,
          formato,
        })

        if (destino?.cancelado) {
          if (destino.motivo) setAviso(`Error: ${destino.motivo}`)
          return
        }

        await backend.reportes.exportar(destino.destino, formato)
        setAviso(`Reporte ${formato.toUpperCase()} generado en ${destino.destino}`)
      } catch (fallo) {
        setAviso(`Error: ${fallo.message}`)
      } finally {
        setOcupado(null)
      }
    },
    [],
  )

  if (!conectado || !autenticado) {
    return (
      <EstadoVacio
        titulo={conectado ? 'Sesión no iniciada' : 'Sin conexión con el servicio local'}
        mensaje={
          conectado
            ? 'Vuelve a la pantalla de acceso para identificarte.'
            : 'Los reportes se generan en el servicio de Python. Revisa la franja inferior.'
        }
      />
    )
  }

  const filas = datos?.filas ?? []
  const metricas = datos?.metricas ?? {}

  return (
    <div className="flex flex-col gap-4">
      <CabeceraPagina
        titulo="Reportes"
        descripcion="Inventario documental exportable con la identidad del sistema"
        acciones={
          <>
            <BotonExportar
              formato="pdf"
              ocupado={ocupado === 'pdf'}
              onClick={() => exportar('pdf')}
              icono="documentos"
            />
            <BotonExportar
              formato="csv"
              ocupado={ocupado === 'csv'}
              onClick={() => exportar('csv')}
              icono="lista"
            />
          </>
        }
      />

      {aviso && (
        <Aviso tipo={aviso.startsWith('Error') ? 'error' : 'exito'} onCerrar={() => setAviso(null)}>
          {aviso}
        </Aviso>
      )}

      {estado === 'cargando' && (
        <Panel titulo="Inventario" descripcion="Preparando el reporte">
          <Esqueleto filas={6} variante="tabla" />
        </Panel>
      )}

      {estado === 'error' && <EstadoError mensaje={error} onReintentar={cargar} />}

      {estado === 'listo' && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Tarjeta etiqueta="Documentos" valor={metricas.total_pdfs ?? 0} acento="primario" />
            <Tarjeta etiqueta="Titulares" valor={metricas.total_personas ?? 0} />
            <Tarjeta etiqueta="Empresas" valor={metricas.total_empresas ?? 0} />
            <Tarjeta etiqueta="Volumen" valor={metricas.total_size_str ?? '0 B'} acento="exito" />
          </div>

          <Panel
            titulo="Inventario"
            descripcion={`${filas.length} expediente(s) · portada, inventario y gráfico por empresa`}
            acciones={
              <button
                type="button"
                onClick={() => onNavegar?.('estadisticas')}
                className="inline-flex items-center gap-1.5 rounded-lg border border-borde px-3 py-1.5 text-etiqueta-sm transition-colors hover:border-primario hover:text-primario"
              >
                <Icono nombre="grafico" tamano={13} />
                Ver estadísticas
              </button>
            }
          >
            {filas.length === 0 ? (
              <EstadoVacio
                titulo="Sin documentos que reportar"
                mensaje="El inventario se construye con los PDF cifrados del archivo. Agrega el primero en el panel documental."
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
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-cuerpo-md">
                  <thead>
                    <tr className="border-b border-borde text-left text-etiqueta-sm uppercase tracking-wider text-tenue">
                      <th className="py-2.5 pr-3 font-medium">Documento</th>
                      <th className="px-3 py-2.5 font-medium">Titular</th>
                      <th className="px-3 py-2.5 font-medium">Cédula</th>
                      <th className="px-3 py-2.5 font-medium">Empresa</th>
                      <th className="px-3 py-2.5 font-medium">Tamaño</th>
                      <th className="py-2.5 pl-3 font-medium">Fecha</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filas.map((fila) => (
                      <tr
                        key={fila[0]}
                        className="animar-entrada border-b border-borde last:border-b-0"
                      >
                        <td className="py-2.5 pr-3">
                          <span className="font-medium">{fila[1]}</span>
                          {fila[2] && (
                            <span className="block text-cuerpo-sm text-tenue">{fila[2]}</span>
                          )}
                        </td>
                        <td className="px-3 py-2.5 text-texto-2">{fila[6] ?? 'Sin titular'}</td>
                        <td className="px-3 py-2.5 font-mono text-cuerpo-sm text-texto-2">
                          {fila[5] ?? '—'}
                        </td>
                        <td className="px-3 py-2.5 text-texto-2">{fila[7] ?? '—'}</td>
                        <td className="px-3 py-2.5 font-mono text-cuerpo-sm">
                          {tamanoLegible(fila[3])}
                        </td>
                        <td className="py-2.5 pl-3 font-mono text-cuerpo-sm text-tenue">
                          {fechaCorta(fila[4])}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </>
      )}
    </div>
  )
}

function BotonExportar({ formato, ocupado, onClick, icono }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={ocupado}
      className="inline-flex items-center gap-2 rounded-lg bg-primario px-3.5 py-2 text-etiqueta-md font-medium text-sobre-primario transition-colors hover:bg-primario-enfasis disabled:opacity-50"
    >
      <Icono nombre={icono} tamano={14} />
      {ocupado ? 'Generando…' : `Exportar ${formato.toUpperCase()}`}
    </button>
  )
}