/** Contenedor con desplazamiento propio para paneles extensos. */
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