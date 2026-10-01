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

/** Retardo de la búsqueda: evita una petición por pulsación. */
const RETARDO_BUSQUEDA_MS = 250

const CAMPOS_VACIOS = { cedula: '', nombres: '', empresa: '' }

/**
 * Panel de personas (SCRUM-30): titulares y empresas asociadas.
 *
 * Conserva la funcionalidad del panel anterior —alta, edición, baja y el
 * conteo de documentos vinculados por titular— y adopta la composición de los
 * mockups: cabecera de página, fila de tarjetas de métrica, formulario de alta
 * y tabla de titulares con la cédula y el conteo en monoespaciada.
 */
export default function Personas() {
  const { conectado, autenticado } = useApp()

  const [busqueda, setBusqueda] = useState('')
  const [estado, setEstado] = useState('cargando')
  const [filas, setFilas] = useState([])
  const [error, setError] = useState(null)
  const [aviso, setAviso] = useState(null)
  const [ocupado, setOcupado] = useState(null)
  const [seleccion, setSeleccion] = useState(null)
  const [alta, setAlta] = useState(CAMPOS_VACIOS)
  // Catálogo de empresas (calidad de vida): alimenta el selector del formulario
  // y el panel de personal por empresa. La gestión deja de ser texto libre.
  const [catalogo, setCatalogo] = useState([])
  const [empresaFiltro, setEmpresaFiltro] = useState(null)

  const cargar = useCallback(async (texto) => {
    setEstado('cargando')
    setError(null)

    try {
      const [personas, empresas] = await Promise.all([
        backend.personas.listar(texto),
        backend.empresas.listar(),
      ])
      setFilas(personas)
      setCatalogo(empresas)
      setEstado('listo')
    } catch (fallo) {
      setError(fallo.message)
      setEstado('error')
    }
  }, [])

  useEffect(() => {
    if (!conectado || !autenticado) return undefined

    const temporizador = setTimeout(() => cargar(busqueda), RETARDO_BUSQUEDA_MS)
    return () => clearTimeout(temporizador)
  }, [busqueda, cargar, conectado, autenticado])

  /** Métricas de la fila de KPI, calculadas sobre el inventario cargado. */
  const resumen = useMemo(
    () => ({
      total: filas.length,
      conEmpresa: filas.filter((fila) => fila.empresa).length,
      conDocumentos: filas.filter((fila) => (fila.documentos ?? 0) > 0).length,
      documentos: filas.reduce((suma, fila) => suma + (fila.documentos ?? 0), 0),
    }),
    [filas],
  )

  const seleccionada = useMemo(
    () => filas.find((fila) => fila.id === seleccion) ?? null,
    [filas, seleccion],
  )

  /** Personas que se listan: todas, o las de la empresa elegida en el panel. */
  const visibles = useMemo(
    () => (empresaFiltro ? filas.filter((fila) => fila.empresa_id === empresaFiltro) : filas),
    [filas, empresaFiltro],
  )

  const empresaElegida = useMemo(
    () => catalogo.find((empresa) => empresa.id === empresaFiltro) ?? null,
    [catalogo, empresaFiltro],
  )

  const ejecutar = useCallback(
    async (clave, operacion, exito) => {
      setOcupado(clave)
      setAviso(null)
      try {
        const resultado = await operacion()
        if (exito) setAviso({ tipo: 'exito', texto: exito })
        await cargar(busqueda)
        return resultado
      } catch (fallo) {
        setAviso({ tipo: 'error', texto: fallo.message })
        return null
      } finally {
        setOcupado(null)
      }
    },
    [busqueda, cargar],
  )

  const crear = useCallback(
    async (evento) => {
      evento.preventDefault()
      const resultado = await ejecutar(
        'crear',
        () => backend.personas.crear(alta),
        `Titular "${alta.nombres}" registrado`,
      )
      if (resultado) setAlta(CAMPOS_VACIOS)
    },
    [alta, ejecutar],
  )

  const eliminar = useCallback(
    async (fila) => {
      const vinculados = fila.documentos ?? 0
      const pregunta =
        vinculados > 0
          ? `"${fila.nombres}" tiene ${vinculados} documento(s) asociado(s). Al eliminarlo quedan sin titular. ¿Continuar?`
          : `¿Eliminar a "${fila.nombres}"?`

      if (!globalThis.confirm(pregunta)) return

      const resultado = await ejecutar(
        'eliminar',
        () => backend.personas.eliminar(fila.id),
        `Titular "${fila.nombres}" eliminado`,
      )
      if (resultado) setSeleccion(null)
    },
    [ejecutar],
  )

  if (!conectado || !autenticado) {
    return (
      <Panel titulo="Personas" descripcion="Titulares y empresas asociadas">
        <EstadoVacio
          titulo={conectado ? 'Sesión no iniciada' : 'Sin conexión con el servicio local'}
          mensaje={
            conectado
              ? 'Vuelve a la pantalla de acceso para identificarte.'
              : 'El registro de titulares se consulta contra el servicio de Python.'
          }
        />
      </Panel>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <CabeceraPagina
        titulo="Titulares"
        descripcion={`${resumen.total} persona(s) · ${resumen.documentos} documento(s) asociado(s)`}
        acciones={
          <input
            type="search"
            value={busqueda}
            onChange={(evento) => setBusqueda(evento.target.value)}
            placeholder="Buscar por cédula, nombre o empresa"
            aria-label="Buscar titulares"
            className="w-72 rounded-lg border border-borde bg-superficie px-3 py-2 text-cuerpo-md outline-none transition-colors focus:border-primario"
          />
        }
      />

      {aviso && (
        <Aviso tipo={aviso.tipo} onCerrar={() => setAviso(null)}>
          {aviso.texto}
        </Aviso>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Tarjeta etiqueta="Titulares" valor={resumen.total} acento="primario" />
        <Tarjeta etiqueta="Empresas" valor={catalogo.length} />
        <Tarjeta etiqueta="Con documentos" valor={resumen.conDocumentos} acento="exito" />
        <Tarjeta etiqueta="Documentos vinculados" valor={resumen.documentos} />
      </div>

      {/* Personal por empresa (calidad de vida): el catálogo deja de ser texto
          libre, así que aquí se ve el reparto real y se filtra con un clic. */}
      {catalogo.length > 0 && (
        <Panel
          titulo="Personal por empresa"
          descripcion="Titulares y documentos agrupados por su empresa"
        >
          <ul className="flex flex-col divide-y divide-borde">
            {catalogo.map((empresa) => {
              const activa = empresa.id === empresaFiltro
              return (
                <li key={empresa.id}>
                  <button
                    type="button"
                    onClick={() => setEmpresaFiltro(activa ? null : empresa.id)}
                    aria-pressed={activa}
                    className={[
                      'flex w-full items-center gap-3 rounded-md px-3 py-2 text-left transition-colors',
                      activa ? 'bg-primario-suave text-primario' : 'hover:bg-fondo-2',
                    ].join(' ')}
                  >
                    <span className="min-w-0 flex-1 truncate font-medium">{empresa.nombre}</span>
                    <Pill tipo="primario">{empresa.personas}</Pill>
                    <span className="shrink-0 font-mono text-telemetria text-tenue">
                      {empresa.documentos} doc.
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        </Panel>
      )}

      <Panel titulo="Registrar titular" descripcion="Cédula y nombres son obligatorios">
        <form className="grid grid-cols-2 gap-4 lg:grid-cols-4" onSubmit={crear}>
          {[
            ['cedula', 'Cédula'],
            ['nombres', 'Nombres'],
            ['empresa', 'Empresa'],
          ].map(([campo, etiqueta]) => (
            <Campo
              key={campo}
              etiqueta={etiqueta}
              valor={alta[campo]}
              obligatorio={campo !== 'empresa'}
              mono={campo === 'cedula'}
              lista={campo === 'empresa' ? 'catalogo-empresas' : undefined}
              onCambio={(evento) =>
                setAlta((actual) => ({ ...actual, [campo]: evento.target.value }))
              }
            />
          ))}

          <div className="flex items-end">
            <button
              type="submit"
              disabled={ocupado === 'crear'}
              className="rounded-lg bg-primario px-4 py-2 text-etiqueta-md font-medium text-sobre-primario transition-colors hover:bg-primario-enfasis disabled:opacity-50"
            >
              {ocupado === 'crear' ? 'Registrando…' : 'Registrar'}
            </button>
          </div>
        </form>
      </Panel>

      <Panel
        titulo="Listado de titulares"
        descripcion={
          empresaElegida
            ? `${visibles.length} de ${filas.length} persona(s) · ${empresaElegida.nombre}`
            : `${filas.length} persona(s)`
        }
      >
        {empresaElegida && (
          <p className="mb-3 flex items-center gap-2 text-cuerpo-sm text-tenue">
            Filtrando por empresa
            <button
              type="button"
              onClick={() => setEmpresaFiltro(null)}
              className="text-primario transition-colors hover:underline"
            >
              Quitar filtro
            </button>
          </p>
        )}

        {estado === 'cargando' && <Esqueleto filas={4} variante="tabla" />}
        {estado === 'error' && <EstadoError mensaje={error} onReintentar={() => cargar(busqueda)} />}

        {estado === 'listo' && visibles.length === 0 && (
          <EstadoVacio
            titulo={busqueda ? 'Sin resultados' : 'Sin titulares'}
            mensaje={
              empresaElegida
                ? `Nadie está asociado a "${empresaElegida.nombre}" todavía.`
                : busqueda
                  ? `Ninguna persona coincide con "${busqueda}".`
                  : 'Registra el primer titular para poder asociarle documentos.'
            }
          />
        )}

        {estado === 'listo' && visibles.length > 0 && (
          <table className="w-full border-collapse text-cuerpo-md">
            <thead>
              <tr className="text-left text-etiqueta-sm uppercase tracking-wider text-tenue">
                <th className="pb-2 font-medium">Cédula</th>
                <th className="pb-2 font-medium">Nombres</th>
                <th className="pb-2 font-medium">Empresa</th>
                <th className="pb-2 font-medium">Documentos</th>
                <th className="pb-2" />
              </tr>
            </thead>
            <tbody>
              {visibles.map((fila, indice) => (
                <tr
                  key={fila.id}
                  onClick={() => setSeleccion(fila.id === seleccion ? null : fila.id)}
                  style={{ animationDelay: `${Math.min(indice, 12) * 18}ms` }}
                  className={[
                    'animar-entrada cursor-pointer border-t border-borde transition-colors',
                    fila.id === seleccion ? 'bg-primario-suave/60' : 'hover:bg-fondo-2',
                  ].join(' ')}
                >
                  <td className="py-2.5 pr-3 font-mono text-cuerpo-sm">{fila.cedula}</td>
                  <td className="py-2.5 pr-3 font-medium">{fila.nombres}</td>
                  <td className="py-2.5 pr-3 text-texto-2">{fila.empresa || '—'}</td>
                  <td className="py-2.5 pr-3">
                    <Pill tipo={(fila.documentos ?? 0) > 0 ? 'primario' : 'neutro'}>
                      {fila.documentos ?? 0}
                    </Pill>
                  </td>
                  <td className="py-2.5 text-right">
                    <button
                      type="button"
                      onClick={(evento) => {
                        evento.stopPropagation()
                        eliminar(fila)
                      }}
                      disabled={ocupado === 'eliminar'}
                      className="rounded border border-peligro/40 px-2 py-1 text-etiqueta-sm text-peligro transition-colors hover:bg-peligro/5 disabled:opacity-50"
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      {seleccionada && (
        <Panel titulo="Titular seleccionado" descripcion={seleccionada.nombres}>
          <FormularioPersona
            key={seleccionada.id}
            fila={seleccionada}
            ocupado={ocupado === 'guardar'}
            onGuardar={(cambios) =>
              ejecutar(
                'guardar',
                () => backend.personas.actualizar(seleccionada.id, cambios),
                'Titular actualizado',
              )
            }
          />
        </Panel>
      )}

      {/* Una sola lista de sugerencias para los dos formularios: repetirla
          dentro de cada uno dejaría dos elementos con el mismo id. */}
      <ListaDeEmpresas catalogo={catalogo} />
    </div>
  )
}

/** Edición de un titular. La cédula se conserva: identifica el registro. */
function FormularioPersona({ fila, ocupado, onGuardar }) {
  const [campos, setCampos] = useState({
    nombres: fila.nombres ?? '',
    empresa: fila.empresa ?? '',
  })

  return (
    <form
      className="grid grid-cols-2 gap-4 lg:grid-cols-3"
      onSubmit={(evento) => {
        evento.preventDefault()
        onGuardar(campos)
      }}
    >
      <Campo etiqueta="Cédula" valor={fila.cedula} onCambio={() => {}} soloLectura mono />
      <Campo
        etiqueta="Nombres"
        valor={campos.nombres}
        obligatorio
        onCambio={(evento) => setCampos((actual) => ({ ...actual, nombres: evento.target.value }))}
      />
      <Campo
        etiqueta="Empresa"
        valor={campos.empresa}
        lista="catalogo-empresas"
        onCambio={(evento) => setCampos((actual) => ({ ...actual, empresa: evento.target.value }))}
      />

      <div className="col-span-2 flex items-end lg:col-span-3">
        <button
          type="submit"
          disabled={ocupado}
          className="rounded-lg bg-primario px-4 py-2 text-etiqueta-md font-medium text-sobre-primario transition-colors hover:bg-primario-enfasis disabled:opacity-50"
        >
          {ocupado ? 'Guardando…' : 'Guardar cambios'}
        </button>
      </div>
    </form>
  )
}

/** Lista de sugerencias del catálogo, compartida por los dos formularios. */
function ListaDeEmpresas({ catalogo }) {
  return (
    <datalist id="catalogo-empresas">
      {catalogo.map((empresa) => (
        <option key={empresa.id} value={empresa.nombre} />
      ))}
    </datalist>
  )
}

function Campo({
  etiqueta,
  valor,
  onCambio,
  obligatorio = false,
  soloLectura = false,
  mono = false,
  lista,
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-etiqueta-sm text-texto">{etiqueta}</span>
      <input
        type="text"
        value={valor ?? ''}
        onChange={onCambio}
        required={obligatorio}
        readOnly={soloLectura}
        list={lista}
        className={[
          'rounded-lg border border-borde bg-fondo px-3 py-2 text-cuerpo-md outline-none transition-colors',
          mono ? 'font-mono' : '',
          soloLectura ? 'text-tenue' : 'focus:border-primario',
        ].join(' ')}
      />
    </label>
  )
}