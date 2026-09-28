import Panel, { EstadoVacio } from '../components/Panel.jsx'

/**
 * Panel de documentos.
 *
 * Alcance pendiente (SCRUM-22): rejilla del inventario, búsqueda, alta con
 * selección de archivo, visor y exportación. El contenido funcional llega en
 * ese ticket; aquí queda el andamiaje de la pantalla.
 */
export default function Documentos() {
  return (
    <Panel
      titulo="Documentos"
      descripcion="PDFs cifrados del archivo documental"
    >
      <EstadoVacio
        titulo="Pantalla en construcción"
        mensaje="La rejilla del inventario, la búsqueda y el alta de documentos se construyen en SCRUM-22 sobre el servicio de documentos del backend."
      />
    </Panel>
  )
}