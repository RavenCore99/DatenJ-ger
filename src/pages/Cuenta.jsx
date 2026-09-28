import Panel, { EstadoVacio } from '../components/Panel.jsx'
import { useApp } from '../estado/ProveedorApp.jsx'

/**
 * Panel de cuenta.
 *
 * Alcance pendiente (SCRUM-25): contraseña, 2FA, códigos de respaldo,
 * confianza de dispositivo y apariencia. Solo las secciones que tienen lógica
 * real en `main.py` — el resto de la referencia visual no es alcance
 * (CLAUDE.md sección 6). Los cambios de contraseña, 2FA y confianza de
 * dispositivo tocan el flujo de autenticación: se muestran antes de aplicarse.
 */
export default function Cuenta() {
  const { tema, alternarTema } = useApp()

  return (
    <div className="flex flex-col gap-6">
      <Panel titulo="Apariencia" descripcion="Tema de la interfaz">
        <div className="flex items-center justify-between gap-4">
          <p className="text-xs text-tenue">
            Tema activo: <span className="font-mono">{tema}</span>
          </p>
          <button
            type="button"
            onClick={alternarTema}
            className="rounded-lg border border-borde px-3 py-1.5 text-xs font-medium transition-colors hover:border-primario hover:text-primario"
          >
            Alternar tema
          </button>
        </div>
      </Panel>

      <Panel titulo="Seguridad" descripcion="Contraseña, doble factor y dispositivos">
        <EstadoVacio
          titulo="Pantalla en construcción"
          mensaje="La gestión de contraseña, la configuración de 2FA, los códigos de respaldo y la confianza de dispositivo se construyen en SCRUM-25 sobre el flujo de autenticación de main.py."
        />
      </Panel>
    </div>
  )
}