# planning.md — DatenJäger

> Hoja de ruta técnica derivada de la sección "Hoja de ruta sobre
> incorporaciones del sistema" del anteproyecto Ciclo III. Traduce las
> instancias priorizadas por impacto/esfuerzo en fases ejecutables por
> secciones de código. Cada fase se marca activa manualmente por Raven; el
> agente no salta de fase por su cuenta.

## Visión del proyecto (v3 — estructura simplificada)

Hoy, **CustomTkinter es el frontend** del sistema: cada panel (login, 2FA,
dashboard, PDFs, personas, auditoría, chatbot) está implementado como
lógica de negocio y renderizado de UI mezclados en los mismos módulos
Python (`main.py`, `pdf_manager.py`, `personas.py`, `audit.py`,
`chatbot_ui.py`, etc.).

La meta es **separar esas dos cosas**: Python se queda como backend puro
(lógica, cifrado, base de datos, chatbot, agentes) y el frontend se
reconstruye visualmente en **Electron + React + Tailwind CSS**, guiado por
los mockups ya existentes en `/assets/mockups`. No es "agregar" un frontend
nuevo encima del actual — es trasladar lo visual de cada panel al nuevo
stack y dejar en Python solo lo que un backend necesita exponer.

Orden de trabajo, de más a menos prioritario:

1. **Pulir el backend Python** — extraer la lógica de cada panel de su
   implementación actual en CustomTkinter, para que quede como una capa de
   servicios que cualquier frontend pueda consumir.
2. **Migrar a los nuevos frameworks** — levantar el proyecto
   Electron + React + Tailwind y conectarlo al backend Python ya
   desacoplado (el "plomeo": bridge, rutas, estructura de pantallas).
3. **Construir el frontend conforme a los mockups** de
   `/assets/mockups` — aplicar el diseño visual real a cada pantalla ya
   conectada en el paso anterior.
4. **Integración de APIs y modelos locales** — panel de selección de
   modelos, streaming del chatbot, fallback local (Ollama), decisión de
   motor de persistencia. Se deja para el final porque depende de tener ya
   un frontend real donde mostrar ese panel, y no bloquea nada de lo
   anterior.

## Cómo usar este archivo

- Una fase se declara **activa** solo cuando Raven lo confirma.
- Dentro de una fase activa, el trabajo avanza por **secciones**: cada
  sección es un cambio acotado, verificable y terminado en un commit propio
  (redactado por el agente, ejecutado por Raven).
- Al cerrar una fase completa: actualizar el estado aquí (`por hacer` →
  `en progreso` → `hecho`) y reflejar el cambio en `CLAUDE.md` (sección 12).
- No se avanza a la siguiente fase con la anterior en `en progreso`, salvo
  excepción explícita de Raven.

Leyenda de estado: `por hacer` · `en progreso` · `hecho` · `evaluación`
(cuando el alcance depende de resultados de pruebas, no es un compromiso
cerrado).

---

## Fase 0 — Preparación (transversal, antes de tocar código)

Estado: **hecho en lo técnico**, y los **mockups ya están en el repositorio**:

* el mecanismo Python↔Electron quedó definido y construido (FastAPI + uvicorn
  sobre `127.0.0.1`, token por proceso; ver `backend/README.md` y
  `backend/server.py`);
* los mockups que faltaban llegaron: **11 pantallas** en `assets/tema claro/` y
  `assets/tema oscuro/`, que cubren justo lo que estaba pendiente —menú de
  inicio con registro de operadores y setup 2FA, flujo de autenticación y
  verificación 2FA TOTP, suite documental con el chatbot en la barra lateral,
  panel de auditoría (trazabilidad Ley 1581), panel de configuración estilo
  Hermes Desktop, asistente conversacional—, más el logo en
  `assets/logo/logo.png` y `assets/logo/logo.ico`, **44 iconos** en
  `assets/icons/` y cinco complementos de interfaz en `assets/assets/`.

Con esto la Fase 3 deja de estar bloqueada. **Los assets ya están versionados**
(`ee40d51` incorporó `assets/mockups/` con las 15 pantallas, su `code.html`, los
dos `DESIGN.md` y el inventario; `19a6cde` retiró las 24 copias antiguas tras
comprobar una por una que eran byte a byte idénticas).

- [x] Revisar el contenido de `/assets/mockups` disponible hasta ahora
      (5 pantallas: Configuración/Appearance, Auditoría Ley 1581 en modo
      claro, Expedientes + Hermes IA en modo claro, Auditoría Ley 1581 en
      modo oscuro, Expedientes + Hermes IA en modo oscuro) y el logo del
      proyecto. Ver resumen, paleta extraída y alcance en la Fase 3.
      **Confirmado con Raven**: estos mockups son **inspiración de
      estilo** (muy influenciados por "Hermes Desktop"), no una
      especificación 1:1 a replicar.
- [x] Mockups recibidos y revisados (2026-09-30): **15 pantallas** con su
      `code.html` real, en `assets/mockups/tema claro/` y `tema oscuro/`.
      Cubren login, bienvenida/intro, menú de inicio con registro y setup 2FA,
      registro con QR, suite principal, suite con el chatbot en la barra
      lateral, auditoría, ajustes y asistente conversacional. **Sigue sin
      haber referencia visual** para el dashboard de gráficos, el visor de PDF,
      los modales de documento, personas, reportes y el restablecimiento de
      contraseña: se construyen con el sistema de diseño (decisión de Raven del
      2026-09-30).
- [x] `.claudeignore` creado (2026-09-30): excluye entornos virtuales,
      dependencias, builds, binarios, la base de datos, el almacén de tokens y
      los secretos. Los mockups y el material de diseño **sí** quedan legibles
      (solo se excluyen las imágenes).
- [x] rama de trabajo en v2.1. consolidar ver el archivo.`jira.md` para realizar los commits en base a etiquetas acordes.
- [x] **Definir el mecanismo de comunicación Python↔Electron** (IPC nativo,
      API local tipo FastAPI + fetch desde React, `pywebview`, subprocess,
      etc.). Esta decisión condiciona cómo se diseña la capa de servicios
      en la Fase 1 y se implementa en la Fase 2.
      **Decidido y aprobado por Raven (2026-09-28)**: servidor local
      **FastAPI + uvicorn** sobre `localhost`, consumido por `fetch` desde
      React (opción A de la skill `electron-react-migration`). La fachada
      `backend/commands.py` ya concentra las operaciones que expondrá.

---

## Fase 1 — Pulir el backend Python (separar lógica de UI)

Estado: **hecho** (cerrada 2026-09-28, Sprint 2 — `SCRUM-12` a `SCRUM-19`)
— Skill: `python-refactor-audit`. La skill `app-state-router` **no está
instalada** en el perfil; la capa de estado se construyó siguiendo el
patrón de `python-refactor-audit` (sección 2.C).

Objetivo: que cada módulo quede con la lógica de negocio aislada de las
llamadas a `customtkinter`/`tkinter`, expuesta de forma que el futuro
frontend (Electron/React) pueda invocarla vía el mecanismo definido en
Fase 0. El frontend actual en CustomTkinter se mantiene funcionando en
paralelo mientras se hace esta extracción — no se rompe nada durante el
proceso. FastAPI sera para integrar al backend para conexion a frameworks de frontend.

Secciones sugeridas (cada una = un commit, por módulo):

1. **`pdf_manager.py`**: separar las operaciones CRUD de PDF (agregar,
   ver, buscar, abrir, eliminar, editar, exportar) de la construcción de
   ventanas/widgets. La lógica queda como funciones/métodos invocables sin
   necesidad de una ventana Tkinter abierta.
2. **`personas.py`**: mismo tratamiento para el CRUD de personas.
3. **`audit.py`**: separar el registro y consulta de auditoría de la
   ventana del visor.
4. **`chatbot.py` / `chatbot_ui.py`**: `chatbot.py` ya está relativamente
   limpio (es el servicio); verificar que `chatbot_ui.py` no contenga
   lógica que debería vivir en el servicio.
5. **Capa de estado de aplicación**: sesión, usuario autenticado, tema,
   configuración, temporización de inactividad — hoy viven como atributos
   implícitos de `main.py` (`self.usuario_actual`, `self._session_key`,
   etc.). Se extraen a un objeto/módulo de estado consultable
   explícitamente, no acoplado a Tkinter.
6. **Capa de "rutas" o comandos**: un punto de entrada único (funciones o
   clase de servicio) que agrupe las operaciones de cada panel — login,
   2FA, PDFs, personas, auditoría, reportes, chatbot — como las que
   consumirá el bridge de la Fase 2.

Explícitamente **fuera de alcance** en esta fase: tocar la apariencia visual
(colores, animaciones, layout) de las pantallas actuales de CustomTkinter.
No tiene sentido pulir una UI que se va a reemplazar completo en la Fase 3.

Criterio de cierre: cada panel tiene su lógica accesible sin pasar por un
widget de Tkinter (se puede probar con un script o test que la invoque
directamente); la capa de estado y la capa de comandos existen y están en
uso por `main.py`.

**Cierre verificado (Sprint 2)**:

| Sección | Entrega | Commit |
| --- | --- | --- |
| `pdf_manager.py` | `backend/services/documentos.py` | `refactor(SCRUM-12)` |
| `personas.py` | `backend/services/personas.py` | `refactor(SCRUM-13)` |
| `audit.py` | `backend/services/auditoria.py` | `refactor(SCRUM-14)` |
| `chatbot.py` / `chatbot_ui.py` | servicio consolidado (contenido y fábrica) | `refactor(SCRUM-15)` |
| Capa de estado | `backend/state.py` (`AppState`, `SesionUsuario`) | `refactor(SCRUM-16)` |
| Capa de comandos | `backend/commands.py` (`ComandosDatenJager`) | `refactor(SCRUM-17)` |
| Pruebas sin Tkinter | `tests/` (46 pruebas, base temporal real) | `test(SCRUM-18)` |
| Documentación | `backend/README.md` | `docs(SCRUM-19)` |

Pendiente declarado: login, 2FA, cambio de contraseña y token de
confianza siguen en `main.py` — el flujo de autenticación requiere
aprobación explícita para moverse. Catálogo en
`ComandosDatenJager.operaciones_pendientes()`. La skill `security-review`
**no está instalada** en el perfil.

---

## Fase 2 — Migración a los nuevos frameworks (andamiaje técnico)

Estado: **hecho** (cerrada 2026-09-28, Sprint 2 — `SCRUM-20` a `SCRUM-25`;
`SCRUM-26`, el instalador, queda en pausa por decisión expresa de Raven y así
figura en `jira.md`) — Skill: `electron-react-migration`

Objetivo: levantar el proyecto Electron + React + Tailwind y conectarlo al
backend ya desacoplado en la Fase 1, usando el mecanismo de comunicación
definido en Fase 0. En esta fase el foco es que **funcione**, no que se vea
igual a los mockups todavía (eso es la Fase 3) — pantallas mínimas que
prueben el flujo real contra el backend Python.

Secciones sugeridas:

1. **Andamiaje del proyecto**: scaffolding de Electron + React + Tailwind,
   estructura de carpetas, configuración de build.
2. **Implementación del puente Python↔Electron** según lo definido en
   Fase 0, conectado a la capa de comandos de la Fase 1.
3. **Migración pantalla por pantalla (funcional, sin diseño final)**, en
   este orden sugerido: login/2FA → panel documental (CRUD + etiquetas) →
   personas → auditoría → configuración/cuenta.
4. **Empaquetado inicial**: verificar que el instalador de escritorio
   pueda generarse desde este punto, aunque el diseño visual no esté
   terminado.

Criterio de cierre: el flujo login → panel documental → CRUD de PDFs
funciona end-to-end sobre Electron/React consumiendo el backend Python
real (no un mock), aunque visualmente sea provisional.

**Cómo quedó cerrada.** El andamiaje (Vite + React + Tailwind con Electron),
el puente HTTP (`backend/server.py` sobre FastAPI, con token por proceso) y
los cinco paneles funcionales: acceso con 2FA, documentos, personas,
auditoría y cuenta. Verificado con sondas que conducen el renderer real
sobre bases temporales (`DATENJAGER_DB`) y almacenes temporales
(`DATENJAGER_TOKENS`), nunca sobre los datos del usuario. La Fase 3 toma
estas pantallas y las lleva al diseño de los mockups; el empaquetado
(`SCRUM-26`) se retoma entonces.

---

## Verificación de las fases 0 a 2 (2026-09-30)

Comprobado antes de abrir la Fase 3, para que lo anterior quede al día:

| Fase | Comprobación | Resultado |
| --- | --- | --- |
| 0 | Mecanismo Python↔Electron definido y construido | `backend/server.py` (FastAPI + uvicorn, token por proceso) — verificado punta a punta |
| 0 | Material de diseño disponible y versionado | 15 mockups + `code.html` + 2 `DESIGN.md` + inventario, en git |
| 0 | `.claudeignore` vigente | creado |
| 1 | Pruebas del backend sin Tkinter | `./venv/bin/python -m unittest discover -s tests -t .` → **121 pruebas, OK** (hoy 142; ver el cierre de la Fase 3) |
| 1 | La capa backend no arrastra interfaz | importar `backend.*` sin `DISPLAY` → *modulos de interfaz cargados: ninguno* |
| 2 | El frontend compila | `npx vite build` → correcto |
| 2 | Paneles funcionales | `Acceso`, `Documentos`, `Personas`, `Auditoria`, `Cuenta`, `Inicio` |
| 2 | Puente en marcha | arranque ~1 s, `401` sin token, sesión heredada `200` |

---

## Fase 3 — Construcción del frontend conforme a los mockups

> **Alcance ampliado (2026-09-28).** Además de llevar a diseño las cinco
> pantallas ya funcionales, la Fase 3 cubre las pantallas que todavía no
> existen, la identidad visual y el movimiento. En `jira.md` estos trabajos
> viven en el **Sprint 5**: pantallas nuevas en `SCRUM-57` a `SCRUM-64`,
> identidad visual y movimiento en `SCRUM-65` a `SCRUM-71`. Los `SCRUM-27` a
> `SCRUM-32` del Sprint 3 siguen siendo el acabado visual de lo que ya
> funciona.

Estado: **en progreso** — Skill: `electron-react-migration` +
`ui-states-animations`. La sección **Base visual y movimiento** (`SCRUM-27` a
`SCRUM-32` y `SCRUM-65` a `SCRUM-71`) está cerrada y verificada, y las
**pantallas que faltaban** (`SCRUM-57` a `SCRUM-64`) también, con `SCRUM-89`
como corrección del hallazgo de conexión a base de datos. Queda abierto el
resto del Bloque D (`SCRUM-80` a `SCRUM-88`) y el empaquetado.

Objetivo: tomar cada pantalla ya funcional de la Fase 2 y llevarla a una
identidad visual **inspirada** en `/assets/mockups`, con Tailwind.

### Alcance: inspiración de estilo, no especificación literal

Los mockups en `/assets/mockups` están fuertemente inspirados en el
patrón visual "Hermes Desktop" (barra superior con breadcrumb, sidebar
con atajos de teclado, panel lateral de IA, visor de log tipo terminal,
barra de estado inferior con hash de git) y en la paleta del logo del
proyecto. **No son el resultado final a replicar pixel a pixel** —
sirven como referencia de tono, paleta y composición.

Dos reglas de alcance confirmadas por Raven:

- **Los paneles, funcionalidades y secciones a construir son los que ya
  existen en el código Python actual** (Expedientes/PDFs, Titulares/
  Personas, Auditoría, Hermes IA/Chatbot, Configuración con las
  secciones reales: contraseña, 2FA, códigos de respaldo, confianza de
  dispositivo, apariencia). La pantalla de Configuración del mockup
  incluye ~18 secciones estilo IDE (Model, Workspace, Safety, Browser,
  Passwords & Logins, Voice, Billing, Providers, Gateways, Archived
  Chats, etc.); esas son **decoración de referencia de estilo**, no
  alcance funcional — no se construyen secciones sin lógica real
  detrás de ellas, salvo que Raven pida explícitamente ampliar el
  alcance de Configuración más adelante.
- La búsqueda semántica (`Hermes IA Semantic` en el sidebar del mockup)
  **sigue como Fase 6, en evaluación** — que ya tenga un ítem diseñado
  en el mockup no la promueve a compromiso cerrado.

### Decisiones cerradas (2026-09-30, revisión del material de diseño)

Raven revisó `/assets/mockups` completo y respondió:

1. **Los mockups son referencias, no especificaciones.** El diseño y la
   estructura del dashboard, los paneles y los subpaneles están **inspirados en
   Hermes Desktop**; lo que manda es el sistema de diseño (`DESIGN.md`) más el
   patrón de Hermes Desktop. No se replican pixel a pixel.
2. **Gráficos, reportes y estadística: la lógica en Python, el diseño en el
   frontend.** Los gráficos y reportes se generan con Python (numpy,
   matplotlib, PyMuPDF) y el frontend los viste con la paleta del sistema. Los
   métodos de datos y estadística siguen el mismo enfoque que ya usa el código
   actual (regresión lineal con `numpy`).
3. **Nada de modelos locales todavía.** Hasta que el frontend y el backend no
   estén completos al 100 %, el chatbot funciona **solo por API**; el respaldo
   local vía Ollama se retoma después. El objetivo ahora es tener todos los
   paneles y secciones listos.
4. **Ajustes:** las cuatro secciones reales (contraseña, códigos 2FA,
   confianza, apariencia) **más las que tengan sentido** para este proyecto.
5. **Iconos:** lo que mejor se adapte, priorizando rendimiento y estética.

**Reconciliación del sistema de diseño (`SCRUM-27`).** El export oficial del
spec reveló que los dos `DESIGN.md` **no son un modo claro y otro oscuro del
mismo sistema**, sino dos sistemas que divergen: el claro usa **Inter**, escalas
más densas (cuerpo 13px) y margen de `1rem`; el oscuro usa **Manrope**, escalas
mayores (cuerpo 14px, título 28px en vez de 32px) y margen de `1.25rem`. El
oscuro además añade diez roles propios (semáforo de ventana, superficies
translúcidas, lienzos, `status-verified`). Se adoptó:

* **tipografía y escalas del claro** — Manrope no aparece en ningún mockup, y
  una fuente que cambia al cambiar de tema es inviable;
* **colores de cada modo**, conservando los nombres de rol del spec y expuestos
  como una capa semántica (`fondo`, `superficie`, `borde`, `texto`, `tenue`,
  `primario`, `acento`, `exito`, `alerta`, `peligro`, ...);
* **los roles que solo define el oscuro** disponibles en ambos modos (semáforo,
  cristal, lienzo), y `alerta` conservada del proyecto porque el spec no define
  un rol de advertencia;
* los nombres antiguos (`tenue`, `panel`) se mantienen para que las pantallas ya
  construidas sigan funcionando sin cambios.

**Tipografías autoalojadas:** Space Grotesk (marca), Inter (cuerpo) y JetBrains
Mono (telemetría) en `assets/fuentes/`, **tres archivos y 99,6 KB**. Se
descubrió por hash que los nueve archivos que sirve Google eran tres contenidos
distintos (fuentes variables): quedaron los tres y cada peso apunta al archivo
de su familia, con el `unicode-range` de `latin`.

**Deuda detectada en esta revisión:** la estadística y los gráficos viven hoy
dentro de `ui_components.py` (`DashboardWidget`, líneas ~673-950): la regresión
lineal, la predicción y **los colores de los gráficos están incrustados en la
capa de UI**. Para que el frontend nuevo dibuje los gráficos con la paleta del
sistema, esa lógica debe subir al backend (nueva sección de este plan).

### Paleta: el `DESIGN.md` es la fuente, no la estimación

La paleta que figuraba aquí (`#F5F7FB`/`#0D0F1A`, primario `#2F6FED`) era una
**estimación** hecha antes de recibir el material. El `DESIGN.md` que acompaña a
los mockups ("DatenJäger Precision Desktop") la reemplaza:

| Rol | Claro | Oscuro |
| --- | --- | --- |
| Fondo / superficie | `#f8f9ff` | `#0b1326` |
| Superficie de contenedor | `#e5eeff` | `#171f33` |
| Texto principal | `#0b1c30` | `#dae2fd` |
| Texto secundario | `#434655` | `#c3c6d7` |
| Primario (acción) | `#1d4ed8` | `#2563eb` |
| Primario (énfasis) | `#0037b0` | `#b4c5ff` |
| Secundario | `#0284c7` | `#4edea3` |
| Borde | `#e2e8f0` | `#434655` |
| Error | `#ba1a1a` | `#ffb4ab` |
| Éxito | `#10b981` | `#10b981` |

Tipografía: **Space Grotesk** (títulos y marca), **Inter** (cuerpo y controles),
**JetBrains Mono** (telemetría, hashes, atajos). Radios: `4/6/8/12/16px` y
`full`. Densidad: barra lateral `240px` (colapsable a `64px`), sub-cabecera
`48px`, franja de telemetría inferior `32px`.

Los tokens `--dj-*` de `src/index.css` se construyeron con la estimación: hay
que reemplazarlos por estos valores.

### Paleta extraída del logo y los mockups

El logo (círculo navy oscuro, anillo azul, ave blanca) es la fuente de
la paleta; los mockups la aplican en modo claro y modo oscuro de forma
consistente. Valores aproximados, a verificar con color-picker sobre los
mockups reales antes de fijarlos en `tailwind.config`:

| Token | Claro | Oscuro |
| --- | --- | --- |
| Fondo base | `#F5F7FB` | `#0D0F1A` (tono del círculo del logo) |
| Superficie / card | `#FFFFFF`, borde `#E2E8F0` | `#161A2C`, borde `#262B40` |
| Acento primario | `#2F6FED` (azul del anillo del logo) | mismo azul, algo más brillante |
| Texto primario | `#151B3D` | `#E6E8F0` |
| Texto secundario | `#64748B` | `#8B93AE` |
| Éxito | `#16A34A` / `#22C55E` | igual, más saturado |
| Advertencia | `#D97706` / `#F59E0B` | igual |
| Peligro | `#DC2626` / `#EF4444` | igual |
| Info / semántico (RAG, IA) | `#0D9488` (teal) | igual |

Tipografía: sans-serif para UI general; **monoespaciada** para hashes,
timestamps y el visor de log (`app.log`) — es un detalle de identidad
consistente en los 5 mockups revisados.

Componentes recurrentes a construir como piezas reutilizables (no una
por pantalla): barra superior con breadcrumb + badge de cifrado + CTA
primario; sidebar con atajos `⌘1`–`⌘5` e indicador de sección activa;
fila de tarjetas KPI; pills de estado coloreadas por tipo de acción;
tabla con columna de hash monoespaciada; panel lateral de IA con
tarjetas de hallazgo (éxito/alerta) y citas normativas; visor flotante
de log tipo terminal; barra de estado inferior (gateway, modelo local,
nodo del cluster, versión + hash de git corto).

Secciones sugeridas:

1. **Tokens de diseño en Tailwind**: paleta (tabla anterior), tipografía
   y espaciados, configurados en `tailwind.config`. Confirmar valores
   exactos de color contra los mockups (o pedirle a Raven el archivo de
   diseño fuente) antes de darlos por definitivos.
2. **Migración visual pantalla por pantalla**, siguiendo el mismo orden de
   la Fase 2 (login/2FA → panel documental → personas → auditoría →
   configuración), reemplazando el markup provisional por el diseño
   inspirado en el mockup correspondiente y limitado a las secciones que
   existen en el código Python actual.
3. **Pantallas que todavía no existen** (hoy no tienen equivalente en el
   frontend nuevo y sí lógica en el código Python):

   | Pantalla | Origen en el sistema actual |
   | --- | --- |
   | Registro de operadores (alta de usuario) | flujo de registro de `main.py`, ya portado al backend en `SCRUM-57` (`POST /api/registro`) |
   | Setup 2FA con QR y códigos de respaldo | `main.py` (`mostrar_setup_2fa`, `_mostrar_codigos_respaldo`); el backend ya lo expone, falta la pantalla dedicada al alta |
   | Panel del chatbot con barra lateral por botones | `chatbot_ui.py` (hoy bloqueante; el streaming llega en la Fase 4) |
   | Visor de PDF dentro de la aplicación | hoy no existe: los documentos se descifran y se abren por fuera |
   | Reportes con paleta estructurada por tipo | `reporter.py` |
   | Recopilador de datos y estadísticas | métricas de `ui_components.py` y `backend/services/reportes.py` |
   | Panel de ajustes completo | paridad con las secciones reales del código Python (`main.py`), más el panel de conexión de APIs y modelos |
   | Panel de conexión de modelos y APIs | Fase 4; aquí se construye la pantalla |

4. **Identidad visual y movimiento**, extraída de `assets/` y de la paleta del
   logo:

   * logo e icono de la aplicación desde `assets/logo/` (ventana, barra de
     tareas, pantalla de acceso);
   * los 44 iconos de `assets/icons/` como set de acción del sistema;
   * transición **suave** al cambiar de tema claro a oscuro y viceversa (hoy
     el cambio es instantáneo);
   * animación de entrada al abrir la aplicación, de tono minimalista, en la
     línea de Hermes Desktop;
   * micro-interacciones y transiciones entre paneles;
   * los complementos de `assets/assets/` incorporados como componentes
     propios, con la estética del proyecto (no tal cual vienen): botón
     biométrico, sistema de partículas, conmutador de notificaciones, cajón
     desplazable y formulario suave.

5. **Dashboard, estadística y reportes** (con el criterio de la decisión 2):

   * la **lógica** de datos y estadística en Python: métricas, distribución por
     empresa, serie temporal, **regresión lineal con predicción y R²**
     (`numpy`), y los gráficos que hagan falta (`matplotlib`);
   * el **diseño** en el frontend: gauges, donut, barras y línea de tendencia
     dibujados con la paleta del sistema, no con los colores incrustados hoy en
     `ui_components.py`;
   * el **reporte PDF** conserva estructura de portada, inventario y gráfico por
     empresa, con los colores y la organización del sistema (`PyMuPDF`);
   * se valora incorporar métodos de aprendizaje automático para datos y
     estadística, con el mismo enfoque que ya usa el código actual.

6. **Visor de PDF dentro de la aplicación**: hoy no existe; los documentos se
   descifran y se abren por fuera.

7. **Estados que informan de verdad**: indicadores con color para la conexión
   con la base de datos, el estado de las conexiones de API y el estado del
   chatbot; *skeletons* de carga en las listas; iconos de acción para
   desplegar y recoger las barras laterales.

8. **Estados canónicos y transiciones**: vacío, error, carga
   (*skeleton*), y animaciones (fade, hover, easing) — implementados
   directamente en React/Tailwind, con opción de deshabilitarlas desde
   configuración de usuario.

Criterio de cierre: cada pantalla migrada refleja la paleta e identidad
visual de los mockups (sin exigir coincidencia pixel a pixel) y cubre
únicamente las secciones/funcionalidades presentes en el código Python
actual; estados canónicos y transiciones activos en al menos las
pantallas principales (login, dashboard, PDFs).

---

### Avance de la Fase 3 (marcar al cerrar cada sección)

Base visual y movimiento:

- [x] `SCRUM-27` tokens visuales del `DESIGN.md` en Tailwind (paleta, tipografía, radios, densidades)
- [x] `SCRUM-28` layout base: barra lateral `240px`/`64px`, sub-cabecera `48px`, franja inferior `32px`, marco de ventana
- [x] `SCRUM-29` login, bienvenida/intro, verificación 2FA y panel documental
- [x] `SCRUM-30` personas y auditoría
- [x] `SCRUM-31` configuración y cuenta
- [x] `SCRUM-32` estados canónicos y transiciones
- [x] `SCRUM-65` logo, icono de aplicación y set de iconos
- [x] `SCRUM-66` transición suave entre tema claro y oscuro
- [x] `SCRUM-67` animación de entrada y micro-interacciones
- [x] `SCRUM-68` estados con color (base de datos, APIs, chatbot)
- [x] `SCRUM-69` skeleton como animacion de carga
- [x] `SCRUM-70` barras laterales desplegables
- [x] `SCRUM-71` complementos de `assets/assets/` como componentes propios

Pantallas que faltan (cerradas 2026-09-30):

- [x] `SCRUM-57` registro de operadores (el único pendiente del backend)
- [x] `SCRUM-58` alta de 2FA con QR y códigos de respaldo
- [x] `SCRUM-59` panel del chatbot con barra lateral por botones
- [x] `SCRUM-60` visor de PDF dentro de la aplicación
- [x] `SCRUM-61` panel de reportes
- [x] `SCRUM-62` recopilador de datos y estadísticas
- [x] `SCRUM-63` panel de ajustes completo
- [x] `SCRUM-64` panel de conexión de APIs y modelos

> **Corrección de alcance registrada (2026-09-30, `SCRUM-89`).** El hallazgo de
> `docs/issues.md` —«conexión a base de datos fallida; electron y web caen; no
> se puede acceder al dashboard mediante login ni register»— eran **tres**
> problemas superpuestos, y el tercero era la causa directa del síntoma:
>
> 1. **El alta de usuario no existía en el frontend** (era `SCRUM-57`): el
>    backend validaba credenciales y gestionaba el 2FA, pero crear una cuenta
>    seguía siendo exclusivo de `main.py`, así que una instalación nueva no tenía
>    forma de entrar.
> 2. **Una base caída se veía como un servicio sano:** `GET /api/salud` no
>    comprobaba la base y el arranque moría con una traza de Python que el
>    lanzador resumía en «servicio no disponible», sin decir por qué.
> 3. **`src/App.jsx` usaba `<Icono>` en la sub-cabecera sin importarlo.** Al
>    montar el shell autenticado saltaba `ReferenceError: Icono is not defined`
>    y React desmontaba el árbol entero: la ventana quedaba **en blanco justo
>    después de entrar**. Era un defecto **previo** (ya estaba en `42eeaa8`) y
>    pasó inadvertido porque `vite build` compila igual — un identificador sin
>    definir no es un error de compilación. Es exactamente «puedo loguearme pero
>    no llego al dashboard».
>
> Los tres están cerrados. La verificación del cierre **no** fue `vite build`,
> sino conducir la ventana real de Electron (`SCRUM-89`), que es lo que destapó
> el punto 3.
>
> Al mismo cierre se sumaron **dos correcciones más**, encontradas al arrancar la
> aplicación como la usa Raven:
>
> 4. **Un puerto 8756 ocupado dejaba la app sin servicio.** Bastaba una instancia
>    anterior que no se cerró bien: el servicio no podía enlazar, la interfaz
>    decía «sin conexión» y el motivo no se pintaba en ninguna pantalla. Ahora
>    `electron/backend.js` prueba 8756, 8757, 8758, 8759 y por último el puerto
>    que elija el sistema, y Bienvenida y Acceso muestran el error real del
>    proceso principal (`cb1dc31`).
> 5. **`npm run dev` no conectaba.** En modo desarrollo el renderer se sirve desde
>    el servidor de Vite (`:5273`), así que su origen deja de ser `file://` y el
>    navegador bloqueaba las llamadas al servicio por CORS —`Access to fetch … has
>    been blocked by CORS policy`— pese a que el servicio estaba levantado. El
>    servicio habilita CORS solo para esos orígenes y solo en desarrollo
>    (`DATENJAGER_CORS_ORIGENES`; en producción no se habilita) (`27c7aa5`).
>
> Con esto **la ruta de desarrollo deja de estar sin verificar**: era «no
> verificada» en la Fase 2 y ahora está comprobada conduciendo el propio
> `npm run dev`.

Diseño, datos y cierre:

- [x] `SCRUM-79` versionar el material de diseño y de marca (`ee40d51`, `19a6cde`)
- [x] `SCRUM-80` set de iconos del frontend — resuelto con el set SVG en línea de
  `Icono.jsx`, que cubre todos los nombres que el sistema pide
- [x] `SCRUM-81` extraer la estadística y los gráficos al backend — `reportes.tendencia()`
  (regresión, predicción y R²) y `reportes.PALETA_GRAFICOS` (colores por rol semántico);
  `GET /api/reportes/tendencia`. `DashboardWidget` ya no calcula: solo dibuja
- [x] `SCRUM-82` dashboard de gráficos — `src/components/Graficos.jsx` (medidor, anillo y
  línea de tendencia en SVG, sin dependencias) sobre los datos del backend
- [x] `SCRUM-83` reportes con la paleta del sistema — logo en la portada,
  exportador `scripts/exportar_inventario.py` y glifos que salían como `?`
  corregidos (PR #12)
- [x] `SCRUM-84` restablecimiento de contraseña — códigos de respaldo en hash de un solo
  sentido (verificables sin la contraseña), dos pasos sin sesión y reinicio del segundo
  factor al restablecer
- [x] `SCRUM-85` atajos de teclado y búsqueda global — tabla única en `src/lib/atajos.js`;
  activos `Ctrl+B`, `Ctrl+F`, `Ctrl+N`, `Ctrl+Q`, `Supr`, `F11`, `Enter` y `Esc`
- [x] `SCRUM-86` franja de telemetría inferior — `BarraEstado` con el estado real
  de base de datos, APIs y chatbot
- [x] `SCRUM-87` notificaciones del sistema — pila de avisos en el proveedor de la
  aplicación, silenciables desde Ajustes
- [x] `SCRUM-88` modales de documento — detalles y edición como capas modales
  (`src/components/ModalDocumento.jsx`), con el alta y el visor

> **Claves de Jira (2026-09-30).** Los números de este archivo vienen de la
> numeración que `jira.md` mantuvo en paralelo. Al consultar el tablero por el
> MCP se comprobó que **Jira no tiene más allá de `SCRUM-66`** y que `SCRUM-57` a
> `SCRUM-66` son tickets de **área** (Backend, Frontend, UI / UX, Electron,
> Chatbot, API / Servicios, Búsqueda semántica, Testing / QA, Documentación /
> Release, Arquitectura / Core). `jira.md` ya usa las áreas como etiqueta y
> conserva el mapeo de la numeración antigua; aquí se mantienen los números
> originales para no romper las referencias a los commits ya publicados.

### Calidad de vida y diseño (2026-10-01) — cerrada

Revisión de Raven sobre la aplicación ya funcional, antes de abrir la Fase 4. No
estaba en la hoja de ruta; se incorpora como sección propia.

- [x] **Intro con más vida**: `src/lib/movimiento.js` envuelve anime.js y respeta
  la preferencia de movimiento —`sin-animacion` solo apagaba las animaciones CSS,
  no las de JS—; entrada escalonada y latido al pulsar
- [x] **Fondo de marca persistente**: partículas y nombre subieron de `Bienvenida`
  a `MarcoAcceso`, así que acompañan a bienvenida, acceso y registro
- [x] **Login limpio**: retirado el panel «Bóveda local» y sustituida la nota
  legal incrustada por un enlace **«Términos y uso»** con subpanel animado
- [x] **Ajustes al pie**, debajo del conmutador de tema, con **Auditoría** y
  **Conexión de modelos** como secciones propias; **tuerca** de acceso rápido en
  la sub-cabecera; **el logo pliega** la barra lateral
- [x] **Alta de documento con sus metadatos en el mismo acto** (formulario de
  registro: se elige el PDF y se rellenan nombre, descripción, titular y empresa)
- [x] **Catálogo de empresas**: tabla `Empresas` + `Personas.empresa_id`, con
  normalización que une las variantes de escritura, migración idempotente del
  texto libre, y servicio con alta, renombrado en cascada, **fusión de fichas** y
  baja sin borrar personas
- [x] **Panel de Personas por empresa** con filtro y catálogo como sugerencias
- [x] **Asistente flotante** en todas las secciones menos Ajustes
- [x] **Modelos**: la credencial se escribe también en el `.env` (0600) y hay
  **prueba real de conexión** contra el proveedor
- [x] **Franja de telemetría**: escribe el estado real (`BD disponible`,
  `APIs credencial lista`), no solo lo colorea
- [x] **Hueco de CRUD corregido**: al editar el titular de un documento, la
  persona vinculada se resolvía por subconsulta, así que sin titular no se
  guardaba nada y al cambiar la cédula se renombraba a la persona equivocada

**Verificación**: 178 pruebas (`unittest discover`) y sondas de la ventana real
(22/22, 23/23, 14/14, 19/19 y 9/9).

### Lo que queda de la Fase 3 y la Fase 4 (orden acordado 2026-10-01)

Hecho en el PR #16 (`v2.1 → main`), verificado con la suite (194 pruebas) y
conduciendo la ventana real de Electron:

1. [x] `SCRUM-81` extraer la estadística y los gráficos al backend — `3598f95`
2. [x] `SCRUM-82` dashboard de gráficos — `cf6d7a3`
3. [x] `SCRUM-84` **restablecer contraseña** — `b035737`; `senior-security` aplicada
   antes de tocar el flujo
4. [x] `SCRUM-87` notificaciones del sistema · `SCRUM-88` modales de documento —
   `bbe44a8` (un solo commit: ambos son el área `SCRUM-59` y ambos tocan
   `Documentos.jsx`)
5. [x] `SCRUM-85` atajos de teclado y búsqueda global — `dc0511a`
6. [x] **Fase 4, solo API** (modelos locales omitidos por decisión de Raven):
   streaming del chatbot, errores de red, decisión de motor de persistencia y
   **asistente anclado al proyecto** — `9cc138f`, `39dfa21` y `bd29981`. El
   asistente solo responde sobre el sistema y con los agregados reales del
   archivo; nunca recibe datos personales, contenido de documentos ni secretos

Evaluación (paralela, backend):

- [ ] `SCRUM-72` a `SCRUM-74` clasificación automática de documentos

---

## Fase 4 — Integración de APIs y modelos locales

Estado: **hecho, solo API** — Skill: `chatbot-streaming`. Los modelos locales
(`local-llm-fallback`) siguen **aparcados** por decisión de Raven del
2026-09-30.

**Cerrado el 2026-10-01** con el bloque del chatbot:

| Pieza | Dónde | Ticket |
| --- | --- | --- |
| Entrega progresiva de la respuesta (RF-16) | `chatbot.py` (`enviar_mensaje_stream`), `POST /api/chat/mensajes/stream` (SSE), `src/lib/api.js` (`transmitir`), `src/pages/Chatbot.jsx` | `SCRUM-34` |
| Tiempos límite, reintentos y errores de red accionables | `chatbot.py` (`_traducir_fallo`, `_con_reintentos`) | `SCRUM-35` |
| Continuidad de la conversación durante el flujo | `chatbot.py` (registro único del turno) + `tests/test_asistente.py` | `SCRUM-36` |
| **Asistente anclado al proyecto** | `backend/services/contexto.py`, reinyectado en cada turno | `SCRUM-61` (área) |
| Prueba real de generación desde el panel | `POST /api/chat/probar`, `src/pages/Modelos.jsx` | `SCRUM-62` (área) |
| Decisión de motor de persistencia | `docs/decision-persistencia.md` | `SCRUM-43` |

Dos decisiones que conviene recordar:

* **El asistente no puede filtrar lo que nunca recibe.** El contexto que se le
  entrega son **agregados** —cuántos documentos, reparto por empresa, titulares,
  catálogo y acciones de auditoría— y nada más: ni cédulas, ni nombres de
  titulares, ni nombres de archivo, ni contenido, ni claves, hashes, tokens o
  rutas. El prompt declara además el alcance estricto y prohíbe responder fuera
  del proyecto.
* **Se retiró el respaldo que fingía contestar.** Ante un 403 del proveedor, el
  servicio devolvía una respuesta enlatada «en modo local de prueba». Ahora dice
  el motivo real y accionable, que es lo que el panel de conexión ayuda a
  resolver. Una respuesta inventada es peor que un error honesto.

El panel de conexión ya existía (`SCRUM-64`, con escritura del `.env` y prueba
real de credencial); esta fase le añade la **prueba de generación** y la
posibilidad de elegir entre los modelos que la cuenta tiene de verdad.

### Cierre de la Fase 4 (2026-10-01)

Los tres defectos que aparecieron al probarla con la credencial real, ya
corregidos:

| Defecto | Causa | Corrección |
| --- | --- | --- |
| El `503` al usar el asistente | El modelo guardado (`gemini-2.0-flash`) estaba retirado; Google responde `503` a un modelo que ya no existe | El catálogo usa **alias** (`-latest`) que no caducan, la prueba de conexión sustituye el modelo retirado por uno vigente de la cuenta, y un `5xx` sobre un modelo pasa al siguiente candidato |
| La sesión se caía al guardar o probar la API | Los manejadores de modelos y del asistente eran `async def` con esperas **bloqueantes**: dejaban al servicio sin atender el sondeo de sesión durante hasta 25 s. El sondeo, además, cerraba la sesión ante **cualquier** fallo, no solo un 401 | Los manejadores pasan a `def` (FastAPI los ejecuta en un hilo aparte) y la sesión solo se cierra cuando el servicio **responde** que no hay sesión |
| El asistente mostraba su razonamiento | Los modelos con razonamiento devuelven sus pasos como partes marcadas (`thought`) y se concatenaban con el texto; además el prompt no lo prohibía, y los modelos pequeños lo escriben como texto normal | Se descartan las partes de pensamiento —en el flujo y en la respuesta completa— y el prompt exige responder directamente, sin analizar la petición ni enumerar opciones |

Y un cambio de sitio pedido por Raven: **Auditoría y Modelos salen de la barra de
secciones** del dashboard y quedan solo dentro de **Ajustes**, que es donde
corresponde a unos ajustes del sistema. Estaban en los dos sitios.

**Alcance inmediato: solo API (decisión 2026-09-30).** Hasta que el frontend y
el backend estén completos al 100 %, el chatbot funciona por API y **no** se
implementan modelos locales: el respaldo vía Ollama (`SCRUM-37` a `SCRUM-39`)
queda aparcado. Lo que sí se construye ahora es el **panel de conexión**
(pantalla propia, no un ajuste suelto): cargar clave y punto de conexión,
elegir el modelo por API y que el chatbot los adopte **sin reiniciar** la
aplicación. El panel se diseñará de forma que añadir proveedores locales
después sea una extensión, no una reescritura.

Se deja para el final porque depende de tener ya un frontend real (Fase 3)
donde mostrar el panel de modelos, y porque no bloquea el resto del
roadmap. La lógica de streaming/fallback en sí puede prototiparse antes en
el backend si Raven lo pide, pero el panel de usuario se construye aquí.

Secciones sugeridas:

1. **Streaming de respuesta (RF-16)**: reemplazar la espera bloqueante de
   la API de Gemini por entrega progresiva de tokens/fragmentos, expuesta
   al frontend vía el bridge.
2. **Manejo explícito de errores de red**: timeouts, reintentos, mensajes
   de estado visibles (usa los estados canónicos de Fase 3).
3. **Respaldo local vía Ollama (RF-17)** — *evaluación*: exponer una API
   REST local con modelos livianos por definir según consumo de hardware.
   No se cierra como compromiso firme hasta validar rendimiento con
   distintos modelos.
4. **Panel de selección de modelos y carga de APIs**: pantalla dedicada
   (React) para elegir modelo activo y cargar credenciales/endpoints, con
   activación automática sin reinicio manual.
5. **Decisión de motor de persistencia**: evaluar si SQLite (con WAL, como
   hoy) sigue siendo suficiente una vez el acceso pase por el puente
   Python↔Electron en producción, o si conviene otra alternativa
   accesible. Se documenta la decisión, no se cambia de motor sin
   aprobación explícita de Raven.

Criterio de cierre: streaming y manejo de errores funcional en producción;
panel de modelos operativo; decisión de motor de BD documentada. El punto 3
(Ollama) puede quedar abierto como "evaluación" sin bloquear el cierre de
la fase.

---

## Fase 5 — La app, instalable y publicada (GitHub Packages)

Estado: **por hacer** — se arranca con una **prueba de viabilidad**, no con el
pipeline completo. Reordena lo que antes era la Fase 7: se adelanta porque es lo
que convierte el proyecto en algo entregable, y porque las fases de evaluación
(Fase 6) no bloquean nada y pueden ir después sin coste.

**Objetivo.** Que alguien que no sabe nada del proyecto pueda instalarlo y
usarlo: descargar, ejecutar y que funcione. Ni «clona el repositorio», ni
«instala Python», ni «crea un entorno virtual».

### El problema real, dicho sin adornos

Hoy la aplicación necesita tres cosas que un usuario final no tiene ni debería
tener que conseguir:

1. **Un intérprete de Python** con `fastapi`, `uvicorn`, `cryptography`,
   `pyotp`, `PyMuPDF`, `numpy`… instalados.
2. **Un Node/Electron** que arranque la ventana.
3. **Saber que hay dos procesos** y que uno lanza al otro.

El instalador tiene que hacer desaparecer las tres. Eso es toda la fase.

### Vía técnica (a validar en la prueba de viabilidad)

**Empaquetado de la ventana: `electron-builder`.** Es el estándar para
Electron y da los dos formatos que hacen falta de una sola configuración:

| Plataforma | Formato | Por qué |
| --- | --- | --- |
| Windows | **NSIS `.exe`** | Es lo que la gente espera: doble clic, siguiente, siguiente. Genera también desinstalador |
| Linux | **AppImage** | Un solo archivo ejecutable, sin permisos de root ni repositorio. `.deb` como segundo formato si hace falta |

**El backend Python, sin que el usuario instale nada.** Dos caminos, y la prueba
de viabilidad debe decidir con datos cuál se queda:

* **Congelar el backend** (`PyInstaller` o `PyOxidizer`) a un binario por
  plataforma y meterlo como `extraResource` del paquete de Electron. El usuario
  nunca ve Python. Contra: un binario por plataforma y arquitectura, y hay que
  verificar que `cryptography` y `PyMuPDF` se congelen bien —son los que suelen
  dar guerra por dependencias nativas—.
* **Vendorizar un Python portable** (CPython *standalone* o `uv`) junto al
  paquete, con las dependencias ya instaladas en un directorio
  (`pip install --target`). Contra: pesa más y hay que resolver las rutas en
  tiempo de ejecución, pero es más transparente para depurar.

En ambos casos, **`electron/backend.js` ya está preparado**: `interprete()`
acepta `DATENJAGER_PYTHON`, así que basta con apuntarlo al binario o al
intérprete empaquetado. No hay que rehacer el arranque.

**Versionado y publicación.** Aquí conviene ser preciso, porque «GitHub
Packages» y «GitHub Releases» no son lo mismo:

* **GitHub Releases** es donde van los **instaladores** (`.exe`, `.AppImage`).
  Es el sitio natural para binarios de release, y es lo que consume
  `electron-updater` para las actualizaciones automáticas.
* **GitHub Packages** es un registro de paquetes (npm, contenedores, Maven…).
  Tiene sentido si publicamos además el paquete npm del proyecto —útil para
  instalar por `npm`, no para el usuario final— o una imagen de contenedor.
  Se usará para eso, y para llevar el control de versiones del paquete.
  
  en casos practicos conviene usar **GitHub Releases** con los comandos propios cuando se haya empaquetado

Un flujo de GitHub Actions que, al empujar una etiqueta `vX.Y.Z`, compile en
Windows y en Linux, adjunte los instaladores al Release y publique el paquete
npm en Packages. La versión sale de `package.json`; no se escribe a mano en dos
sitios.

**La web que ofrece Raven.** Una página con el instalador para descargar y, para
Linux, una línea de consola del estilo (La web se encargar **Raven** una vez este empaquetado y probado el instalador)
`curl -fsSL https://…/install.sh | sh`, que descarga el AppImage, lo deja en
`~/.local/bin` y crea el acceso directo. Para Windows, el `.exe` y —si el
tiempo alcanza— un manifiesto para `winget`. La web es el escaparate; los
binarios siguen viviendo en el Release.

### Lo que la instalación **no** puede traer

Por la filosofía del proyecto, y porque así está construido:

* **Nada de base de datos empaquetada.** `database.py` crea el archivo SQLite
  local en el primer arranque. El instalador no lleva datos, ni vacíos.
* **Nada de credenciales.** El `.env` y el almacén `modelos/` los crea el panel
  de conexión cuando el usuario carga su clave, con permisos `0600`.
* **Nada de tokens de confianza.** `tokens_confianza/` se genera en local.

Es decir: el instalador lleva **programa**, no **estado**. Cualquier cosa que
lleve estado del desarrollador es un defecto de la fase.

### Orden de trabajo

1. **Prueba de viabilidad (lo primero, y sin prometer nada):** empaquetar el
   backend con cada una de las dos vías y **medir**: peso del paquete, tiempo de
   arranque en frío y si `cryptography`, `PyMuPDF` y `uvicorn` funcionan
   congelados. Decidir con esos números, no por preferencia.
2. Instalador de **Linux** funcionando de punta a punta en una máquina limpia
   (contenedor o usuario nuevo): instalar, abrir, registrar usuario, subir un
   PDF, cerrar y volver a abrir con los datos intactos.
3. Instalador de **Windows** con el mismo recorrido, incluido el aviso de
   SmartScreen —**el `.exe` irá sin firmar**, porque firmar cuesta dinero; hay
   que documentar que el aviso es esperado y cómo continuar—.
4. **CI** en GitHub Actions: etiqueta → build en las dos plataformas → Release
   con los instaladores → paquete npm en Packages.
5. **Documentación de instalación** para alguien que llega nuevo: qué descargar,
   qué hace el sistema en el primer arranque y dónde quedan los datos.
6. **Retirada de CustomTkinter** una vez el instalador cubra todo lo que la
   interfaz antigua hacía.

Criterio de cierre: existe un instalador que funciona en Windows y Linux, se
publica con su versión, y una persona ajena al proyecto lo instala y lo usa
siguiendo solo la documentación.

---

## Fase 6 — Búsqueda semántica y clasificación automática (evaluación)

Estado: **evaluación** — Skill: `semantic-search-poc` — `SCRUM-72` a `SCRUM-74`
en `jira.md` (Sprint 5).

**Las dos evaluaciones van juntas porque comparten casi todo.** Buscar por
significado y clasificar por tipo son dos usos del mismo trabajo: extraer el
texto del PDF, partirlo en fragmentos y calcular sus embeddings. Hacerlas por
separado sería montar dos veces la misma tubería. Se evalúan juntas, se miden
por separado y se deciden por separado —puede salir bien una y mal la otra—.

Explícitamente **no comprometida** según el anteproyecto: se prueba durante el
semestre y se define o se descarta según resultados y consumo de hardware. Es
**backend-only**: no depende de qué frontend esté activo.

### La tubería compartida (se construye una vez)

1. **Extracción y fragmentación** del texto de los documentos ya indexados.
   Se reutiliza el camino de lectura de PDF que el sistema ya tiene.
2. **Embeddings** con `sentence-transformers` (`all-MiniLM-L6-v2` como punto de
   partida, que es pequeño y corre en CPU).
3. **Almacén vectorial local**: ChromaDB **o** la extensión `sqlite-vss` sobre
   el SQLite que ya existe. Se elige **una** vía tras el prototipo, no se
   mantienen las dos.

### Uso A — Búsqueda semántica

Complemento de la búsqueda léxica actual, **no su reemplazo**: quien busca un
número de cédula quiere coincidencia exacta, no «parecido». Se expone al
asistente, que es donde aporta: «¿qué contratos hablan de trabajo en altura?»
no se responde con `LIKE`.

### Uso B — Clasificación automática

Evaluar si un método de aprendizaje automático puede clasificar los PDF que ya
entran al sistema (afiliaciones, reportes de seguridad social, contratos
laborales…) sin que nadie elija la categoría a mano. El valor académico está en
la **medición**, no en la promesa.

1. **Corpus de evaluación**: los documentos reales ya cargados, etiquetados a
   mano como referencia (sin sacarlos del sistema).
2. **Línea base sin modelo**: reglas sobre el texto extraído (palabras clave,
   nombre del archivo, entidad asociada). **Si esto ya acierta lo suficiente, es
   la respuesta más barata y hay que decirlo**: un clasificador de verdad solo
   se justifica si le gana con margen.
3. **Prototipo**: un clasificador simple sobre los embeddings de la tubería
   compartida; alternativamente, un modelo de cero disparos.
4. **Medición**: precisión, exhaustividad y matriz de confusión sobre el corpus
   etiquetado.

### Decisión

Se documenta cada uso por separado —continuar, ajustar o descartar— con los
números que lo respalden, incluido el consumo de hardware. **No se integra a la
interfaz en esta fase**: si los números lo justifican, se convierte en tarea
propia. Descartar con datos es un resultado válido, y el anteproyecto lo
contempla.

---

## Fase 7 — Pulido final: diseño, animaciones y orden del repositorio

Estado: **por hacer** — es la última fase, y la más fácil de posponer sin coste
porque no bloquea nada.

### 1. Diseño, animaciones y retoques de interfaz

Lo que quede por pulir una vez todo funcione: detalles de la transición entre
temas, micro-interacciones que falten, revisión de los estados de carga y de
error pantalla por pantalla, y los cambios ligeros de interfaz que aparezcan al
usarla de verdad. **Se hace al final a propósito**: pulir antes de que la app
sea instalable es pulir algo que quizá haya que mover.

### 2. Orden del repositorio: los `.py` de la raíz

Hoy la raíz tiene **13 módulos Python, 8.840 líneas**, mezclando el backend real
con la interfaz antigua de CustomTkinter. Eso es lo que queda del desacople: el
código está separado por dentro, pero no por fuera.

El reparto, medido:

| Se van a `backend/` (backend puro, sin Tkinter) | Líneas |
| --- | --- |
| `chatbot.py` (servicio del asistente) | 612 |
| `database.py` (SQLite) | 485 |
| `reporter.py` (informes) | 396 |
| `transhumano.py` (textos de la declaración) | 262 |
| `encryption.py` (AES-256-GCM) | 130 |
| `config.py` (carga del `.env`) | 107 |

| Se **retiran** (interfaz CustomTkinter) | Líneas |
| --- | --- |
| `main.py` | 3.556 |
| `ui_components.py` | 1.271 |
| `pdf_manager.py` | 709 |
| `personas.py` | 459 |
| `audit.py` | 404 |
| `chatbot_ui.py` | 353 |
| `icons.py` | 96 |

**Los dos trabajos son el mismo.** No tiene sentido mover `main.py` a
`backend/`: se retira. Y los siete módulos de interfaz solo pueden retirarse
cuando el instalador (Fase 5) cubra todo lo que la interfaz antigua hacía, así
que esta parte depende de aquella.

**Cómo hacerlo sin romper nada**, en este orden:

1. Retirar primero la interfaz antigua: es la que *importa* los módulos de
   backend, no al revés. Mientras esté, mover los módulos obliga a tocar sus
   importaciones para nada.
2. Mover los seis módulos de backend, uno por commit, actualizando
   importaciones en `backend/`, `tests/` y `scripts/`. La suite es la red de
   seguridad: si sigue en verde, el movimiento está bien.
3. Actualizar `CLAUDE.md` (§3 y §5) y `backend/README.md`.

**Aviso, y es una parada obligatoria:** `database.py` y `encryption.py` son
**cifrado y base de datos**. Moverlos no cambia ni una línea de criptografía,
pero toca los dos archivos que `CLAUDE.md` §10 marca como sensibles. Se pide
aprobación explícita de Raven antes de empezar esa parte, no después.

Criterio de cierre: la raíz no tiene módulos Python de la aplicación —solo
configuración y puntos de entrada—, la suite pasa en verde y CustomTkinter ya no
está en el proyecto.

---

## Criterio de cierre del proyecto

`SCRUM-75` a `SCRUM-78` en `jira.md` (Sprint 5). Además del criterio de cada
fase, el proyecto se considera entregable cuando:

* existe un **instalador de escritorio** que funciona en Windows y Linux, con su
  versión publicada y sus instaladores descargables;
* una persona ajena al proyecto lo instala y lo usa **sin instalar Python ni
  dependencias a mano** y siguiendo solo la documentación;
* el código Python que queda es **backend funcional** (servicios, cifrado, base
  de datos, asistente) y vive bajo `backend/`;
* **CustomTkinter ya no está** en el repositorio;
* la base de datos, el `.env` y los almacenes cifrados se generan **en local**
  en la instalación: el instalador lleva programa, no estado.

---

## Checklist de commits (aplica a toda fase)

- [ ] El commit corresponde a **una sola sección**, no a varias.
- [ ] El proyecto queda funcional después del commit.
- [ ] El mensaje de commit describe el flujo real resuelto (no "wip" ni
      "cambios varios").
- [ ] Si el cambio tocó cifrado, autenticación, o más de 2 archivos de UI,
      fue aprobado explícitamente por Raven antes del commit (ver
      `CLAUDE.md`, sección 10).
- [ ] `add` / `commit` / `push` **y `pr`** los ejecuta el agente con
      autorización de Raven (ver `CLAUDE.md` §8), siempre desde `v2.1` y con
      `--base main` (ver `jira.md`).

## Seguimiento de progreso

| Fase | Estado | Última actualización |
| --- | --- | --- |
| 0. Preparación | hecho (mockups recibidos y versionados en `SCRUM-79`) | 2026-10-01 |
| 1. Pulir backend Python | hecho | 2026-09-28 |
| 2. Migración a Electron/React/Tailwind (andamiaje) | hecho | 2026-09-28 |
| 3. Frontend conforme a mockups | **cerrada salvo el empaquetado** — además de lo anterior (base visual, movimiento, pantallas nuevas, iconos, reportes con logo, telemetría, catálogo de empresas y calidad de vida), el PR #16 cierra `SCRUM-81`, `82`, `84`, `85`, `87` y `88`. Solo queda el empaquetado, que es la Fase 5 | 2026-10-01 |
| 4. Integración de APIs y modelos locales | **hecho, solo API** — `SCRUM-34` (streaming), `35` (tiempos y reintentos), `36` (continuidad), `SCRUM-61` (asistente anclado al proyecto con datos reales en vivo) y `SCRUM-43` (SQLite con WAL, decisión en `docs/decision-persistencia.md`). El panel de conexión permite cargar la credencial, probarla y probar la generación. Los modelos locales quedan omitidos por decisión de Raven | 2026-10-01 |
| 5. App instalable y publicada (GitHub Packages) | **por hacer** — adelantada desde el final (ver «Reordenación» abajo). Arranca por la **prueba de viabilidad** del backend empaquetado | 2026-10-01 |
| 6. Búsqueda semántica + clasificación (evaluación) | evaluación — las dos juntas: comparten extracción de texto y embeddings | 2026-10-01 |
| 7. Pulido final: diseño, animaciones y orden del repositorio | por hacer — la retirada de CustomTkinter depende de que la Fase 5 cubra todo | 2026-10-01 |

### Reordenación de fases (2026-10-01, decisión de Raven)

El orden cambia respecto al planteamiento inicial, por dos razones:

* **La instalación sube al puesto 5.** Es lo que convierte el proyecto en algo
  entregable y lo que permite retirar CustomTkinter; dejarla para el final
  obligaba a pulir una interfaz que quizá hubiera que mover.
* **Búsqueda semántica y clasificación se juntan en la Fase 6.** Comparten casi
  todo el trabajo —extracción de texto, fragmentación, embeddings—, así que
  separarlas era montar dos veces la misma tubería. Se evalúan juntas, se miden
  por separado y se deciden por separado.

El orden queda: **5 → instalable**, **6 → evaluación (búsqueda + clasificación)**,
**7 → pulido y orden del repositorio**. Ninguna de las tres bloquea a las otras
dos más allá de lo indicado en cada una.
Actualiza esta tabla al cerrar cada fase o hito relevante, y refleja el
cambio en `CLAUDE.md` (sección 12) en la misma sesión.

---

## Qué ya está hecho — no volver a hacerlo

Esta lista existe para no repetir trabajo ni re-abrir decisiones cerradas.
Antes de proponer una tarea, comprueba aquí.

**Backend (`backend/`, sin Tkinter, importable sin display)**

| Pieza | Archivo | Estado |
| --- | --- | --- |
| Errores tipados | `backend/errors.py` | hecho |
| Servicios de negocio | `backend/services/{documentos,personas,auditoria,reportes,autenticacion}.py` | hecho |
| Estado de aplicación | `backend/state.py` (`AppState`, `SesionUsuario`) | hecho |
| Fachada de comandos | `backend/commands.py` (punto de entrada único) | hecho |
| Puente HTTP | `backend/server.py` (FastAPI + uvicorn, token por proceso) | hecho |
| Almacén cifrado de tokens | `backend/tokens.py` + `scripts/cifrar_tokens_confianza.py` | hecho |
| Contrato | `backend/README.md` | hecho |

**Autenticación: ya no vive en `main.py`.** Está en
`backend/services/autenticacion.py`: bloqueo por intentos, migración de hashes
heredados, derivación de la clave de sesión, migración del material 2FA de
`ENC:` a `ENCK:`, verificación TOTP, códigos de respaldo de un solo uso,
activación/desactivación del 2FA, cambio de contraseña con re-cifrado y token
de confianza. Las primitivas de `database.py` y `encryption.py` **no** se
tocaron: cualquier cambio futuro ahí es un cambio de cifrado y exige
aprobación explícita (CLAUDE.md §10).

**Puente HTTP:** `POST /api/sesion` (con `/2fa` y `/respaldo`), `GET|DELETE /api/sesion`,
`POST /api/sesion/heredar`, `GET /api/cuenta` y `/api/cuenta/2fa/{preparar,activar,desactivar,codigos}`,
`POST /api/cuenta/contrasena`, `DELETE /api/cuenta/confianza`, más documentos,
personas, auditoría, reportes y asistente.

**Frontend (`src/`, `electron/`):** andamiaje Vite + React + Tailwind, puente
Electron (`electron/{main,preload,backend,archivos}.js`) y los cinco paneles
funcionales: `Acceso` (login y 2FA), `Documentos`, `Personas`, `Auditoria` y
`Cuenta` (apariencia, 2FA, contraseña, confianza).

**Pendiente de verdad:** **nada del desacople.** El alta de usuario se movió al
backend en `SCRUM-57` y `ComandosDatenJager.operaciones_pendientes()` quedó
vacío. Lo único que sigue en pausa es el empaquetado (`SCRUM-26`, retomado por
`SCRUM-75`/`SCRUM-76`).

**Pantallas nuevas (Fase 3, Sprint 5).** Cerradas el 2026-09-30 con
`SCRUM-57` a `SCRUM-64`:

| Pieza | Archivo | Estado |
| --- | --- | --- |
| Alta de usuario | `backend/services/autenticacion.py` (`registrar_usuario`), `POST /api/registro` | hecho |
| Registro y alta de 2FA | `src/pages/Registro.jsx`, `src/components/AltaSegundoFactor.jsx` | hecho |
| Panel del asistente | `src/pages/Chatbot.jsx` (barra lateral por botones) | hecho |
| Visor de PDF | `src/components/VisorPdf.jsx` (`<iframe>` + `Blob`, sin dependencias) | hecho |
| Reportes | `src/pages/Reportes.jsx`, `GET /api/reportes/por-empresa` y `/por-dia` | hecho |
| Datos y estadísticas | `src/pages/Estadisticas.jsx` | hecho |
| Ajustes completos | `src/pages/Cuenta.jsx` (sesión, almacenamiento, atajos, «Acerca de») | hecho |
| Conexión de modelos | `backend/services/modelos.py`, `src/pages/Modelos.jsx`, `GET|POST /api/modelos` | hecho |
| Base caída visible | `GET /api/salud` (`base_datos`), `DATENJAGER_ERROR`, `electron/backend.js` | hecho (`SCRUM-89`) |
| Puerto ocupado | `electron/backend.js` (8756→8759→puerto del sistema) y el motivo visible en Bienvenida/Acceso | hecho (`SCRUM-89`) |
| Modo desarrollo (`npm run dev`) | `DATENJAGER_CORS_ORIGENES` en `backend/server.py`, definido por `electron/main.js` solo con `--dev` | hecho (`SCRUM-89`) |

**Variables de entorno del servicio:** `DATENJAGER_DB` (base alternativa) y
`DATENJAGER_TOKENS` (almacén alternativo de tokens). Las pruebas y las sondas
las usan siempre para no tocar los datos reales del usuario.

**Cómo verificar sin rehacer:** `./venv/bin/python -m unittest discover -s tests -t .`
(142 pruebas, sin Tkinter), `npx vite build`, `./node_modules/.bin/electron . --no-sandbox`.
