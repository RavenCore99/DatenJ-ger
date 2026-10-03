import { useEffect, useRef, useState } from 'react'

import Icono from './Icono.jsx'
import { animar } from '../lib/movimiento.js'
import { fechaCorta, tamanoLegible, titular } from '../lib/formato.js'
import { useCerrarConEscape } from '../lib/modal.js'

/**
 * Modales de documento (SCRUM-88): **detalles** y **editar**.
 *
 * La aplicación anterior abría cada uno en su propia ventana (`CTkToplevel`:
 * «Detalles PDF», «Editar PDF»). Aquí son capas modales sobre el panel, con el
 * sistema de diseño, igual que el alta y el visor: una sola forma de abrir algo
 * encima de la pantalla, no tres.
 *
 * `MarcoModal` concentra lo común —velo, tarjeta, `Esc`, foco y animación de
 * entrada— para que los dos modales solo se ocupen de su contenido.
 */

/** Cáscara compartida: velo, tarjeta, cierre con `Esc` y animación de entrada. */
function MarcoModal({ id, titulo, descripcion, onCerrar, children, ancho = 'max-w-xl' }) {
  const panel = useRef(null)
  // `Esc` y el foco de entrada, sin robar el foco en cada pulsación
  // (ver `src/lib/modal.js`).
  const cerrar = useCerrarConEscape(onCerrar)

  useEffect(() => {
    animar(panel.current, {
      opacity: [0, 1],
      translateY: [14, 0],
      scale: [0.985, 1],
      duration: 240,
      ease: 'outQuad',
    })
  }, [])

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={id}
      className="fixed inset-0 z-50 flex items-center justify-center p-6"
    >
      <button
        type="button"
        aria-label="Cerrar"
        onClick={onCerrar}
        className="absolute inset-0 cursor-default bg-texto/40 backdrop-blur-sm"
      />

      <div
        ref={panel}
        className={`superficie-cristal relative flex max-h-[86vh] w-full ${ancho} flex-col overflow-hidden rounded-panel border border-borde shadow-flotante`}
      >
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-borde px-6 py-4">
          <div className="min-w-0">
            <h2 id={id} className="font-marca text-titulo-sm tracking-tight">
              {titulo}
            </h2>
            {descripcion && <p className="text-cuerpo-sm text-tenue">{descripcion}</p>}
          </div>

          <button
            ref={cerrar}
            type="button"
            onClick={onCerrar}
            aria-label="Cerrar"
            className="shrink-0 rounded px-1.5 text-tenue transition-colors hover:text-texto"
          >
            <Icono nombre="cerrar" tamano={16} />
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">{children}</div>
      </div>
    </div>
  )
}

/** Fila de dato: etiqueta a la izquierda, valor a la derecha. */
function Dato({ etiqueta, valor, mono = false }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-borde py-2 last:border-b-0">
      <dt className="shrink-0 text-cuerpo-sm text-tenue">{etiqueta}</dt>
      <dd className={`min-w-0 truncate text-right text-cuerpo-md ${mono ? 'font-mono' : ''}`} title={valor}>
        {valor}
      </dd>
    </div>
  )
}

/**
 * Detalles del expediente: todo lo que el sistema guarda de él, más las
 * acciones que antes vivían sueltas en la fila de la tabla.
 */
export function ModalDetalle({
  documento,
  ocupado,
  onVer,
  onExportar,
  onEliminar,
  onEditar,
  onCerrar,
}) {
  return (
    <MarcoModal
      id="detalle-documento-titulo"
      titulo="Detalles del documento"
      descripcion="Metadatos y acciones del expediente"
      onCerrar={onCerrar}
    >
      <div className="flex flex-col gap-5">
        <dl className="flex flex-col">
          <Dato etiqueta="Nombre" valor={documento.nombre} />
          <Dato etiqueta="Descripción" valor={documento.descripcion || '—'} />
          <Dato etiqueta="Titular" valor={titular(documento)} />
          <Dato etiqueta="Cédula" valor={documento.cedula || '—'} mono />
          <Dato etiqueta="Empresa" valor={documento.empresa || '—'} />
          <Dato etiqueta="Tamaño" valor={tamanoLegible(documento.tamano)} mono />
          <Dato etiqueta="Fecha de alta" valor={fechaCorta(documento.fecha_subida)} mono />
        </dl>

        <p className="rounded-lg border border-exito/40 bg-exito/5 px-3 py-2 text-cuerpo-sm text-exito">
          Cifrado en reposo con AES-256-GCM. Se descifra en memoria al abrirlo y el original no se
          conserva.
        </p>

        <div className="flex flex-wrap items-center gap-2 border-t border-borde pt-4">
          <button
            type="button"
            onClick={onVer}
            className="inline-flex items-center gap-1.5 rounded-lg border border-borde px-3 py-1.5 text-etiqueta-sm transition-colors hover:border-primario hover:text-primario"
          >
            <Icono nombre="ojo" tamano={13} />
            Ver aquí
          </button>

          <button
            type="button"
            onClick={onEditar}
            className="inline-flex items-center gap-1.5 rounded-lg border border-borde px-3 py-1.5 text-etiqueta-sm transition-colors hover:border-primario hover:text-primario"
          >
            <Icono nombre="lapiz" tamano={13} />
            Editar
          </button>

          <button
            type="button"
            onClick={onExportar}
            disabled={ocupado === 'descargar'}
            className="inline-flex items-center gap-1.5 rounded-lg border border-borde px-3 py-1.5 text-etiqueta-sm transition-colors hover:border-primario hover:text-primario disabled:opacity-50"
          >
            <Icono nombre="descargar" tamano={13} />
            {ocupado === 'descargar' ? 'Descargando…' : 'Exportar'}
          </button>

          <button
            type="button"
            onClick={onEliminar}
            disabled={ocupado === 'eliminar'}
            className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-peligro/40 px-3 py-1.5 text-etiqueta-sm font-medium text-peligro transition-colors hover:bg-peligro/5 disabled:opacity-50"
          >
            <Icono nombre="basura" tamano={13} />
            {ocupado === 'eliminar' ? 'Eliminando…' : 'Eliminar'}
          </button>
        </div>
      </div>
    </MarcoModal>
  )
}

/**
 * Edición de los metadatos del expediente. La empresa se ofrece como lista de
 * las ya conocidas —igual que en el alta— para no sembrar duplicados con otra
 * escritura, y el nombre se exige porque es como aparece en el inventario.
 */
export function ModalEditar({ documento, empresas = [], ocupado, error, onGuardar, onCerrar }) {
  const [campos, setCampos] = useState({
    nombre: documento.nombre ?? '',
    descripcion: documento.descripcion ?? '',
    cedula: documento.cedula ?? '',
    nombres: documento.nombres ?? '',
    empresa: documento.empresa ?? '',
  })
  const [errorLocal, setErrorLocal] = useState(null)
  const fallo = error ?? errorLocal

  const cambiar = (campo) => (evento) =>
    setCampos((actual) => ({ ...actual, [campo]: evento.target.value }))

  const enviar = (evento) => {
    evento.preventDefault()

    if (!campos.nombre.trim()) {
      setErrorLocal('El documento necesita un nombre.')
      return
    }
    if (Boolean(campos.cedula) !== Boolean(campos.nombres)) {
      setErrorLocal('La cédula y los nombres del titular van juntos, o ninguno de los dos.')
      return
    }

    setErrorLocal(null)
    onGuardar({
      nombre: campos.nombre.trim(),
      descripcion: campos.descripcion.trim() || null,
      cedula: campos.cedula.trim() || null,
      nombres: campos.nombres.trim() || null,
      empresa: campos.empresa.trim() || null,
    })
  }

  return (
    <MarcoModal
      id="editar-documento-titulo"
      titulo="Editar documento"
      descripcion="Cambia los metadatos; el PDF cifrado no se toca"
      onCerrar={onCerrar}
    >
      <form className="flex flex-col gap-4" onSubmit={enviar}>
        <Campo etiqueta="Nombre" valor={campos.nombre} onCambio={cambiar('nombre')} obligatorio
               ayuda="Como aparecerá en el inventario" />

        <label className="flex flex-col gap-1">
          <span className="text-etiqueta-sm text-texto">Descripción</span>
          <textarea
            value={campos.descripcion}
            onChange={cambiar('descripcion')}
            rows={2}
            className="resize-y rounded-lg border border-borde bg-fondo px-3 py-2 text-cuerpo-md outline-none transition-colors focus:border-primario"
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <Campo etiqueta="Cédula" valor={campos.cedula} onCambio={cambiar('cedula')} mono />
          <Campo etiqueta="Nombres del titular" valor={campos.nombres} onCambio={cambiar('nombres')} />
        </div>

        <label className="flex flex-col gap-1">
          <span className="text-etiqueta-sm text-texto">Empresa</span>
          <input
            type="text"
            list="empresas-conocidas-edicion"
            value={campos.empresa}
            onChange={cambiar('empresa')}
            className="rounded-lg border border-borde bg-fondo px-3 py-2 text-cuerpo-md outline-none transition-colors focus:border-primario"
          />
          <datalist id="empresas-conocidas-edicion">
            {empresas.map((nombre) => (
              <option key={nombre} value={nombre} />
            ))}
          </datalist>
        </label>

        {fallo && (
          <p role="alert" className="rounded-lg border border-peligro/40 bg-peligro/5 px-3 py-2 text-cuerpo-sm text-peligro">
            {fallo}
          </p>
        )}

        {/* Pie del formulario: el PDF ya está cifrado en el alta; aquí no se
            reemplaza. El selector de archivo vive en AltaDocumento. */}
        <div className="flex items-center justify-between gap-3 border-t border-borde pt-4">
          <span className="min-w-0 truncate font-mono text-telemetria text-tenue" title={documento.nombre}>
            PDF cifrado · {documento.nombre}
          </span>
          <span className="flex shrink-0 items-center gap-3">
            <button
              type="button"
              onClick={onCerrar}
              className="rounded-lg border border-borde px-3.5 py-2 text-etiqueta-md font-medium transition-colors hover:border-primario hover:text-primario"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={ocupado}
              className="inline-flex items-center gap-2 rounded-lg bg-primario px-3.5 py-2 text-etiqueta-md font-medium text-sobre-primario transition-colors hover:bg-primario-enfasis disabled:opacity-50"
            >
              <Icono nombre="guardar" tamano={14} />
              {ocupado ? 'Guardando…' : 'Guardar cambios'}
            </button>
          </span>
        </div>
      </form>
    </MarcoModal>
  )
}

function Campo({ etiqueta, valor, onCambio, obligatorio = false, mono = false, ayuda }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-etiqueta-sm text-texto">{etiqueta}</span>
      <input
        type="text"
        value={valor}
        onChange={onCambio}
        required={obligatorio}
        className={[
          'rounded-lg border border-borde bg-fondo px-3 py-2 text-cuerpo-md outline-none transition-colors focus:border-primario',
          mono ? 'font-mono' : '',
        ].join(' ')}
      />
      {ayuda && <span className="text-cuerpo-sm text-tenue">{ayuda}</span>}
    </label>
  )
}