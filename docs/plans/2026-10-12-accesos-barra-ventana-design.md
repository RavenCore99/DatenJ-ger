# Accesos de la barra sin marco — diseño aprobado

**Objetivo:** sustituir la marca redundante de la barra de Electron por accesos de Ajustes, Asistente y Cerrar sesión, manteniendo espacio arrastrable y controles de ventana.

**Decisión:** la barra toma las acciones del mismo estado de navegación y sesión que el marco principal; los accesos solo aparecen cuando el sistema está autenticado (no en bienvenida, registro o acceso). Ajustes y Asistente navegan a sus secciones existentes; Cerrar sesión reutiliza la confirmación y petición del atajo Ctrl+Q. La tuerca duplicada se retira de la subcabecera, pero se conservan la navegación lateral y el asistente flotante. El visor PDF no cambia.

**Aspecto:** fondo, bordes, texto y hover usan tokens del tema; iconos SVG del proyecto, separados de los tres controles de ventana. La zona vacía conserva `drag`, y los botones quedan en `no-drag` con nombres accesibles y foco visible.

**Verificación:** prueba roja de estructura y cableado; build; suite; sonda CDP con perfil y base aislados para navegación, cierre cancelado/confirmado y ambos temas; push al PR #24, sin merge ni ejecución manual de Actions.
