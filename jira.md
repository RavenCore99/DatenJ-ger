# jira.md — Guía de trabajo Jira y commits

**Regla de ramas:** siempre se trabaja desde la rama `v2.1`; nunca crear o usar
otras ramas. Los PR se abren desde `v2.1` y se hace el merge a `main`.

para los PR, los peudes hacer siempore y cuando cumplas con las condiciones y etiquetas que hacen parte de cada archivo. ejemplo:

gh pr create --base main --head v2.1 --title "[SPRINT-2] SCRUM-5 a SCRUM-11: Implementación de funcionalidades del Sprint 1" --body "Desacoplar logica de backend python y levantar frontend con Electron/React/Tailwind conectando al backed.

     ### Tickets incluidos:
     - SCRUM-12
     - SCRUM-13
     - SCRUM-14
     - SCRUM-15
     - SCRUM-16
     - SCRUM-17
     - SCRUM-18"


el titulo del PR debe hacer parte del sprint que se esta trabajando. la descripcion o body debe tener la etiqueta SCRUM-# que referencia a la secicon del codigo y funcionalidad. con una descripcion
cuando se cierre el pr con la funcionalidad probada. hacer el merge correspondiente

es vital que los pr se mergean desde la rama v2.1 hasta la rama main


## Propósito

Este archivo sirve como referencia para cualquier agente o desarrollador que trabaje sobre **DatenJäger**.

Las tareas deben ejecutarse siguiendo los sprints y el orden definido en Jira. Cada cambio de código debe poder relacionarse con una tarea `SCRUM-#`.

### Regla principal

Cada commit debe:

- Ser corto y descriptivo.
- Referenciar el identificador de Jira correspondiente.
- Usar una etiqueta de tipo de cambio.
- No mencionar el nombre del agente, IA, asistente o herramienta que realizó el cambio.
- Representar un cambio acotado y verificable.
- Evitar mezclar tareas diferentes en un mismo commit cuando puedan separarse.

Formato recomendado:

```text
<tipo>(SCRUM-#): descripción corta
```

Ejemplos:

```text
feat(SCRUM-12): separa el CRUD de documentos
fix(SCRUM-18): corrige acceso al servicio PDF
refactor(SCRUM-16): extrae el estado de sesión
test(SCRUM-18): valida backend sin Tkinter
docs(SCRUM-19): documenta la extracción del backend
```

---

# Tipos de commit

| Tipo | Uso |
|---|---|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de un comportamiento existente |
| `bug` | Corrección asociada explícitamente a un defecto detectado |
| `hotfix` | Corrección urgente que no puede esperar al flujo normal |
| `improvement` | Mejora de una funcionalidad existente sin introducir una capacidad completamente nueva |
| `refactor` | Reestructuración interna sin cambiar el comportamiento esperado |
| `test` | Creación o modificación de pruebas |
| `docs` | Documentación |
| `ui` | Cambios visuales o de interfaz |
| `style` | Formato, estilos o convenciones sin cambio funcional |
| `perf` | Mejora de rendimiento |
| `build` | Build, empaquetado o instalador |
| `config` | Configuración del proyecto |
| `chore` | Mantenimiento técnico que no encaja en los anteriores |

### Cuándo usar `bug` y `hotfix`

`bug` se utiliza cuando la tarea consiste en corregir un defecto identificado.

`hotfix` se reserva para una corrección urgente que debe aplicarse fuera del flujo normal del sprint.

No usar `hotfix` simplemente porque una tarea sea importante.

---

# Sprint 1 — Diagnóstico

**Sprint:** `DJ S1 — Diagnóstico` | **Fase terminada**

**Objetivo:** diagnóstico, documentación, requisitos, UML/ER, mecanismo Python↔Electron y revisión de mockups.

| Jira | Tarea | Etiquetas adicionales sugeridas |
|---|---|---|
| `SCRUM-5` | Auditar módulos y acoplamientos del backend actual | `backend`, `fase-1`, `refactor` |
| `SCRUM-6` | Consolidar documentación base del semestre | `documentacion`, `fase-0` |
| `SCRUM-7` | Revisar RF/RNF y dependencias arquitectónicas | `requisitos`, `arquitectura` |
| `SCRUM-8` | Actualizar UML y modelo ER | `uml`, `arquitectura` |
| `SCRUM-9` | Definir mecanismo Python-Electron | `fase-0`, `electron` |
| `SCRUM-10` | Validar mockups y alcance funcional | `mockups`, `frontend` |
| `SCRUM-11` | Cerrar diagnóstico y preparar Fase 1 | `hito`, `fase-1` |

### Commits esperados

```text
docs(SCRUM-6): actualiza documentación base
docs(SCRUM-7): alinea requisitos del sistema
docs(SCRUM-8): actualiza modelos UML y ER
config(SCRUM-9): define integración Python Electron
docs(SCRUM-10): delimita alcance de mockups
```

---
> El **Sprint 2 está cerrado**. El siguiente trabajo es el **Sprint 3**
> (Frontend + UI) y no debe volver a tocar lo ya hecho aquí: el desacople del
> backend, el puente, los cinco paneles funcionales y la autenticación ya
> viven en el backend y están verificados.

# Sprint 2 — Backend + Andamiaje   | pr actual "[SPRINT-2] SCRUM-5 a SCRUM-11: Implementación de funcionalidades del Sprint 1- #9"

**Sprint:** `DJ S2 — Backend + Andamiaje`

**Objetivo:** desacoplar la lógica del backend Python y levantar el andamiaje funcional Electron/React/Tailwind conectado al backend.

**Estado: Sprint 2 cerrado (2026-09-28) — `SCRUM-12` a `SCRUM-25` hechos y publicados en `origin/v2.1`.**

| Jira | Tarea | Etiquetas adicionales sugeridas | Estado | Commit(s) |
|---|---|---|---|---|
| `SCRUM-12` | Extraer CRUD de PDF de la UI | `backend`, `pdf-manager`, `refactor` | hecho | `171eba9` |
| `SCRUM-13` | Extraer CRUD de personas de la UI | `backend`, `personas`, `refactor` | hecho | `fbc6919` |
| `SCRUM-14` | Separar auditoría de la interfaz | `backend`, `auditoria`, `refactor` | hecho | `c42e996` |
| `SCRUM-15` | Consolidar servicio del chatbot | `backend`, `chatbot`, `refactor` | hecho | `8820c02` |
| `SCRUM-16` | Implementar capa de estado de aplicación | `arquitectura`, `rnf-07`, `refactor` | hecho | `a0f20b4` |
| `SCRUM-17` | Crear capa de comandos y rutas | `arquitectura`, `servicios`, `refactor` | hecho | `df258ea` |
| `SCRUM-18` | Probar backend sin Tkinter | `testing`, `backend` | hecho | `d8add47` |
| `SCRUM-19` | Documentar cierre de extracción backend | `documentacion`, `hito` | hecho | `aa7c94e`, `05b02f8` |
| `SCRUM-20` | Crear andamiaje Electron + React + Tailwind | `electron`, `react`, `build` | hecho | `b8c0b8b` |
| `SCRUM-21` | Implementar bridge Python-Electron | `electron`, `bridge`, `backend` | hecho | `0de7137`, `50cb5db`, `111b4f2` |
| `SCRUM-22` | Migrar login y 2FA funcionales | `electron`, `auth`, `feat` | hecho | `2d67e56`, `93b6680` |
| `SCRUM-23` | Migrar panel documental funcional | `electron`, `pdf-manager`, `feat` | hecho | `cf59b76` |
| `SCRUM-24` | Migrar personas y auditoría funcional | `electron`, `frontend`, `feat` | hecho | `73ded75` |
| `SCRUM-25` | Migrar configuración y cuenta funcional | `electron`, `configuracion`, `feat` | hecho | `5aec953`, `0ba7ff5`, `27e6e60` |
| `SCRUM-26` | Generar instalador inicial | `electron`, `build`, `release` | **en pausa** | — |

`SCRUM-26` queda en pausa: hay que ver cómo generarlo y publicarlo con GitHub
Packages para que funcione tanto en Windows como en Linux.

### Cómo comprobar el estado del Sprint 2 sin repetir trabajo

```bash
./venv/bin/python -m unittest discover -s tests -t .     # 142 pruebas, sin Tkinter (121 al cerrar el Sprint 2)
npx vite build                                            # el frontend compila
./node_modules/.bin/electron . --no-sandbox              # arranca el sistema completo
npm run dev                                               # modo desarrollo (Vite + Electron), verificado
```

La autenticación ya **no** vive en `main.py`: está en
`backend/services/autenticacion.py` y se expone por el puente (`POST /api/sesion`,
`/api/sesion/2fa`, `/api/sesion/respaldo`, `GET /api/cuenta` y `/api/cuenta/...`).
Los tokens de confianza ya **no** están en claro en `config.json`: viven cifrados
en `tokens_confianza/` (ignorado por git). **No queda nada pendiente en el
desacople**: el alta de usuario se movió al backend en `SCRUM-57`
(`POST /api/registro`) y `ComandosDatenJager.operaciones_pendientes()` quedó
vacío.

### Commits esperados

```text
refactor(SCRUM-12): separa el CRUD de documentos
refactor(SCRUM-13): separa el CRUD de personas
refactor(SCRUM-14): desacopla la auditoría
refactor(SCRUM-15): consolida el servicio chatbot
refactor(SCRUM-16): extrae el estado de aplicación
refactor(SCRUM-17): crea rutas de servicio
test(SCRUM-18): valida backend sin Tkinter
docs(SCRUM-19): documenta extracción del backend
build(SCRUM-20): crea andamiaje Electron
feat(SCRUM-21): conecta bridge Python Electron
feat(SCRUM-22): migra login y 2FA
feat(SCRUM-23): migra panel documental
feat(SCRUM-24): migra personas y auditoría
feat(SCRUM-25): migra configuración y cuenta
build(SCRUM-26): genera instalador inicial
```

---

# Sprint 3 — Frontend + UI

**Sprint:** `DJ S3 — Frontend + UI`

**Objetivo:** construir el frontend React/Tailwind conforme a los mockups y aplicar estados y transiciones reutilizables.

> Las **pantallas nuevas** (registro, setup 2FA, chatbot, visor de PDF,
> reportes, estadísticas, ajustes completos, conexión de modelos) y el
> **movimiento e identidad visual** están en el Sprint 5, no aquí.

| Jira | Tarea | Etiquetas adicionales sugeridas |
|---|---|---|
| `SCRUM-27` | Definir tokens visuales en Tailwind | `ui`, `tailwind`, `design-system` |
| `SCRUM-28` | Implementar layout base inspirado en mockups | `ui`, `components`, `frontend` |
| `SCRUM-29` | Migrar visualmente login, 2FA y documentos | `ui`, `frontend`, `improvement` |
| `SCRUM-30` | Migrar visualmente personas y auditoría | `ui`, `frontend`, `improvement` |
| `SCRUM-31` | Migrar visualmente configuración y cuenta | `ui`, `configuracion`, `improvement` |
| `SCRUM-32` | Implementar estados y transiciones en React | `ui`, `ui-states`, `animation` |

### Commits esperados

```text
ui(SCRUM-27): define tokens visuales
ui(SCRUM-28): crea layout base
improvement(SCRUM-29): ajusta login y documentos
improvement(SCRUM-30): ajusta personas y auditoría
improvement(SCRUM-31): ajusta configuración y cuenta
feat(SCRUM-32): añade estados y transiciones
```

---

# Sprint 4 — APIs + Modelos + Cierre

**Sprint:** `DJ S4 — APIs + Cierre`

**Objetivo:** integración de APIs, chatbot, evaluación de modelos locales, persistencia, búsqueda semántica, pruebas, documentación y entrega.

`SCRUM-33` funciona como bloque coordinador del sprint.

## Bloque A — Chatbot

| Jira | Tarea | Etiquetas adicionales |
|---|---|---|
| `SCRUM-34` | Implementar streaming del chatbot (RF-16) | `chatbot`, `rf-16`, `feat` |
| `SCRUM-35` | Implementar timeouts y reintentos | `chatbot`, `errores-red`, `fix` |
| `SCRUM-36` | Validar continuidad de conversación durante streaming | `chatbot`, `testing` |
| `SCRUM-37` | Evaluar Ollama como respaldo local (RF-17) | `ollama`, `evaluacion` |
| `SCRUM-38` | Definir criterio de fallback Gemini → Ollama | `ollama`, `rf-17`, `arquitectura` |
| `SCRUM-39` | Implementar prototipo de fallback local | `ollama`, `rf-17`, `evaluacion` |

> **`SCRUM-34`, `SCRUM-35` y `SCRUM-36` hechos** (PR de la Fase 4, 2026-10-01,
> `9cc138f`): la respuesta llega **por fragmentos** (`POST
> /api/chat/mensajes/stream`, SSE), con tiempos límite, reintentos de espera
> creciente y mensajes accionables por código de error; y el turno se registra
> **una sola vez**, conservando lo que el usuario llegó a ver si el flujo se
> corta. Además el asistente queda **anclado al proyecto**
> (`backend/services/contexto.py`): recibe solo agregados reales del sistema y
> responde únicamente sobre DatenJäger.

> **`SCRUM-37` a `SCRUM-39` aparcados (2026-09-30).** Raven decidió que no se
> implementan modelos locales hasta que el frontend y el backend estén completos
> al 100 %; por ahora el chatbot funciona **solo por API** (`SCRUM-61`/`SCRUM-62`).

## Bloque B — APIs y backend

| Jira | Tarea | Etiquetas adicionales |
|---|---|---|
| `SCRUM-40` | Definir API local del backend | `api`, `backend`, `arquitectura` |
| `SCRUM-41` | Integrar autenticación y 2FA mediante API | `api`, `auth`, `feat` |
| `SCRUM-42` | Integrar documentos, personas y auditoría mediante API | `api`, `integracion`, `feat` |
| `SCRUM-43` | Evaluar persistencia de modelos y datos | `persistencia`, `evaluacion` |

> **`SCRUM-43` decidido** (2026-10-01, `bd29981`): se mantiene **SQLite con
> WAL**. El patrón real de acceso —un solo proceso, una conexión y `db_lock`
> serializando, el renderer sin tocar la base— no justifica un motor
> cliente-servidor, y cambiarlo encarecería el instalador de la Fase 7. La
> decisión completa y sus criterios de revisión están en
> `docs/decision-persistencia.md`.

## Bloque C — Búsqueda semántica

| Jira | Tarea | Etiquetas adicionales |
|---|---|---|
| `SCRUM-44` | POC de extracción y fragmentación documental | `busqueda-semantica`, `rf-15`, `poc` |
| `SCRUM-45` | Generar embeddings con all-MiniLM-L6-v2 | `embeddings`, `evaluacion` |
| `SCRUM-46` | Comparar almacenamiento vectorial | `vector-db`, `evaluacion` |
| `SCRUM-47` | Integrar búsqueda semántica como complemento | `busqueda-semantica`, `chatbot`, `feat` |
| `SCRUM-48` | Evaluar calidad de resultados semánticos | `busqueda-semantica`, `evaluacion` |
| `SCRUM-49` | Decidir continuidad de búsqueda semántica | `busqueda-semantica`, `decision` |

## Bloque D — Validación

| Jira | Tarea | Etiquetas adicionales |
|---|---|---|
| `SCRUM-50` | Pruebas end-to-end del flujo principal | `testing`, `e2e` |
| `SCRUM-51` | Pruebas de regresión del sistema existente | `testing`, `regresion`, `bug` |

## Bloque E — Documentación y entrega

| Jira | Tarea | Etiquetas adicionales |
|---|---|---|
| `SCRUM-52` | Documentar arquitectura final | `documentacion`, `arquitectura` |
| `SCRUM-53` | Documentar resultados de evaluación | `documentacion`, `evaluacion` |
| `SCRUM-54` | Preparar entrega e instalador final | `release`, `electron`, `build` |
| `SCRUM-55` | Preparar evidencia de pruebas y demostración | `sustentacion`, `documentacion` |
| `SCRUM-56` | Cerrar backlog técnico del semestre | `cierre`, `roadmap` |

### Commits esperados

```text
feat(SCRUM-34): implementa streaming del chatbot
fix(SCRUM-35): corrige reintentos de red
test(SCRUM-36): valida continuidad del chat
docs(SCRUM-37): registra evaluación de Ollama
docs(SCRUM-38): define criterio de fallback
feat(SCRUM-39): implementa fallback local
feat(SCRUM-40): expone API local
feat(SCRUM-41): integra autenticación por API
feat(SCRUM-42): integra servicios documentales
docs(SCRUM-43): documenta evaluación de persistencia
feat(SCRUM-44): crea POC de fragmentación
feat(SCRUM-45): genera embeddings
perf(SCRUM-46): compara almacenamiento vectorial
feat(SCRUM-47): integra búsqueda semántica
test(SCRUM-48): evalúa resultados semánticos
docs(SCRUM-49): registra decisión semántica
test(SCRUM-50): valida flujo end-to-end
bug(SCRUM-51): corrige regresión detectada
docs(SCRUM-52): actualiza arquitectura final
docs(SCRUM-53): registra resultados técnicos
build(SCRUM-54): prepara instalador final
docs(SCRUM-55): organiza evidencias de entrega
docs(SCRUM-56): cierra backlog técnico
```

---

# Sprint 5 — Paneles avanzados, datos y empaquetado

**Sprint:** `DJ S5 — Frontend avanzado y cierre`

**Objetivo:** construir las pantallas que todavía no existen, dar identidad
visual y movimiento al frontend, evaluar la clasificación automática de
documentos y dejar el proyecto instalable y publicable.

> Estos trabajos **amplían** la Fase 3 y la Fase 4 de `planning.md`; no sustituyen
> los `SCRUM-27` a `SCRUM-32` (Sprint 3), que siguen siendo el acabado visual de
> las pantallas que ya funcionan.
>
> **Reconciliación con el tablero (2026-09-30).** Al consultar Jira por el MCP se
> comprobó que el tablero **no** contiene los tickets que este archivo inventó
> desde `SCRUM-57`: su key más alto es **`SCRUM-66`**, y `SCRUM-57` a `SCRUM-66`
> son **tickets de área** (`DatenJäger — Backend`, `— Frontend`, `— UI / UX`,
> `— Electron`, `— Chatbot`, `— API / Servicios`, `— Búsqueda semántica`,
> `— Testing / QA`, `— Documentación / Release`, `— Arquitectura / Core`). Hasta
> `SCRUM-56` el archivo y el tablero coinciden (por ejemplo `SCRUM-55`
> «Preparar evidencia de pruebas y demostración» y `SCRUM-56` «Cerrar backlog
> técnico del semestre»).
>
> Por eso, **a partir de aquí el trabajo se etiqueta con el ticket de área** que
> le corresponde, no con una numeración paralela que no existe en Jira. El mapeo
> histórico deja constancia de qué significaban los números antiguos para que los
> commits ya publicados sigan siendo trazables.

## Tickets del tablero (áreas)

| Jira | Área en el tablero | Estado |
|---|---|---|
| `SCRUM-57` | DatenJäger — Backend | trabajo hecho (alta de usuario, estado de la base, conexión de modelos) |
| `SCRUM-58` | DatenJäger — Frontend | trabajo hecho (registro, asistente, reportes, estadísticas, modelos, ajustes) |
| `SCRUM-59` | DatenJäger — UI / UX | trabajo hecho (identidad visual, movimiento, visor, ajustes) |
| `SCRUM-60` | DatenJäger — Electron | trabajo hecho (arranque en otro puerto, CORS de desarrollo, motivo del fallo) |
| `SCRUM-61` | DatenJäger — Chatbot | trabajo hecho (panel con barra lateral por botones) |
| `SCRUM-62` | DatenJäger — API / Servicios | trabajo hecho (rutas de reportes y de conexión de modelos) |
| `SCRUM-63` | DatenJäger — Búsqueda semántica | sin trabajo: es la Fase 5, en evaluación |
| `SCRUM-64` | DatenJäger — Testing / QA | trabajo hecho (142 pruebas, sondas de la ventana real) |
| `SCRUM-65` | DatenJäger — Documentación / Release | trabajo hecho (planning, jira, CLAUDE, docs/issues) |
| `SCRUM-66` | DatenJäger — Arquitectura / Core | trabajo hecho (capa de comandos, AppState, puente) |

## Mapeo histórico (numeración antigua → área)

| Numeración antigua de este archivo | Área del tablero |
|---|---|
| `SCRUM-57` a `SCRUM-62` (pantallas que faltan) | `SCRUM-58` (Frontend) y `SCRUM-57` (Backend) |
| `SCRUM-63` (ajustes), `SCRUM-71` (complementos) | `SCRUM-59` (UI / UX) |
| `SCRUM-65` a `SCRUM-70` (identidad y movimiento) | `SCRUM-59` (UI / UX) |
| `SCRUM-64` (conexión de modelos) y sus rutas | `SCRUM-62` (API / Servicios) y `SCRUM-58` |
| `SCRUM-72` a `SCRUM-74` (clasificación automática) | sin ticket: es la Fase 6, en evaluación |
| `SCRUM-75` a `SCRUM-78` (empaquetado) | `SCRUM-65` (Documentación / Release) |
| `SCRUM-79` a `SCRUM-83` (diseño, datos y reportes) | `SCRUM-59` (UI / UX) y `SCRUM-58` (Frontend) |
| `SCRUM-84` a `SCRUM-88` (cierre de la Fase 3) | `SCRUM-58` / `SCRUM-59` |
| `SCRUM-89` (hallazgo de `docs/issues.md`) | `SCRUM-64` (Testing / QA) y `SCRUM-60` (Electron) |

> `SCRUM-89` **no existe en el tablero**: se acuñó en este archivo para el hallazgo
> de `docs/issues.md`. Si Raven quiere que sea un ticket real, hay que crearlo; el
> trabajo que representa ya está hecho y verificado.

## Calidad de vida y diseño (2026-10-01)

Sección nueva, pedida por Raven sobre la aplicación ya funcional y antes de abrir
la Fase 4. Se etiqueta con las **áreas del tablero**, no con números inventados:

| Área del tablero | Trabajo |
|---|---|
| `SCRUM-57` (Backend) | catálogo de empresas (`Empresas` + `personas.empresa_id`), normalización y migración del texto libre; corrección del alta/edición de titular en documentos |
| `SCRUM-58` (Frontend) | panel de Personas agrupado por empresa; formulario de alta de documento con sus metadatos |
| `SCRUM-59` (UI / UX) | animaciones del portal, fondo de marca compartido, «Términos y uso», Ajustes al pie con auditoría y modelos, asistente flotante, tuerca de acceso rápido, logo como control de la barra, franja de telemetría con estado en texto |
| `SCRUM-61` (Chatbot) | acceso flotante al asistente desde cualquier sección |
| `SCRUM-62` (API / Servicios) | rutas de empresas; credencial de la API escrita en el `.env` y prueba real de conexión |
| `SCRUM-64` (Testing / QA) | 178 pruebas, con cobertura nueva de empresas, normalización, migración y modelos |
| `SCRUM-65` (Documentación / Release) | `planning.md`, este archivo y `CLAUDE.md` al día |

**Commits esperados de la sección** (los ya publicados siguen siendo trazables por
la tabla de mapeo de arriba):

```text
feat(SCRUM-62): escribe la credencial de la API en el .env y anade la prueba real de conexion
test(SCRUM-64): cubre el .env, la clave vigente y la prueba de conexion
ui(SCRUM-59): escribe el estado real en la franja de telemetria
fix(SCRUM-57): vincula la persona correcta al editar el titular de un documento
feat(SCRUM-57): catalogo de empresas para no duplicar y asociar el personal
feat(SCRUM-58): agrupa el personal por empresa y sugiere el catalogo al registrar
```

### Orden acordado para lo que queda (2026-10-01)

1. `SCRUM-81` estadística al backend · `SCRUM-82` dashboard de gráficos
2. `SCRUM-84` **restablecer contraseña** (el más vital; autorizado en `CLAUDE.md`,
   con `senior-security` antes de tocar el flujo)
3. `SCRUM-87` notificaciones · `SCRUM-88` modales de documento
4. `SCRUM-85` atajos de teclado y búsqueda global (el último, el más simple)
5. Fase 4 **solo API**: streaming, errores de red, decisión de motor y asistente
   anclado al proyecto

## Bloque A — Pantallas que faltan

**Estado: cerrado (2026-09-30) — hecho y verificado: 142 pruebas, `vite build`
correcto y las nueve secciones conducidas en la ventana real de Electron.**

| Área | Tarea | Etiquetas adicionales | Estado |
|---|---|---|---|
| `SCRUM-57` | Alta de usuario en el backend (`registrar_usuario`) | `registro`, `auth`, `feat` | hecho |
| `SCRUM-58` | Registro de operadores, panel del asistente, reportes, estadísticas, conexión de modelos y ajustes | `ui`, `feat` | hecho |
| `SCRUM-59` | Alta de 2FA con QR y códigos de respaldo; visor de PDF dentro de la aplicación | `ui`, `2fa`, `pdf`, `feat` | hecho |
| `SCRUM-61` | Panel del chatbot con barra lateral por botones | `chatbot`, `ui`, `feat` | hecho |
| `SCRUM-62` | Rutas de reportes (`por-empresa`, `por-dia`) y de conexión de modelos | `api`, `datos`, `feat` | hecho |
| `SCRUM-64` | Cerrar el hallazgo de `docs/issues.md` (dashboard en blanco, base caída, puerto ocupado, CORS en desarrollo) | `diagnostico`, `bug` | hecho |

> El hallazgo se acuñó aquí como `SCRUM-89` (en el tablero corresponde a
> `SCRUM-64`): «conexión a base de datos fallida; electron y web caen; no se puede
> acceder al dashboard mediante login y register». El síntoma tenía **cinco**
> causas superpuestas:
>
> 1. el alta de usuario no existía en el frontend (`SCRUM-57`);
> 2. una base caída se veía como un servicio sano (`GET /api/salud` no la
>    comprobaba) — la salud informa ahora del estado real, el arranque anuncia
>    `DATENJAGER_ERROR base de datos: …` y Electron muestra ese mensaje;
> 3. **la causa directa del síntoma**: `src/App.jsx` usaba `<Icono>` en la
>    sub-cabecera sin importarlo, así que el shell autenticado lanzaba
>    `ReferenceError: Icono is not defined` y React dejaba la ventana **en
>    blanco justo después de entrar**. Era un defecto previo (ya en `42eeaa8`) e
>    invisible para `vite build`, que compila igual un identificador sin
>    definir.
>
> 4. un **puerto 8756 ocupado** por una instancia anterior dejaba la app sin
>    servicio (`electron/backend.js` prueba ahora 8756, 8757, 8758, 8759 y por
>    último el que elija el sistema) y el motivo no se pintaba en ninguna
>    pantalla: Bienvenida y Acceso muestran ahora el error real;
> 5. **`npm run dev` no conectaba** porque en desarrollo el renderer se sirve
>    desde el servidor de Vite y su origen deja de ser `file://`: el navegador
>    bloqueaba las llamadas al servicio por CORS. Se habilita solo para esos
>    orígenes y solo en desarrollo (`DATENJAGER_CORS_ORIGENES`), nunca en
>    producción.
>
> No estaba contemplado en este archivo ni en `planning.md`; queda consolidado
> aquí y en la Fase 3 de `planning.md`.

## Bloque B — Identidad visual y movimiento

**Área del tablero: `SCRUM-59` (UI / UX).**

| Tarea | Etiquetas adicionales | Estado |
|---|---|---|
| Integrar logo, icono de aplicación y set de iconos de acción | `branding`, `assets`, `ui` | hecho |
| Animar el cambio entre tema claro y oscuro | `ui`, `tema`, `animacion` | hecho |
| Añadir animación de entrada y micro-interacciones | `ui`, `animacion`, `feat` | hecho |
| Indicar con color el estado de base de datos, APIs y chatbot | `ui`, `estados`, `feat` | hecho |
| Añadir esqueletos de carga en las listas | `ui`, `ui-states`, `feat` | hecho |
| Permitir desplegar y recoger las barras laterales | `ui`, `layout`, `feat` | hecho |
| Incorporar los complementos de `assets/assets/` como componentes | `ui`, `componentes`, `feat` | hecho |

## Bloque C — Clasificación automática de documentos (evaluación)

**Sin ticket en el tablero: es la Fase 6 y sigue en evaluación.** No se creó
ningún `SCRUM-72` a `SCRUM-74`.

| Tarea | Etiquetas adicionales |
|---|---|
| Etiquetar el corpus y medir la línea base sin modelo | `ml`, `evaluacion`, `poc` |
| Prototipar la clasificación con embeddings | `ml`, `embeddings`, `evaluacion` |
| Medir resultados y decidir continuidad | `ml`, `evaluacion`, `decision` |

## Bloque D — Diseño, datos y cierre de la Fase 3

> Registrado el 2026-09-30 tras revisar `/assets/mockups` completo con Raven.
> Los mockups son **referencias** (estructura inspirada en Hermes Desktop), el
> sistema de diseño está en `DESIGN.md` y la lógica de datos vive en Python.
> **Sin duplicados**: lo que ya está en los bloques A y B no se repite aquí
> (visor de PDF, chatbot, ajustes y panel de conexión ya están en el Bloque A).

**Área del tablero: `SCRUM-59` (UI / UX), con el backend en `SCRUM-57`.**

| Área | Tarea | Etiquetas adicionales | Estado |
|---|---|---|---|
| `SCRUM-59` | Versionar el material de diseño y de marca | `assets`, `documentacion`, `hito` | hecho |
| `SCRUM-59` | Definir e integrar el set de iconos del frontend | `ui`, `iconos`, `rendimiento` | hecho (set SVG en línea de `Icono.jsx`) |
| `SCRUM-57` | Extraer la estadística y los gráficos al backend | `backend`, `estadistica`, `refactor` | hecho (`3598f95`: `reportes.tendencia()` con regresión, predicción y R², más `PALETA_GRAFICOS` por rol semántico y `GET /api/reportes/tendencia`) |
| `SCRUM-59` | Construir el dashboard de gráficos | `ui`, `dashboard`, `feat` | hecho (`cf6d7a3`: `Graficos.jsx` con medidor, anillo y tendencia en SVG) |
| `SCRUM-59` | Generar los reportes con la paleta del sistema | `reportes`, `pdf`, `feat` | hecho (PR #12: logo, tarjetas y exportador) |
| `SCRUM-57` | Implementar el restablecimiento de contraseña | `auth`, `backend`, `feat` | hecho (`b035737`: códigos de respaldo en hash de un solo sentido, dos pasos sin sesión y reinicio del segundo factor) |
| `SCRUM-59` | Implementar atajos de teclado y búsqueda global | `ui`, `atajos`, `feat` | hecho (`dc0511a`: `Ctrl+B`, `Ctrl+F`, `Ctrl+N`, `Ctrl+Q`, `Supr`, `F11`, `Enter`, `Esc`) |
| `SCRUM-59` | Construir la franja de telemetría inferior | `ui`, `telemetria`, `feat` | hecho (`BarraEstado` con estados reales) |
| `SCRUM-59` | Implementar las notificaciones del sistema | `ui`, `notificaciones`, `feat` | hecho (`bbe44a8`: pila de avisos en el proveedor, silenciables desde Ajustes) |
| `SCRUM-59` | Migrar los modales de documento al diseño nuevo | `ui`, `documentos`, `feat` | hecho (`bbe44a8`: `ModalDocumento.jsx` con detalles y edición) |

### Commits esperados (Bloque D)

```text
chore(SCRUM-59): versiona el material de diseño
ui(SCRUM-59): integra el set de iconos
refactor(SCRUM-57): extrae la estadística al backend
feat(SCRUM-59): construye el dashboard de gráficos
feat(SCRUM-59): genera los reportes del sistema
feat(SCRUM-57): habilita el restablecimiento de contraseña
feat(SCRUM-59): añade atajos de teclado
ui(SCRUM-59): construye la franja de telemetría
feat(SCRUM-59): añade las notificaciones del sistema
feat(SCRUM-59): migra los modales de documento
```

### Notas del Bloque D

* Versionar el material de diseño y de marca **cerrado** (`ee40d51` incorpora el
  material, `19a6cde` retira las 24 copias antiguas tras comprobar que eran
  idénticas). No era opcional: los mockups estaban sin versionar mientras las
  copias anteriores figuraban como borradas.
* Set de iconos: los mockups usan la fuente de iconos *Material Symbols*; el
  proyecto tiene 44 PNG estilo lucide y Raven delegó la elección en el criterio
  de **rendimiento y estética**. Quedó resuelto con el set SVG en línea de
  `Icono.jsx`, que ya cubre los nombres que el sistema pide (incluidos
  `flecha-derecha` y `basura`, que faltaban).
* Extraer la estadística al backend: hoy la regresión lineal, la predicción y
  **los colores de los gráficos** están dentro de `ui_components.py`
  (`DashboardWidget`). Las métricas y las series ya viven en
  `backend/services/reportes.py`; falta subir el resto para que el frontend
  dibuje con la paleta del sistema.
* Reportes con la paleta del sistema: el reporte PDF conserva portada,
  inventario y gráfico por empresa. El PR #12 añade el logo en la portada y
  formaliza la exportación (`scripts/exportar_inventario.py`), y corrige los
  glifos que las fuentes base del PDF no podían dibujar (salían como `?`).
* Restablecer contraseña: el flujo del Python **no puede completarse** para
  usuarios nuevos (`paneles_datenjager.md` lo documenta); la verificación de
  códigos de respaldo ya vive en `backend/services/autenticacion.py`, así que se
  construye sobre esa base.
* Atajos y franja de telemetría: los atajos (`Ctrl+F`, `Ctrl+N`, `Ctrl+Q`,
  `Supr`, `F11`) están documentados en `paneles_datenjager.md` §4.7, pero **no
  existen** en el frontend nuevo (sí `Ctrl+B`, `Enter` y `Esc`). La franja sí
  existe y muestra estados reales (`BarraEstado`), contra lo que decía la nota
  original de §4.6.
* Modales de documento: agregar, detalles y editar documento; el **visor** ya
  está hecho en el Bloque A.
* Recordatorio de alcance: **nada de modelos locales** hasta que el frontend y
  el backend estén completos (decisión de Raven del 2026-09-30).

## Bloque E — Empaquetado y publicación

**Área del tablero: `SCRUM-65` (Documentación / Release).**

| Tarea | Etiquetas adicionales |
|---|---|
| Generar el instalador multiplataforma (Windows y Linux) | `release`, `electron`, `build` |
| Publicar el paquete en GitHub Packages | `release`, `paquetes`, `build` |
| Documentar instalación y arranque para alguien nuevo | `documentacion`, `release` |
| Retirar la interfaz CustomTkinter | `limpieza`, `hito`, `refactor` |

### Commits esperados

```text
feat(SCRUM-57): habilita el registro de operadores en el backend
feat(SCRUM-58): construye el registro de operadores
feat(SCRUM-59): construye el alta de 2FA con QR y códigos de respaldo
feat(SCRUM-61): construye el panel del chatbot
feat(SCRUM-59): incorpora el visor de PDF
feat(SCRUM-58): construye el panel de reportes
feat(SCRUM-62): agrega estadísticas del sistema
improvement(SCRUM-58): completa el panel de ajustes
feat(SCRUM-62): crea la conexión de modelos
bug(SCRUM-64): distingue la base caída del servicio vivo
fix(SCRUM-64): importa el icono que dejaba el dashboard en blanco
fix(SCRUM-60): arranca en otro puerto si el 8756 está ocupado
fix(SCRUM-60): habilita CORS del origen del servidor de Vite en desarrollo
ui(SCRUM-59): integra el logo y los iconos
ui(SCRUM-59): anima el cambio de tema
feat(SCRUM-59): añade la animación de entrada
ui(SCRUM-59): indica el estado de las conexiones
feat(SCRUM-59): añade esqueletos de carga
feat(SCRUM-59): permite desplegar las barras laterales
feat(SCRUM-59): incorpora los complementos visuales
chore(SCRUM-59): versiona el material de diseño y de marca
feat(SCRUM-59): formaliza la exportación del inventario con el logo
feat(clasificacion): prepara el corpus de clasificación
feat(clasificacion): prototipo de clasificación
docs(clasificacion): registra la decisión de clasificación
build(SCRUM-65): genera el instalador multiplataforma
build(SCRUM-65): publica el paquete en GitHub Packages
docs(SCRUM-65): documenta la instalación
refactor(SCRUM-65): retira la interfaz antigua
```

### Notas de alcance

* `SCRUM-57` (Backend) cerró el último trabajo que devolvía
  `ComandosDatenJager.operaciones_pendientes()`: el backend validaba credenciales,
  2FA y contraseña, pero el **alta** de una cuenta vivía en `main.py`. Hoy la
  hace `backend/services/autenticacion.py` (`registrar_usuario`).
* `SCRUM-26` (instalador inicial) y `SCRUM-54` cubren lo mismo que el empaquetado
  pendiente: el 26 era el instalador mínimo de la Fase 2 y quedó **en pausa**; el
  trabajo de `SCRUM-65` (Documentación / Release) lo retoma cuando el frontend
  esté cerrado.
* Los complementos de `assets/assets/` se incorporan como componentes propios con
  la estética del proyecto, **no** tal cual vienen: botón biométrico, sistema de
  partículas, conmutador de notificaciones, cajón desplazable y formulario suave.
* Los assets que use la aplicación (logo, icono, iconos de acción) deben quedar
  versionados antes de que el empaquetado dependa de ellos.
* Retirar la interfaz CustomTkinter solo se puede cerrar cuando la Fase 3 haya
  migrado **todas** las pantallas: hasta entonces se mantiene funcionando.

---

# Reglas para el agente

## 1. No inventar tareas

El agente debe trabajar sobre una tarea `SCRUM-#` existente.

Si durante la implementación aparece una necesidad que no pertenece claramente a la tarea actual:

1. No introducir cambios grandes fuera de alcance.
2. Registrar la necesidad.
3. Proponer una nueva tarea Jira.
4. Continuar únicamente si el cambio es necesario para completar la tarea actual.

## 2. Un commit = una unidad verificable

Siempre que sea posible:

```text
SCRUM-12 → cambio → prueba → commit
SCRUM-13 → cambio → prueba → commit
SCRUM-14 → cambio → prueba → commit
```

Evitar:

```text
SCRUM-12 + SCRUM-13 + SCRUM-14 → un único commit
```

salvo que exista una dependencia técnica que haga imposible separarlos.

## 3. Commits cortos

Preferir:

```text
feat(SCRUM-23): migra panel documental
```

Evitar:

```text
feat(SCRUM-23): se implementa toda la funcionalidad del nuevo panel documental con integración completa, manejo de errores, estilos y mejoras varias
```

## 4. No mencionar al agente

Los commits nunca deben contener:

- nombre del agente;
- "AI";
- "IA";
- "Claude";
- "ChatGPT";
- "Rovo";
- "generado por...";
- "implementado por el agente".

El historial debe describir **el cambio técnico**, no quién lo realizó.

## 5. No saltar fases

El orden general es:

```text
S1 Diagnóstico
   ↓
S2 Backend + Andamiaje
   ↓
S3 Frontend + UI
   ↓
S4 APIs + Modelos + Cierre
```

No avanzar automáticamente a una fase posterior si la fase anterior todavía está en `en progreso`, salvo autorización explícita.

## 6. Evaluaciones no son compromisos

Las tareas marcadas con:

```text
evaluacion
poc
decision
```

deben producir evidencia y una decisión documentada.

No convertir automáticamente una evaluación en una implementación definitiva.

## 7. Búsqueda semántica

La búsqueda semántica es experimental.

El flujo esperado es:

```text
extracción
→ fragmentación
→ embeddings
→ almacenamiento vectorial
→ integración con búsqueda léxica
→ evaluación
→ decisión
```

No eliminar la búsqueda léxica existente para introducir la semántica.

## 8. Refactorización

Los cambios de arquitectura deben ser incrementales.

Preferir:

```text
refactor(SCRUM-12): separa CRUD de documentos
```

antes que una reescritura completa del sistema.

Cada modificación debe poder verificarse antes de continuar con la siguiente.

---

# Formato recomendado para el historial

Un historial limpio debería verse aproximadamente así:

```text
docs(SCRUM-6): actualiza documentación base
refactor(SCRUM-12): separa CRUD de documentos
test(SCRUM-18): valida backend sin Tkinter
feat(SCRUM-20): crea andamiaje Electron
feat(SCRUM-21): conecta bridge Python Electron
feat(SCRUM-23): migra panel documental
ui(SCRUM-28): crea layout base
feat(SCRUM-34): implementa streaming del chatbot
test(SCRUM-50): valida flujo end-to-end
docs(SCRUM-52): actualiza arquitectura final
build(SCRUM-54): prepara instalador final
docs(SCRUM-56): cierra backlog técnico
```

El identificador `SCRUM-#` es obligatorio en cada commit relacionado con una tarea Jira.
