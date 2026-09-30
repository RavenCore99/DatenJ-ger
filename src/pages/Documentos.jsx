import { useCallback, useEffect, useMemo, useState } from 'react'

import Panel, { Esqueleto, EstadoError, EstadoVacio } from '../components/Panel.jsx'
import { useApp } from '../estado/ProveedorApp.jsx'
import { backend } from '../lib/api.js'
import { elegirArchivo, guardarArchivo } from '../lib/escritorio.js'
import { fechaCorta, tamanoLegible, titular } from '../lib/formato.js'

/** Retardo de la búsqueda: evita una petición por pulsación. */
const RETARDO_BUSQUEDA_MS = 250

/**
 * Panel documental (SCRUM-23).
 *
 * Migra la funcionalidad del panel de PDFs de CustomTkinter: inventario con
 * búsqueda, alta de PDF (el cifrado lo hace el backend), edición del titular y
 * la descripción, descarga descifrada y eliminación.
 */
export default function Documentos() {
  const { conectado, autenticado } = useApp()

  const [busqueda, setBusqueda] = useState('')
  const [estado, setEstado] = useState('cargando')
  const [filas, setFilas] = useState([])
  const [error, setError] = useState(null)
  const [aviso, setAviso] = useState(null)
  const [ocupado, setOcupado] = useState(null)
  const [seleccion, setSeleccion] = useState(null)

  const cargar = useCallback(async (texto) => {
    setEstado('cargando')
    setError(null)

    try {
      setFilas(await backend.documentos.listar(texto))
      setEstado('listo')
    } catch (fallo) {
      setError(fallo.message)
      setEstado('error')
    }
  }, [])

  // Búsqueda con retardo: el listado se recarga al cambiar el término.
  useEffect(() => {
    if (!conectado || !autenticado) return undefined

    const temporizador = setTimeout(() => cargar(busqueda), RETARDO_BUSQUEDA_MS)
    return () => clearTimeout(temporizador)
  }, [busqueda, cargar, conectado, autenticado])

  const seleccionada = useMemo(
    () => filas.find((fila) => fila.id === seleccion) ?? null,
    [filas, seleccion],
  )

  /** Ejecuta una operación marcándola como ocupada y reportando el resultado. */
  const ejecutar = useCallback(
    async (clave, operacion, exito) => {
      setOcupado(clave)
      setAviso(null)
      try {
        const resultado = await operacion()
        if (resultado?.cancelado) return null
        if (exito) setAviso(exito)
        await cargar(busqueda)
        return resultado
      } catch (fallo) {
        setAviso(`Error: ${fallo.message}`)
        return null
      } finally {
        setOcupado(null)
      }
    },
    [busqueda, cargar],
  )

  const agregar = useCallback(async () => {
    const archivo = await elegirArchivo()
    if (archivo?.cancelado) return
    if (archivo?.error) {
      setAviso(`Error: ${archivo.error}`)
      return
    }

    await ejecutar(
      'agregar',
      () => backend.documentos.crear({
        nombre: archivo.nombre,
        contenido_b64: archivo.contenido_b64,
      }),
      `Documento "${archivo.nombre}" cifrado y guardado`,
    )
  }, [ejecutar])

  const descargar = useCallback(
    async (fila) => {
      await ejecutar('descargar', async () => {
        const descarga = await backend.documentos.descargar(fila.id)
        return guardarArchivo({
          nombre: descarga.nombre,
          contenido_b64: descarga.contenido_b64,
        })
      }, `Documento "${fila.nombre}" descargado`)
    },
    [ejecutar],
  )

  const eliminar = useCallback(
    async (fila) => {
      const confirmado = globalThis.confirm(
        `¿Eliminar "${fila.nombre}"? Esta acción no se puede deshacer.`,
      )
      if (!confirmado) return

      const resultado = await ejecutar(
        'eliminar',
        () => backend.documentos.eliminar(fila.id),
        `Documento "${fila.nombre}" eliminado`,
      )
      if (resultado) setSeleccion(null)
    },
    [ejecutar],
  )

  if (!conectado) {
    return (
      <Panel titulo="Documentos" descripcion="PDFs cifrados del archivo documental">
        <EstadoVacio
          titulo="Sin conexión con el servicio local"
          mensaje="El inventario se consulta contra el servicio de Python. Revisa la barra inferior."
        />
      </Panel>
    )
  }

  if (!autenticado) {
    return (
      <Panel titulo="Documentos" descripcion="PDFs cifrados del archivo documental">
        <EstadoVacio
          titulo="Sesión no iniciada"
          mensaje="La pantalla de inicio de sesión todavía no está migrada (SCRUM-22): mientras tanto el servicio local hereda la sesión de la aplicación de escritorio."
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
        titulo="Inventario"
        descripcion={`${filas.length} documento(s)`}
        acciones={
          <>
            <input
              type="search"
              value={busqueda}
              onChange={(evento) => setBusqueda(evento.target.value)}
              placeholder="Buscar por nombre, titular o empresa"
              aria-label="Buscar documentos"
              className="w-72 rounded-lg border border-borde bg-fondo px-3 py-1.5 text-xs outline-none focus:border-primario"
            />
            <button
              type="button"
              onClick={agregar}
              disabled={ocupado === 'agregar'}
              className="rounded-lg bg-primario px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
            >
              {ocupado === 'agregar' ? 'Cifrando…' : 'Agregar PDF'}
            </button>
          </>
        }
      >
        {estado === 'cargando' && <Esqueleto filas={5} />}
        {estado === 'error' && <EstadoError mensaje={error} onReintentar={() => cargar(busqueda)} />}

        {estado === 'listo' && filas.length === 0 && (
          <EstadoVacio
            titulo={busqueda ? 'Sin resultados' : 'Archivo vacío'}
            mensaje={
              busqueda
                ? `Ningún documento coincide con "${busqueda}".`
                : 'Agrega el primer PDF: se cifra antes de guardarse y el original no se conserva.'
            }
          />
        )}

        {estado === 'listo' && filas.length > 0 && (
          <table className="w-full border-collapse text-xs">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wider text-tenue">
                <th className="pb-2 font-medium">Documento</th>
                <th className="pb-2 font-medium">Titular</th>
                <th className="pb-2 font-medium">Tamaño</th>
                <th className="pb-2 font-medium">Fecha</th>
                <th className="pb-2" />
              </tr>
            </thead>
            <tbody>
              {filas.map((fila) => (
                <tr
                  key={fila.id}
                  onClick={() => setSeleccion(fila.id === seleccion ? null : fila.id)}
                  className={[
                    'cursor-pointer border-t border-borde',
                    fila.id === seleccion ? 'bg-primario/5' : 'hover:bg-fondo',
                  ].join(' ')}
                >
                  <td className="py-2 pr-3">
                    <span className="font-medium">{fila.nombre}</span>
                    {fila.descripcion && (
                      <span className="block text-[11px] text-tenue">{fila.descripcion}</span>
                    )}
                  </td>
                  <td className="py-2 pr-3 text-tenue">{titular(fila)}</td>
                  <td className="py-2 pr-3 font-mono">{tamanoLegible(fila.tamano)}</td>
                  <td className="py-2 pr-3 font-mono text-tenue">{fechaCorta(fila.fecha_subida)}</td>
                  <td className="py-2 text-right">
                    <button
                      type="button"
                      onClick={(evento) => {
                        evento.stopPropagation()
                        descargar(fila)
                      }}
                      disabled={ocupado === 'descargar'}
                      className="rounded border border-borde px-2 py-1 text-[11px] hover:border-primario hover:text-primario disabled:opacity-50"
                    >
                      Descargar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      {seleccionada && (
        <Panel
          titulo="Documento seleccionado"
          descripcion={seleccionada.nombre}
          acciones={
            <button
              type="button"
              onClick={() => eliminar(seleccionada)}
              disabled={ocupado === 'eliminar'}
              className="rounded-lg border border-peligro/40 px-3 py-1.5 text-xs font-medium text-peligro disabled:opacity-50"
            >
              {ocupado === 'eliminar' ? 'Eliminando…' : 'Eliminar'}
            </button>
          }
        >
          <FormularioDocumento
            key={seleccionada.id}
            fila={seleccionada}
            ocupado={ocupado === 'guardar'}
            onGuardar={(cambios) =>
              ejecutar(
                'guardar',
                () => backend.documentos.actualizar(seleccionada.id, cambios),
                'Documento actualizado',
              )
            }
          />
        </Panel>
      )}
    </div>
  )
}

/** Edición de nombre, descripción y titular de un documento. */
function FormularioDocumento({ fila, ocupado, onGuardar }) {
  const [campos, setCampos] = useState({
    nombre: fila.nombre ?? '',
    descripcion: fila.descripcion ?? '',
    cedula: fila.cedula ?? '',
    nombres: fila.nombres ?? '',
    empresa: fila.empresa ?? '',
  })

  const cambiar = (campo) => (evento) =>
    setCampos((actual) => ({ ...actual, [campo]: evento.target.value }))

  return (
    <form
      className="grid grid-cols-2 gap-4 lg:grid-cols-3"
      onSubmit={(evento) => {
        evento.preventDefault()
        onGuardar(campos)
      }}
    >
      <Campo etiqueta="Nombre" valor={campos.nombre} onCambio={cambiar('nombre')} obligatorio />
      <Campo etiqueta="Descripción" valor={campos.descripcion} onCambio={cambiar('descripcion')} />
      <Campo etiqueta="Cédula" valor={campos.cedula} onCambio={cambiar('cedula')} />
      <Campo etiqueta="Nombres del titular" valor={campos.nombres} onCambio={cambiar('nombres')} />
      <Campo etiqueta="Empresa" valor={campos.empresa} onCambio={cambiar('empresa')} />

      <div className="col-span-2 flex items-end lg:col-span-3">
        <button
          type="submit"
          disabled={ocupado}
          className="rounded-lg bg-primario px-4 py-1.5 text-xs font-medium text-white disabled:opacity-50"
        >
          {ocupado ? 'Guardando…' : 'Guardar cambios'}
        </button>
      </div>
    </form>
  )
}

function Campo({ etiqueta, valor, onCambio, obligatorio = false }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] uppercase tracking-wider text-tenue">{etiqueta}</span>
      <input
        type="text"
        value={valor}
        onChange={onCambio}
        required={obligatorio}
        className="rounded-lg border border-borde bg-fondo px-3 py-1.5 text-xs outline-none focus:border-primario"
      />
    </label>
  )
}