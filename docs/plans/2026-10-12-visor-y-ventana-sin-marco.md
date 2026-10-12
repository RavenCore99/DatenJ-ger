# Visor PDF y ventana sin marco — plan de implementación

> **Para Hermes:** ejecutar por secciones verificables, con prueba roja antes del código y commits separados por ticket Jira.

**Objetivo:** aprovechar el alto disponible del visor PDF y sustituir el marco nativo por una barra de ventana propia en claro y oscuro.

**Arquitectura:** el visor sigue descargando el documento mediante el backend y revocando la URL al desmontarse, pero renderiza su diálogo mediante un portal en `document.body`, fuera del contenedor animado de Documentos. Electron crea una ventana `frame: false`; un componente React persistente encima del portal/sistema expone controles de ventana mediante IPC limitado a la ventana emisora, con alternativa inocua en navegador web. La barra se alinea con los tokens existentes y reserva áreas `no-drag` para botones. No se agregan dependencias.

**Stack:** Electron, React 19, Tailwind 3, Node test runner, CDP de Electron, unittest Python.

---

### 1. Regresión del visor (SCRUM-59)
- Crear prueba de geometría sobre el renderer real con base y perfil temporales: abrir Documentos y un PDF de prueba; antes del cambio, el área `iframe` no alcanza el borde inferior de la ventana. Verificar que la prueba falla por altura insuficiente, no por problemas de datos.
- Modificar `src/components/VisorPdf.jsx`: portal al `document.body`; desplazar el visor bajo la barra global y conservar su contenido y cleanup.
- Repetir prueba de geometría: `iframe` ocupa el área vertical restante, la barra del visor y Guardar/Cerrar funcionan, Escape cierra y se revoca la URL. Comprobar claro y oscuro.
- Commit `fix(SCRUM-59): amplía el visor PDF a la altura de la ventana`.

### 2. Barra de ventana y controles (SCRUM-60, SCRUM-59)
- Prueba roja del contrato IPC: antes del cambio no hay estado ni acciones acotadas para minimizar, maximizar y cerrar. Prueba roja de la barra: ausente en bienvenida, acceso y sistema.
- `electron/main.js`: `frame: false` para Windows/Linux; on macOS elegir una solución que mantenga los controles nativos o los supla. Restringir acciones a `BrowserWindow.fromWebContents(event.sender)`, emitir estado maximizado/fullscreen al renderer; no exponer APIs Electron generales.
- `electron/preload.js` y `src/lib/escritorio.js`: API limitada de controles/estado con cleanup de listeners y fallback web.
- Crear `src/components/BarraVentana.jsx`, montarla en `src/App.jsx` fuera de `Marco` y conservar los contenidos debajo; zona drag, accesibilidad y no-drag, responsive cuando el ancho mínimo sea 1024px. Reusar tokens de `src/estilos/tokens.css` y `src/index.css` para temas.
- Pruebas en Electron: arrastre, minimizar/restaurar, maximizar/restaurar, cerrar, F11, claro/oscuro, bienvenida y visor. Probar sin afectar datos reales.
- Commit `feat(SCRUM-60): incorpora ventana sin marco y controles seguros`; si el estilo se puede aislar, commit `ui(SCRUM-59): adapta la barra a ambos temas`.

### 3. Verificación y PR
- `npm run build`, `./venv/bin/python -m unittest discover -s tests -t .`, tests de Node y sonda de la ventana real.
- Revisar `git diff --check`, `git status`, commits cortos con ticket existente.
- `git push origin v2.1` y `gh pr create --base main --head v2.1` con título `[SPRINT-5]`, tickets SCRUM-59/SCRUM-60 y plan de validación. Verificar el PR por lectura. Dejarlo abierto sin merge ni disparar manualmente GitHub Actions: validación humana primero.
