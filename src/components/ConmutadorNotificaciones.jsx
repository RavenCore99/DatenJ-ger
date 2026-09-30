/**
 * Conmutador de notificaciones (SCRUM-71).
 *
 * Portado del complemento `assets/assets/Notifications_toggle`, pero como
 * control accesible del sistema (`role="switch"`) y con los colores de los
 * tokens en lugar del amarillo fijo del original. Sirve para cualquier opción
 * booleana de la aplicación —hoy, las animaciones de la sección de cuenta—.
 */
export default function ConmutadorNotificaciones({ activo, onCambiar, etiqueta, descripcion }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div className="min-w-0">
        <p className="text-cuerpo-md">{etiqueta}</p>
        {descripcion && <p className="text-cuerpo-sm text-tenue">{descripcion}</p>}
      </div>

      <button
        type="button"
        role="switch"
        aria-checked={activo}
        aria-label={etiqueta}
        onClick={() => onCambiar(!activo)}
        className={[
          'relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition-colors',
          activo ? 'border-primario bg-primario' : 'border-borde bg-fondo-2',
        ].join(' ')}
      >
        <span
          aria-hidden="true"
          className={[
            'conmutador-perilla inline-block h-4 w-4 rounded-full bg-superficie shadow',
            activo ? 'translate-x-6' : 'translate-x-1',
          ].join(' ')}
        />
      </button>
    </div>
  )
}