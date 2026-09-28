# jira.md — Guía de trabajo Jira y commits

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
./venv/bin/python -m unittest discover -s tests -t .     # 121 pruebas, sin Tkinter
npx vite build                                            # el frontend compila
./node_modules/.bin/electron . --no-sandbox              # arranca el sistema completo
```

La autenticación ya **no** vive en `main.py`: está en
`backend/services/autenticacion.py` y se expone por el puente (`POST /api/sesion`,
`/api/sesion/2fa`, `/api/sesion/respaldo`, `GET /api/cuenta` y `/api/cuenta/...`).
Los tokens de confianza ya **no** están en claro en `config.json`: viven cifrados
en `tokens_confianza/` (ignorado por git). Lo único pendiente dentro del desacople
es el **alta de usuario**: `ComandosDatenJager.operaciones_pendientes()` devuelve
solo `registro`.

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
> **movimiento e identidad visual** están en el Sprint 5 (`SCRUM-57` a
> `SCRUM-71`), no aquí.

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

## Bloque B — APIs y backend

| Jira | Tarea | Etiquetas adicionales |
|---|---|---|
| `SCRUM-40` | Definir API local del backend | `api`, `backend`, `arquitectura` |
| `SCRUM-41` | Integrar autenticación y 2FA mediante API | `api`, `auth`, `feat` |
| `SCRUM-42` | Integrar documentos, personas y auditoría mediante API | `api`, `integracion`, `feat` |
| `SCRUM-43` | Evaluar persistencia de modelos y datos | `persistencia`, `evaluacion` |

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
> las pantallas que ya funcionan. Los `SCRUM-57` en adelante son tareas nuevas
> registradas el 2026-09-28 a partir de la revisión de Raven.

## Bloque A — Pantallas que faltan

| Jira | Tarea | Etiquetas adicionales |
|---|---|---|
| `SCRUM-57` | Implementar registro de operadores (alta de usuario) | `registro`, `auth`, `feat` |
| `SCRUM-58` | Construir el alta de 2FA con QR y códigos de respaldo | `ui`, `2fa`, `feat` |
| `SCRUM-59` | Construir el panel del chatbot con barra lateral por botones | `chatbot`, `ui`, `feat` |
| `SCRUM-60` | Incorporar visor de PDF dentro de la aplicación | `pdf`, `visor`, `feat` |
| `SCRUM-61` | Construir el panel de reportes con paleta estructurada | `reportes`, `ui`, `feat` |
| `SCRUM-62` | Agregar recopilador de datos y estadísticas | `datos`, `estadisticas`, `feat` |
| `SCRUM-63` | Completar el panel de ajustes (paridad con el código Python) | `configuracion`, `ui`, `improvement` |
| `SCRUM-64` | Crear el panel de conexión de APIs y modelos | `modelos`, `api`, `feat` |

## Bloque B — Identidad visual y movimiento

| Jira | Tarea | Etiquetas adicionales |
|---|---|---|
| `SCRUM-65` | Integrar logo, icono de aplicación y set de iconos de acción | `branding`, `assets`, `ui` |
| `SCRUM-66` | Animar el cambio entre tema claro y oscuro | `ui`, `tema`, `animacion` |
| `SCRUM-67` | Añadir animación de entrada y micro-interacciones | `ui`, `animacion`, `feat` |
| `SCRUM-68` | Indicar con color el estado de base de datos, APIs y chatbot | `ui`, `estados`, `feat` |
| `SCRUM-69` | Añadir esqueletos de carga en las listas | `ui`, `ui-states`, `feat` |
| `SCRUM-70` | Permitir desplegar y recoger las barras laterales | `ui`, `layout`, `feat` |
| `SCRUM-71` | Incorporar los complementos de `assets/assets/` como componentes | `ui`, `componentes`, `feat` |

## Bloque C — Clasificación automática de documentos (evaluación)

| Jira | Tarea | Etiquetas adicionales |
|---|---|---|
| `SCRUM-72` | Etiquetar el corpus y medir la línea base sin modelo | `ml`, `evaluacion`, `poc` |
| `SCRUM-73` | Prototipar la clasificación con embeddings | `ml`, `embeddings`, `evaluacion` |
| `SCRUM-74` | Medir resultados y decidir continuidad | `ml`, `evaluacion`, `decision` |

## Bloque D — Empaquetado y publicación

| Jira | Tarea | Etiquetas adicionales |
|---|---|---|
| `SCRUM-75` | Generar el instalador multiplataforma (Windows y Linux) | `release`, `electron`, `build` |
| `SCRUM-76` | Publicar el paquete en GitHub Packages | `release`, `paquetes`, `build` |
| `SCRUM-77` | Documentar instalación y arranque para alguien nuevo | `documentacion`, `release` |
| `SCRUM-78` | Retirar la interfaz CustomTkinter | `limpieza`, `hito`, `refactor` |

### Commits esperados

```text
feat(SCRUM-57): habilita el registro de operadores
feat(SCRUM-58): construye el alta de 2FA
feat(SCRUM-59): construye el panel del chatbot
feat(SCRUM-60): incorpora el visor de PDF
feat(SCRUM-61): construye el panel de reportes
feat(SCRUM-62): agrega estadísticas del sistema
improvement(SCRUM-63): completa el panel de ajustes
feat(SCRUM-64): crea el panel de conexión de modelos
ui(SCRUM-65): integra el logo y los iconos
ui(SCRUM-66): anima el cambio de tema
feat(SCRUM-67): añade la animación de entrada
feat(SCRUM-68): indica el estado de las conexiones
feat(SCRUM-69): añade esqueletos de carga
feat(SCRUM-70): permite desplegar las barras laterales
feat(SCRUM-71): incorpora los complementos visuales
feat(SCRUM-72): prepara el corpus de clasificación
feat(SCRUM-73): prototipo de clasificación
docs(SCRUM-74): registra la decisión de clasificación
build(SCRUM-75): genera el instalador multiplataforma
build(SCRUM-76): publica el paquete en GitHub Packages
docs(SCRUM-77): documenta la instalación
refactor(SCRUM-78): retira la interfaz antigua
```

### Notas de alcance

* `SCRUM-57` es el único trabajo que hoy devuelve
  `ComandosDatenJager.operaciones_pendientes()`: el backend valida credenciales,
  2FA y contraseña, pero el **alta** de una cuenta todavía vive en `main.py`.
* `SCRUM-26` (instalador inicial) y `SCRUM-54`/`SCRUM-75` cubren lo mismo: el 26
  era el instalador mínimo de la Fase 2 y quedó **en pausa**; el 75 lo retoma
  cuando el frontend esté cerrado y el 76 añade la publicación.
* `SCRUM-71` incorpora los complementos de `assets/assets/` como componentes
  propios con la estética del proyecto, **no** tal cual vienen: botón biométrico,
  sistema de partículas, conmutador de notificaciones, cajón desplazable y
  formulario suave.
* Los assets que use la aplicación (logo, icono, iconos de acción) deben quedar
  versionados antes de que el empaquetado dependa de ellos.
* `SCRUM-78` solo se puede cerrar cuando la Fase 3 haya migrado **todas** las
  pantallas: hasta entonces CustomTkinter se mantiene funcionando.

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
