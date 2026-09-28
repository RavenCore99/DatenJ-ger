import { useCallback, useEffect, useMemo, useState } from 'react'

import Panel, { Esqueleto, EstadoError, EstadoVacio } from '../components/Panel.jsx'
import { useApp } from '../estado/ProveedorApp.jsx'
import { backend } from '../lib/api.js'

/** Retardo de la búsqueda: evita una petición por pulsación. */
const RETARDO_BUSQUEDA_MS = 250

const CAMPOS_VACIOS = { cedula: '', nombres: '', empresa: '' }

/**
 * Panel de personas (SCRUM-24).
 *
 * Migra el panel de titulares de CustomTkinter: alta, edición, baja y el
 * conteo de documentos vinculados que el servicio calcula por titular.
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

  const cargar = useCallback(async (texto) => {
    setEstado('cargando')
    setError(null)

    try {
      setFilas(await backend.personas.listar(texto))
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

  const seleccionada = useMemo(
    () => filas.find((fila) => fila.id === seleccion) ?? null,
    [filas, seleccion],
  )

  const ejecutar = useCallback(
    async (clave, operacion, exito) => {
      setOcupado(clave)
      setAviso(null)
      try {
        const resultado = await operacion()
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
      const aviso =
        vinculados > 0
          ? `"${fila.nombres}" tiene ${vinculados} documento(s) asociado(s). Al eliminarlo quedan sin titular. ¿Continuar?`
          : `¿Eliminar a "${fila.nombres}"?`

      if (!globalThis.confirm(aviso)) return

      const resultado = await ejecutar(
        'eliminar',
        () => backend.personas.eliminar(fila.id),
        `Titular "${fila.nombres}" eliminado`,
      )
      if (resultado) setSeleccion(null)
    },
    [ejecutar],
  )

  if (!conectado) {
    return (
      <Panel titulo="Personas" descripcion="Titulares y empresas asociadas">
        <EstadoVacio
          titulo="Sin conexión con el servicio local"
          mensaje="El registro de titulares se consulta contra el servicio de Python."
        />
      </Panel>
    )
  }

  if (!autenticado) {
    return (
      <Panel titulo="Personas" descripcion="Titulares y empresas asociadas">
        <EstadoVacio
          titulo="Sesión no iniciada"
          mensaje="La pantalla de inicio de sesión todavía no está migrada (SCRUM-22)."
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
              onCambio={(evento) =>
                setAlta((actual) => ({ ...actual, [campo]: evento.target.value }))
              }
            />
          ))}

          <div className="flex items-end">
            <button
              type="submit"
              disabled={ocupado === 'crear'}
              className="rounded-lg bg-primario px-4 py-1.5 text-xs font-medium text-white disabled:opacity-50"
            >
              {ocupado === 'crear' ? 'Registrando…' : 'Registrar'}
            </button>
          </div>
        </form>
      </Panel>

      <Panel
        titulo="Titulares"
        descripcion={`${filas.length} persona(s)`}
        acciones={
          <input
            type="search"
            value={busqueda}
            onChange={(evento) => setBusqueda(evento.target.value)}
            placeholder="Buscar por cédula, nombre o empresa"
            aria-label="Buscar titulares"
            className="w-72 rounded-lg border border-borde bg-fondo px-3 py-1.5 text-xs outline-none focus:border-primario"
          />
        }
      >
        {estado === 'cargando' && <Esqueleto filas={4} />}
        {estado === 'error' && <EstadoError mensaje={error} onReintentar={() => cargar(busqueda)} />}

        {estado === 'listo' && filas.length === 0 && (
          <EstadoVacio
            titulo={busqueda ? 'Sin resultados' : 'Sin titulares'}
            mensaje={
              busqueda
                ? `Ninguna persona coincide con "${busqueda}".`
                : 'Registra el primer titular para poder asociarle documentos.'
            }
          />
        )}

        {estado === 'listo' && filas.length > 0 && (
          <table className="w-full border-collapse text-xs">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wider text-tenue">
                <th className="pb-2 font-medium">Cédula</th>
                <th className="pb-2 font-medium">Nombres</th>
                <th className="pb-2 font-medium">Empresa</th>
                <th className="pb-2 font-medium">Documentos</th>
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
                  <td className="py-2 pr-3 font-mono">{fila.cedula}</td>
                  <td className="py-2 pr-3 font-medium">{fila.nombres}</td>
                  <td className="py-2 pr-3 text-tenue">{fila.empresa}</td>
                  <td className="py-2 pr-3 font-mono">{fila.documentos ?? 0}</td>
                  <td className="py-2 text-right">
                    <button
                      type="button"
                      onClick={(evento) => {
                        evento.stopPropagation()
                        eliminar(fila)
                      }}
                      disabled={ocupado === 'eliminar'}
                      className="rounded border border-peligro/40 px-2 py-1 text-[11px] text-peligro disabled:opacity-50"
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
      <Campo etiqueta="Cédula" valor={fila.cedula} onCambio={() => {}} soloLectura />
      <Campo
        etiqueta="Nombres"
        valor={campos.nombres}
        obligatorio
        onCambio={(evento) => setCampos((actual) => ({ ...actual, nombres: evento.target.value }))}
      />
      <Campo
        etiqueta="Empresa"
        valor={campos.empresa}
        onCambio={(evento) => setCampos((actual) => ({ ...actual, empresa: evento.target.value }))}
      />

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

function Campo({ etiqueta, valor, onCambio, obligatorio = false, soloLectura = false }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] uppercase tracking-wider text-tenue">{etiqueta}</span>
      <input
        type="text"
        value={valor ?? ''}
        onChange={onCambio}
        required={obligatorio}
        readOnly={soloLectura}
        className={[
          'rounded-lg border border-borde bg-fondo px-3 py-1.5 text-xs outline-none',
          soloLectura ? 'font-mono text-tenue' : 'focus:border-primario',
        ].join(' ')}
      />
    </label>
  )
}