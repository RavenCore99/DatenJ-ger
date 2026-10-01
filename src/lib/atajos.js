/**
 * Atajos de teclado del sistema (SCRUM-85).
 *
 * Una sola tabla es la fuente de verdad: la usan el manejador global de
 * `App.jsx` y la sección «Atajos» de Ajustes, así que lo que se anuncia y lo que
 * funciona no pueden divergir. Los que ya existían (`Ctrl+B`, `Enter`, `Esc`)
 * se conservan tal cual.
 *
 * Las combinaciones siguen las de la aplicación anterior
 * (`paneles_datenjager.md` §4.7): `Ctrl+Q`, `Ctrl+F`, `Ctrl+N`, `Supr` y `F11`.
 */

export const ATAJOS = [
  {
    combinacion: 'Ctrl / ⌘ + F',
    accion: 'Buscar en todo el sistema',
    detalle: 'Abre la búsqueda global sobre documentos, titulares y empresas.',
  },
  {
    combinacion: 'Ctrl / ⌘ + N',
    accion: 'Agregar documento',
    detalle: 'Lleva a Documentos y abre el formulario de alta.',
  },
  {
    combinacion: 'Ctrl / ⌘ + B',
    accion: 'Plegar o desplegar la barra lateral',
    detalle: 'Recoge la barra a 64 px o la devuelve a 240 px.',
  },
  {
    combinacion: 'Supr',
    accion: 'Eliminar el documento seleccionado',
    detalle: 'Pide confirmación. Solo actúa en Documentos, con una fila elegida.',
  },
  {
    combinacion: 'F11',
    accion: 'Pantalla completa',
    detalle: 'Alterna la ventana entre pantalla completa y tamaño normal.',
  },
  {
    combinacion: 'Ctrl / ⌘ + Q',
    accion: 'Cerrar la sesión',
    detalle: 'Pide confirmación cuando hay una sesión abierta.',
  },
  {
    combinacion: 'Enter',
    accion: 'Enviar el mensaje en el asistente',
    detalle: 'En los formularios, confirma el envío.',
  },
  {
    combinacion: 'Mayús + Enter',
    accion: 'Salto de línea en el asistente',
    detalle: 'Escribe un salto sin enviar el mensaje.',
  },
  {
    combinacion: 'Escape',
    accion: 'Cerrar la capa abierta',
    detalle: 'Cierra modales, el visor y la búsqueda global.',
  },
]

/**
 * ¿El foco está en un campo donde se escribe? Los atajos de una sola tecla
 * (`Supr`) no deben dispararse mientras alguien escribe, o borrarían el
 * documento al borrar un carácter.
 */
export function escribiendoEn(evento) {
  const elemento = evento.target
  if (!elemento) return false
  const etiqueta = elemento.tagName
  return (
    etiqueta === 'INPUT' ||
    etiqueta === 'TEXTAREA' ||
    etiqueta === 'SELECT' ||
    elemento.isContentEditable === true
  )
}

/** ¿Hay alguna capa modal abierta? */
export function capaAbierta() {
  return Boolean(document.querySelector('[role="dialog"]'))
}