import Panel, { EstadoVacio } from '../components/Panel.jsx'

/**
 * Panel de auditoría.
 *
 * Alcance pendiente (SCRUM-24): historial de acciones con filtros por fecha y
 * tipo, limpieza del historial y consulta del log del sistema.
 */
export default function Auditoria() {
  return (
    <Panel titulo="Auditoría" descripcion="Historial de acciones sobre el archivo">
      <EstadoVacio
        titulo="Pantalla en construcción"
        mensaje="El historial con filtros, la limpieza y el visor del log se construyen en SCRUM-24 sobre el servicio de auditoría del backend."
      />
    </Panel>
  )
}