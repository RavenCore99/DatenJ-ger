import { useCallback, useEffect, useMemo, useState } from 'react'

import { Esqueleto, EstadoError, EstadoVacio } from '../components/Panel.jsx'
import { useApp } from '../estado/ProveedorApp.jsx'
import { backend } from '../lib/api.js'
import { elegirArchivo, guardarArchivo } from '../lib/escritorio.js'
import { fechaCorta, tamanoLegible, titular } from '../lib/formato.js'

/** Retardo de la búsqueda: evita una petición por pulsación. */
const RETARDO_BUSQUEDA_MS = 250

/**
 * Panel documental (SCRUM-29): inventario de PDFs cifrados con la identidad del
 * sistema de diseño.
 *
 * Conserva toda la funcionalidad del panel anterior —alta con cifrado en el
 * backend, edición del titular, descarga descifrada y baja— y adopta el
 * ordenamiento del mockup: título, barra de herramientas con búsqueda y
 * filtro por empresa, tabla de expedientes y panel de detalle al costado.
 *
 * Dos columnas del mockup no se construyen porque el sistema no las respalda:
 * **Tipo de documento** (la clasificación por tipo es la evaluación de la
 * Fase 6, todavía no existe) e **Integridad** como hash SHA-256 por fila (los
 * documentos se cifran con AES-256-GCM pero no se guarda un hash propio). En su
 * lugar, la columna de integridad muestra el cifrado real de cada expediente.
 */
export default function Documentos() {
  const { conectado, autenticado } = useApp()

  const [busqueda, setBusqueda] = useState('')
  const [empresa, setEmpresa] = useState('')
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

  /** Empresas presentes en el inventario cargado, para el filtro. */
  const empresas = useMemo(
    () => [...new Set(filas.map((fila) => fila.empresa).filter(Boolean))].sort(),
    [filas],
  )

  const visibles = useMemo(
    () => (empresa ? filas.filter((fila) => fila.empresa === empresa) : filas),
    [filas, empresa],
  )

  const seleccionada = useMemo(
    () => visibles.find((fila) => fila.id === seleccion) ?? null,
    [visibles, seleccion],
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
      () =>
        backend.documentos.crear({
          nombre: archivo.nombre,
          contenido_b64: archivo.contenido_b64,
        }),
      `Documento "${archivo.nombre}" cifrado y guardado`,
    )
  }, [ejecutar])

  const descargar = useCallback(
    async (fila) => {
      await ejecutar(
        'descargar',
        async () => {
          const descarga = await backend.documentos.descargar(fila.id)
          return guardarArchivo({
            nombre: descarga.nombre,
            contenido_b64: descarga.contenido_b64,
          })
        },
        `Documento "${fila.nombre}" descargado`,
      )
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
      <EstadoVacio
        titulo="Sin conexión con el servicio local"
        mensaje="El inventario se consulta contra el servicio de Python. Revisa la franja inferior para ver el estado."
      />
    )
  }

  if (!autenticado) {
    return (
      <EstadoVacio
        titulo="Sesión no iniciada"
        mensaje="Vuelve a la pantalla de acceso para identificarte."
      />
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-marca text-titulo-md tracking-tight">Gestión documental</h1>
          <p className="text-cuerpo-sm text-tenue">
            {filas.length === 0
              ? 'Sin expedientes registrados'
              : `${visibles.length} de ${filas.length} expediente(s) · cifrados con AES-256-GCM`}
          </p>
        </div>

        <button
          type="button"
          onClick={agregar}
          disabled={ocupado === 'agregar'}
          className="rounded-lg bg-primario px-3.5 py-2 text-etiqueta-md font-medium text-sobre-primario transition-colors hover:bg-primario-enfasis disabled:opacity-50"
        >
          {ocupado === 'agregar' ? 'Cifrando…' : 'Agregar documento'}
        </button>
      </header>

      {aviso && <Aviso texto={aviso} onCerrar={() => setAviso(null)} />}

      <div className="flex flex-wrap items-center gap-2">
        <input
          type="search"
          value={busqueda}
          onChange={(evento) => setBusqueda(evento.target.value)}
          placeholder="Buscar por nombre, descripción, cédula o empresa"
          aria-label="Buscar documentos"
          className="min-w-[18rem] flex-1 rounded-lg border border-borde bg-superficie px-3 py-2 text-cuerpo-md outline-none transition-colors focus:border-primario"
        />

        <select
          value={empresa}
          onChange={(evento) => setEmpresa(evento.target.value)}
          aria-label="Filtrar por empresa"
          className="rounded-lg border border-borde bg-superficie px-3 py-2 text-cuerpo-md outline-none focus:border-primario"
        >
          <option value="">Todas las empresas</option>
          {empresas.map((nombre) => (
            <option key={nombre} value={nombre}>
              {nombre}
            </option>
          ))}
        </select>

        <button
          type="button"
          onClick={() => cargar(busqueda)}
          disabled={estado === 'cargando'}
          className="rounded-lg border border-borde px-3 py-2 text-etiqueta-md text-tenue transition-colors hover:border-primario hover:text-primario disabled:opacity-50"
        >
          {estado === 'cargando' ? 'Actualizando…' : 'Refrescar'}
        </button>
      </div>

      <div className="flex items-start gap-4">
        <section className="min-w-0 flex-1 overflow-hidden rounded-panel border border-borde bg-superficie">
          {estado === 'cargando' && filas.length === 0 && (
            <div className="p-5">
              <Esqueleto filas={5} />
            </div>
          )}

          {estado === 'error' && (
            <div className="p-5">
              <EstadoError mensaje={error} onReintentar={() => cargar(busqueda)} />
            </div>
          )}

          {estado === 'listo' && visibles.length === 0 && (
            <EstadoVacio
              titulo={busqueda || empresa ? 'Sin resultados' : 'Archivo vacío'}
              mensaje={
                busqueda || empresa
                  ? 'Ningún expediente coincide con el filtro aplicado.'
                  : 'Agrega el primer PDF: se cifra antes de guardarse y el original no se conserva.'
              }
              accion={
                busqueda || empresa ? (
                  <button
                    type="button"
                    onClick={() => {
                      setBusqueda('')
                      setEmpresa('')
                    }}
                    className="mt-2 rounded-lg border border-borde px-3 py-1.5 text-etiqueta-sm hover:border-primario hover:text-primario"
                  >
                    Limpiar filtros
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={agregar}
                    className="mt-2 rounded-lg bg-primario px-3 py-1.5 text-etiqueta-sm font-medium text-sobre-primario"
                  >
                    Agregar documento
                  </button>
                )
              }
            />
          )}

          {visibles.length > 0 && (
            <table className="w-full border-collapse text-cuerpo-md">
              <thead>
                <tr className="border-b border-borde text-left text-etiqueta-sm uppercase tracking-wider text-tenue">
                  <th className="px-5 py-3 font-medium">Documento</th>
                  <th className="px-3 py-3 font-medium">Titular</th>
                  <th className="px-3 py-3 font-medium">Empresa</th>
                  <th className="px-3 py-3 font-medium">Tamaño</th>
                  <th className="px-3 py-3 font-medium">Fecha</th>
                  <th className="px-3 py-3 font-medium">Integridad</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody>
                {visibles.map((fila, indice) => (
                  <tr
                    key={fila.id}
                    onClick={() => setSeleccion(fila.id === seleccion ? null : fila.id)}
                    style={{ animationDelay: `${Math.min(indice, 12) * 18}ms` }}
                    className={[
                      'animar-entrada cursor-pointer border-b border-borde transition-colors last:border-b-0',
                      fila.id === seleccion ? 'bg-primario-suave/60' : 'hover:bg-fondo-2',
                    ].join(' ')}
                  >
                    <td className="px-5 py-3">
                      <span className="font-medium">{fila.nombre}</span>
                      {fila.descripcion && (
                        <span className="block text-cuerpo-sm text-tenue">{fila.descripcion}</span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-texto-2">{titular(fila)}</td>
                    <td className="px-3 py-3 text-texto-2">{fila.empresa ?? '—'}</td>
                    <td className="px-3 py-3 font-mono text-cuerpo-sm">
                      {tamanoLegible(fila.tamano)}
                    </td>
                    <td className="px-3 py-3 font-mono text-cuerpo-sm text-tenue">
                      {fechaCorta(fila.fecha_subida)}
                    </td>
                    <td className="px-3 py-3">
                      <span className="inline-flex items-center gap-1.5 rounded border border-exito/40 bg-exito/5 px-2 py-0.5 font-mono text-telemetria text-exito">
                        <span
                          aria-hidden="true"
                          className="inline-block h-1.5 w-1.5 rounded-full bg-exito"
                        />
                        AES-256-GCM
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button
                        type="button"
                        onClick={(evento) => {
                          evento.stopPropagation()
                          descargar(fila)
                        }}
                        disabled={ocupado === 'descargar'}
                        className="rounded border border-borde px-2 py-1 text-etiqueta-sm transition-colors hover:border-primario hover:text-primario disabled:opacity-50"
                      >
                        Descargar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        {seleccionada && (
          <aside className="hidden w-80 shrink-0 flex-col rounded-panel border border-borde bg-superficie xl:flex">
            <header className="flex items-start justify-between gap-3 border-b border-borde px-4 py-3">
              <div className="min-w-0">
                <p className="text-etiqueta-sm uppercase tracking-wider text-tenue">Expediente</p>
                <p className="truncate font-medium" title={seleccionada.nombre}>
                  {seleccionada.nombre}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSeleccion(null)}
                aria-label="Cerrar el detalle"
                className="shrink-0 rounded px-1.5 text-tenue transition-colors hover:text-texto"
              >
                ✕
              </button>
            </header>

            <div className="flex flex-col gap-3 px-4 py-4">
              <dl className="flex flex-col gap-2 text-cuerpo-sm">
                <Dato etiqueta="Tamaño" valor={tamanoLegible(seleccionada.tamano)} mono />
                <Dato etiqueta="Fecha" valor={fechaCorta(seleccionada.fecha_subida)} mono />
                <Dato etiqueta="Titular" valor={titular(seleccionada)} />
                <Dato etiqueta="Empresa" valor={seleccionada.empresa ?? '—'} />
              </dl>

              <p className="rounded-lg border border-exito/40 bg-exito/5 px-3 py-2 text-cuerpo-sm text-exito">
                Cifrado en reposo con AES-256-GCM. Se descifra en memoria al abrirlo.
              </p>

              <div className="flex items-center gap-2 border-t border-borde pt-3">
                <button
                  type="button"
                  onClick={() => descargar(seleccionada)}
                  disabled={ocupado === 'descargar'}
                  className="rounded-lg border border-borde px-3 py-1.5 text-etiqueta-sm transition-colors hover:border-primario hover:text-primario disabled:opacity-50"
                >
                  Exportar
                </button>
                <button
                  type="button"
                  onClick={() => eliminar(seleccionada)}
                  disabled={ocupado === 'eliminar'}
                  className="ml-auto rounded-lg border border-peligro/40 px-3 py-1.5 text-etiqueta-sm font-medium text-peligro transition-colors hover:bg-peligro/5 disabled:opacity-50"
                >
                  {ocupado === 'eliminar' ? 'Eliminando…' : 'Eliminar'}
                </button>
              </div>
            </div>

            <div className="border-t border-borde px-4 py-4">
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
            </div>
          </aside>
        )}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */

function Dato({ etiqueta, valor, mono }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="shrink-0 text-tenue">{etiqueta}</dt>
      <dd className={`truncate text-right ${mono ? 'font-mono' : ''}`} title={valor}>
        {valor}
      </dd>
    </div>
  )
}

function Aviso({ texto, onCerrar }) {
  const esError = texto.startsWith('Error')

  return (
    <div
      role="status"
      className={[
        'flex items-center justify-between gap-4 rounded-lg border px-4 py-2 text-cuerpo-sm',
        esError ? 'border-peligro/40 bg-peligro/5 text-peligro' : 'border-exito/40 bg-exito/5 text-exito',
      ].join(' ')}
    >
      <span>{texto}</span>
      <button type="button" onClick={onCerrar} className="font-mono text-etiqueta-sm">
        cerrar
      </button>
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
      className="flex flex-col gap-3"
      onSubmit={(evento) => {
        evento.preventDefault()
        onGuardar(campos)
      }}
    >
      <p className="text-etiqueta-sm uppercase tracking-wider text-tenue">Editar metadatos</p>

      <Campo etiqueta="Nombre" valor={campos.nombre} onCambio={cambiar('nombre')} obligatorio />
      <Campo etiqueta="Descripción" valor={campos.descripcion} onCambio={cambiar('descripcion')} />
      <Campo etiqueta="Cédula" valor={campos.cedula} onCambio={cambiar('cedula')} />
      <Campo etiqueta="Nombres del titular" valor={campos.nombres} onCambio={cambiar('nombres')} />
      <Campo etiqueta="Empresa" valor={campos.empresa} onCambio={cambiar('empresa')} />

      <button
        type="submit"
        disabled={ocupado}
        className="mt-1 rounded-lg bg-primario px-3.5 py-2 text-etiqueta-md font-medium text-sobre-primario transition-colors hover:bg-primario-enfasis disabled:opacity-50"
      >
        {ocupado ? 'Guardando…' : 'Guardar cambios'}
      </button>
    </form>
  )
}

function Campo({ etiqueta, valor, onCambio, obligatorio = false }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-etiqueta-sm text-texto">{etiqueta}</span>
      <input
        type="text"
        value={valor}
        onChange={onCambio}
        required={obligatorio}
        className="rounded-lg border border-borde bg-fondo px-3 py-1.5 text-cuerpo-md outline-none transition-colors focus:border-primario"
      />
    </label>
  )
}