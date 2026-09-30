import { useCallback, useEffect, useState } from 'react'

import Panel, { Esqueleto, EstadoError, EstadoVacio } from '../components/Panel.jsx'
import { useApp } from '../estado/ProveedorApp.jsx'
import { backend } from '../lib/api.js'

/**
 * Panel de inicio: resumen documental.
 *
 * Las métricas vienen de `reportes.estadisticas` del backend (mismo cálculo
 * que el dashboard de `ui_components.py`).
 */
export default function Inicio({ onNavegar }) {
  const { conectado, estadoBackend } = useApp()
  const [estado, setEstado] = useState('cargando')
  const [metricas, setMetricas] = useState(null)
  const [error, setError] = useState(null)

  const cargar = useCallback(async (senal) => {
    setEstado('cargando')
    setError(null)
    try {
      const datos = await backend.reportes.estadisticas()
      setMetricas(datos)
      setEstado('listo')
    } catch (fallo) {
      if (fallo?.name === 'AbortError') return
      setError(fallo.message)
      setEstado('error')
    }
  }, [])

  useEffect(() => {
    if (!conectado) {
      setEstado(estadoBackend === 'verificando' ? 'cargando' : 'sin_servicio')
      return undefined
    }
    const control = new AbortController()
    cargar(control.signal)
    return () => control.abort()
  }, [conectado, estadoBackend, cargar])

  if (estado === 'sin_servicio') {
    return (
      <Panel titulo="Resumen documental" descripcion="Métricas del archivo cifrado">
        <EstadoVacio
          titulo="Sin conexión con el servicio local"
          mensaje="Inicia el backend de Python para consultar el inventario. La barra inferior indica el estado."
        />
      </Panel>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <Panel titulo="Resumen documental" descripcion="Métricas del archivo cifrado">
        {estado === 'cargando' && <Esqueleto filas={2} />}
        {estado === 'error' && <EstadoError mensaje={error} onReintentar={() => cargar()} />}
        {estado === 'listo' && (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Metrica etiqueta="Documentos" valor={metricas.total_pdfs} />
            <Metrica etiqueta="Personas" valor={metricas.total_personas} />
            <Metrica etiqueta="Empresas" valor={metricas.total_empresas} />
            <Metrica etiqueta="Almacenamiento" valor={metricas.total_size_str} />
          </div>
        )}
      </Panel>

      <Panel titulo="Accesos" descripcion="Secciones del sistema">
        <div className="flex flex-wrap gap-2">
          {[
            ['documentos', 'Ver documentos'],
            ['personas', 'Ver personas'],
            ['auditoria', 'Ver auditoría'],
            ['cuenta', 'Cuenta y seguridad'],
          ].map(([clave, etiqueta]) => (
            <button
              key={clave}
              type="button"
              onClick={() => onNavegar?.(clave)}
              className="rounded-lg border border-borde px-3 py-1.5 text-xs font-medium transition-colors hover:border-primario hover:text-primario"
            >
              {etiqueta}
            </button>
          ))}
        </div>
      </Panel>
    </div>
  )
}

function Metrica({ etiqueta, valor }) {
  return (
    <div className="rounded-panel border border-borde px-4 py-3">
      <p className="text-[11px] uppercase tracking-wider text-tenue">{etiqueta}</p>
      <p className="mt-1 font-mono text-xl">{valor ?? '—'}</p>
    </div>
  )
}