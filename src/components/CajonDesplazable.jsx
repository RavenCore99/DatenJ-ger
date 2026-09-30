/**
 * Cajón desplazable (SCRUM-71).
 *
 * Portado del complemento `assets/assets/scroller_cajon`: un contenedor con
 * desplazamiento propio y barra fina, para el contenido largo que vive dentro
 * de un panel —hoy, el visor del log de auditoría—. Mantiene la barra del
 * sistema fuera y usa la del propio cajón.
 */
export default function CajonDesplazable({ children, className = '', alto = 'max-h-96', sinMarco = false }) {
  return (
    <div
      className={[
        'cajon-scroll overflow-auto',
        sinMarco ? '' : 'rounded-lg border border-borde bg-lienzo',
        alto,
        className,
      ].join(' ')}
    >
      {children}
    </div>
  )
}