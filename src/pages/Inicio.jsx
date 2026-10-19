import { useCallback, useEffect, useState } from 'react'

import { CabeceraPagina, Esqueleto, EstadoError, EstadoVacio } from '../components/Panel.jsx'
import Icono from '../components/Icono.jsx'
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
      <section className="space-y-5">
        <CabeceraPagina titulo="Inicio" descripcion="Resumen documental · archivo cifrado" />
        <EstadoVacio
          titulo="Sin conexión con el servicio local"
          mensaje="Inicia el backend de Python para consultar el inventario. La barra inferior indica el estado."
        />
      </section>
    )
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
      <CabeceraPagina titulo="Inicio" descripcion="Resumen documental · archivo cifrado" />
      <section aria-label="Resumen documental" className="border-t border-borde pt-5">
        {estado === 'cargando' && <Esqueleto filas={4} variante="tarjetas" />}
        {estado === 'error' && <EstadoError mensaje={error} onReintentar={() => cargar()} />}
        {estado === 'listo' && (
          <div className="grid grid-cols-2 gap-y-6 pb-5 lg:grid-cols-4">
            {[
              ['Documentos', metricas.total_pdfs],
              ['Personas', metricas.total_personas],
              ['Empresas', metricas.total_empresas],
              ['Almacenamiento', metricas.total_size_str],
            ].map(([etiqueta, valor], indice) => (
              <div key={etiqueta} className="animar-entrada border-l border-borde pl-4" style={{ animationDelay: `${indice * 40}ms` }}>
                <p className="text-etiqueta-sm uppercase tracking-wider text-tenue">{etiqueta}</p>
                <p className="mt-1 font-mono text-titulo-md text-texto">{valor ?? '—'}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      <section aria-label="Accesos" className="space-y-3">
        <h2 className="text-titulo-sm">Accesos</h2>
        <div className="grid gap-1 sm:grid-cols-2">
          {[
            ['documentos', 'Ver documentos', 'documentos'],
            ['personas', 'Ver personas', 'personas'],
            ['auditoria', 'Ver auditoría', 'auditoria'],
            ['cuenta', 'Cuenta y seguridad', 'cuenta'],
          ].map(([clave, etiqueta, icono]) => (
            <button
              key={clave}
              type="button"
              onClick={() => onNavegar?.(clave)}
              className="flex items-center gap-3 rounded-md px-3 py-2.5 text-left text-etiqueta-md font-medium transition-colors hover:bg-superficie-2 hover:text-primario focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario"
            >
              <Icono nombre={icono} tamano={14} />
              {etiqueta}
            </button>
          ))}
        </div>
      </section>
    </div>
  )
}