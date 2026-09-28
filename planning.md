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

Estado: **por hacer**

- [x] Revisar el contenido de `/assets/mockups` disponible hasta ahora
      (5 pantallas: Configuración/Appearance, Auditoría Ley 1581 en modo
      claro, Expedientes + Hermes IA en modo claro, Auditoría Ley 1581 en
      modo oscuro, Expedientes + Hermes IA en modo oscuro) y el logo del
      proyecto. Ver resumen, paleta extraída y alcance en la Fase 3.
      **Confirmado con Raven**: estos mockups son **inspiración de
      estilo** (muy influenciados por "Hermes Desktop"), no una
      especificación 1:1 a replicar.
- [ ] Mockups pendientes de recibir antes de que la Fase 3 llegue a esas
      pantallas: login, verificación 2FA, registro, setup 2FA (QR) y el
      dashboard de gráficos (donut por empresa + línea de tendencia,
      equivalente a `DashboardWidget`). Ninguna de las 5 imágenes actuales
      los cubre.
- [ ] Confirmar `.claudeignore` vigente para que el agente no indexe
      artefactos irrelevantes (venv, builds, node_modules cuando exista
      frontend).
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

Estado: **por hacer** — Skill: `electron-react-migration`

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

---

## Fase 3 — Construcción del frontend conforme a los mockups

Estado: **por hacer** — Skill: `electron-react-migration` +
`ui-states-animations`

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
  **sigue como Fase 5, en evaluación** — que ya tenga un ítem diseñado
  en el mockup no la promueve a compromiso cerrado.

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
3. **Estados canónicos y transiciones**: vacío, error, carga
   (*skeleton*), y animaciones (fade, hover, easing) — implementados
   directamente en React/Tailwind, con opción de deshabilitarlas desde
   configuración de usuario.

Criterio de cierre: cada pantalla migrada refleja la paleta e identidad
visual de los mockups (sin exigir coincidencia pixel a pixel) y cubre
únicamente las secciones/funcionalidades presentes en el código Python
actual; estados canónicos y transiciones activos en al menos las
pantallas principales (login, dashboard, PDFs).

---

## Fase 4 — Integración de APIs y modelos locales

Estado: **por hacer** — Skill: `chatbot-streaming` + `local-llm-fallback`

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

## Fase 5 — Búsqueda semántica sobre el corpus documental (evaluación, paralela)

Estado: **evaluación** — Skill: `semantic-search-poc`

Explícitamente no comprometida al 100% según el anteproyecto: se testea
durante el semestre y se define o se descarta según resultados y consumo
de hardware. Es **backend-only**: no depende de qué frontend esté activo,
así que puede evaluarse en paralelo con cualquier fase posterior a la
Fase 1, sin bloquear el camino principal.

Secciones sugeridas (como prototipo, no como entrega cerrada):

1. Extracción y fragmentación de texto de los documentos ya indexados.
2. Generación de embeddings con `sentence-transformers`
   (`all-MiniLM-L6-v2` como punto de partida).
3. Almacenamiento vectorial local: ChromaDB **o** extensión `sqlite-vss`
   sobre el motor SQLite ya existente — elegir una sola vía tras el
   prototipo, no mantener ambas.
4. Integración de la búsqueda semántica como complemento (no reemplazo) de
   la búsqueda léxica actual, expuesta al chatbot.

Criterio de cierre: decisión documentada de continuar o descartar, con datos
de consumo de hardware y calidad de resultados que la respalden.

---

## Checklist de commits (aplica a toda fase)

- [ ] El commit corresponde a **una sola sección**, no a varias.
- [ ] El proyecto queda funcional después del commit.
- [ ] El mensaje de commit describe el flujo real resuelto (no "wip" ni
      "cambios varios").
- [ ] Si el cambio tocó cifrado, autenticación, o más de 2 archivos de UI,
      fue aprobado explícitamente por Raven antes del commit (ver
      `CLAUDE.md`, sección 10).
- [ ] Raven ejecuta `add` / `commit` / `push` — el agente nunca lo hace.

## Seguimiento de progreso

| Fase | Estado | Última actualización |
| --- | --- | --- |
| 0. Preparación | por hacer (mockups pendientes de recibir) | 2026-09-28 |
| 1. Pulir backend Python | hecho | 2026-09-28 |
| 2. Migración a Electron/React/Tailwind (andamiaje) | en progreso | 2026-09-28 |
| 3. Frontend conforme a mockups | por hacer | — |
| 4. Integración de APIs y modelos locales | por hacer | — |
| 5. Búsqueda semántica (evaluación) | evaluación | — |

Actualiza esta tabla al cerrar cada fase o hito relevante, y refleja el
cambio en `CLAUDE.md` (sección 12) en la misma sesión.
