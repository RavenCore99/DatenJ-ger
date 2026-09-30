/**
 * Formulario suave (SCRUM-71).
 *
 * Portado del complemento `assets/assets/smooth_formulario`: un formulario que
 * entra con un fundido corto y campos con el subrayado que se dibuja al
 * enfocar. No impone pasos ni validación —eso es del flujo que lo use—; solo
 * aporta la transición y el tratamiento del campo.
 */

/** Envoltorio del formulario: fundido de entrada, sin bloquear la interacción. */
export function FormularioSuave({ children, className = '', ...resto }) {
  return (
    <form className={`paso-suave flex flex-col gap-4 ${className}`} {...resto}>
      {children}
    </form>
  )
}

/** Campo de texto con el subrayado animado del complemento. */
export function CampoSuave({ etiqueta, valor, onCambio, tipo = 'text', ayuda, ...resto }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-etiqueta-sm text-texto">{etiqueta}</span>

      <span className="campo-suave relative block">
        <input
          type={tipo}
          value={valor}
          onChange={(evento) => onCambio(evento.target.value)}
          className="w-full rounded-lg border border-borde bg-fondo px-3 py-2 text-cuerpo-md outline-none transition-colors focus:border-primario"
          {...resto}
        />
      </span>

      {ayuda && <span className="text-cuerpo-sm text-tenue">{ayuda}</span>}
    </label>
  )
}

export default FormularioSuave