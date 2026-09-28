import Panel, { EstadoVacio } from '../components/Panel.jsx'

/**
 * Panel de personas (titulares de los documentos).
 *
 * Alcance pendiente (SCRUM-23): alta, edición, eliminación y conteo de
 * documentos vinculados por titular.
 */
export default function Personas() {
  return (
    <Panel titulo="Personas" descripcion="Titulares y empresas asociadas">
      <EstadoVacio
        titulo="Pantalla en construcción"
        mensaje="El registro y la edición de titulares se construyen en SCRUM-23 sobre el servicio de personas del backend."
      />
    </Panel>
  )
}