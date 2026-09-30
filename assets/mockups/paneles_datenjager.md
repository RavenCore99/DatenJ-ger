# DatenJäger — Mapa de paneles y secciones

> Derivado de la lectura de `main.py`, `ui_components.py`, `pdf_manager.py`, `personas.py`, `audit.py`, `chatbot_ui.py`, `chatbot.py`, `reporter.py`, `database.py`, `config.py`, `encryption.py`, `icons.py` y `transhumano.py`.
> Sirve como inventario base para la Fase 1 (estados canónicos) y la Fase 4/5 (enrutador de pantallas y migración a React) de `planning.md`.

---

#revisar carpetas tema claro y tema oscuro para tener referencias del diseño#

## 1. Vista general de navegación

```
Intro ──(tecla/clic)──▶ Inicial ──┬─▶ Login ──┬─▶ Verificación 2FA ──▶ PANEL PRINCIPAL
                                  │           ├─(sin 2FA / token de confianza)─▶ PANEL PRINCIPAL
                                  │           └─▶ [Modal] Restablecer contraseña
                                  └─▶ Registro ─▶ Setup 2FA ─▶ [Modal] Códigos de respaldo ─▶ Login

PANEL PRINCIPAL ──┬─▶ [Modal] Asistente IA
                  ├─▶ [Notificación] Acerca de
                  ├─▶ [Diálogo guardar] Reporte PDF
                  ├─▶ [Modal] Personas
                  ├─▶ [Modal] Auditoría ─▶ [Modal] Log del Sistema
                  ├─▶ [Modal] Mi Cuenta (Contraseña · Códigos 2FA · Confianza)
                  ├─▶ Alternar tema Claro/Oscuro
                  ├─▶ Cerrar Sesión ─▶ Inicial
                  └─▶ Acciones de PDF (Agregar · Detalles · Editar · Exportar · Eliminar · Visor)
```

**Tipos de pantalla**

| Tipo | Pantallas |
| --- | --- |
| Frames a pantalla completa (`frame_*`) | Intro, Inicial, Login, 2FA, Registro, Setup 2FA, Principal |
| Ventanas modales (`CTkToplevel`) | Restablecer contraseña, Códigos de respaldo, Agregar PDF, Detalles PDF, Editar PDF, Visor PDF, Personas (+ formulario), Auditoría (+ Log del sistema), Mi Cuenta, Asistente IA (+ Reflexión) |
| Diálogos / avisos | `ConfirmDialog`, `Notification` (toast), `askstring` (código de respaldo), diálogos de archivo |

Transición entre frames: `_fade_to()` (overlay oscuro de ~100 ms + 80 ms).

---

## 2. Pantallas de acceso (antes de iniciar sesión)

### 2.1 Intro (`frame_intro`)
- Fondo animado `CosmicBackground` (siempre oscuro).
- Tarjeta central con texto *typewriter* que rota frases: "DatenJäger", "Seguridad Inquebrantable", "Gestión Inteligente", "Tus Documentos, Protegidos", "Cifrado AES-256", "Privacidad Sin Compromiso".
- Subtítulo "Sistema de Gestión Documental Seguro", línea técnica "AES-256-GCM · 2FA · PBKDF2" y hint pulsante.
- **Navegación:** cualquier tecla o clic → Inicial.

### 2.2 Inicial (`frame_inicial`)
- Logo + "Seguridad · Privacidad · Control".
- **Botones:**
  - `Iniciar Sesión` → Login
  - `Crear Usuario` → Registro
- Pie con versión "v.2.0 – AES-256-GCM + PBKDF2 + 2FA".

### 2.3 Login (`frame_login`)
- Campos: **Usuario**, **Contraseña** (con botón ojo para mostrar/ocultar).
- **Botones:**
  - `Siguiente` → valida credenciales
  - `Volver` → Inicial
  - `¿Olvidaste tu contraseña?` → modal Restablecer contraseña (**oculto hasta 3 intentos fallidos**)
- **Comportamiento asociado:**
  - Bloqueo de cuenta: 5 intentos fallidos → 15 min.
  - Efecto *shake* en campos al fallar.
  - Migración automática de hash SHA-256 → PBKDF2.
  - Si el usuario tiene 2FA → pantalla 2FA; si hay **token de confianza** vigente → entra directo al Panel Principal; si no tiene 2FA → entra directo.

### 2.4 Verificación 2FA (`frame_2fa`)
- Campo de código de 6 dígitos.
- Anillo de cuenta regresiva TOTP (30 s, cambia de color: verde → naranja → rojo).
- **Botones:**
  - `Verificar` → Panel Principal
  - `Código de Respaldo` → diálogo `askstring` para código de respaldo
  - `Volver` → Login

### 2.5 Registro (`frame_registro`)
- Campos: **Nombre de usuario**, **Contraseña** (con ojo) + barra de fortaleza (`PasswordStrengthBar`).
- Validaciones: usuario ≥ 3 caracteres, contraseña ≥ 8, fortaleza mínima "Regular".
- **Botones:**
  - `Registrar` → Setup 2FA
  - `Volver` → Inicial

### 2.6 Configurar 2FA (`frame_setup_2fa`, scrollable)
- Pasos guiados: (1) abrir app autenticadora, (2) escanear QR, (3) ingresar código.
- Código QR + clave secreta en texto.
- **Botones:**
  - `Copiar` (clave secreta)
  - `Confirmar y Activar 2FA` → genera 5 códigos de respaldo → modal Códigos de respaldo → Login

---

## 3. Modales de acceso

### 3.1 Restablecer contraseña (`_abrir_reset_password`)
Asistente de pasos dentro de una sola ventana:
1. **Usuario** (`Siguiente`) — exige que el usuario tenga 2FA activo.
2. **Código 2FA** (`Verificar`) — si el secreto está cifrado (caso normal), deriva al paso 2b.
   - **2b. Código de respaldo** (`Verificar Código`).
3. **Nueva contraseña** + confirmación + barra de fortaleza (`Guardar Nueva Contraseña`).

### 3.2 Códigos de respaldo (`_mostrar_codigos_respaldo`)
- Lista de los 5 códigos generados.
- **Botones:** `Copiar todos`, `Entendido`.

---

## 4. Panel Principal (`frame_principal`)

Estructura vertical, de arriba abajo:

`Navbar → Barra de progreso → Dashboard → Toolbar (búsqueda + acciones) → Área de contenido → Barra de estado`

### 4.1 Navbar
Elementos a la izquierda: logo "DatenJäger" y **badge del usuario** activo.

Botones a la derecha (de izquierda a derecha en pantalla):

| Botón | Destino / acción |
| --- | --- |
| `Asistente IA` | Abre modal **Asistente IA** (§6) |
| `Acerca de` | Notificación con versión y tecnologías (no es panel) |
| `Reporte` | Diálogo "guardar como" → genera **reporte PDF** (§7) |
| `Personas` | Modal **Gestión de Personas** (§5.3) |
| `Auditoría` | Modal **Log de Auditoría** (§5.4) |
| `Mi Cuenta` | Modal **Configuración de Cuenta** (§5.5) |
| `Claro` / `Oscuro` | Alterna el tema y persiste en `config.json` |
| `Cerrar Sesión` | `ConfirmDialog` → Inicial |

### 4.2 Barra de progreso
`ProgressBarModerno` (indeterminada). Solo aparece durante operaciones (cifrar, descifrar, cargar, exportar, generar reporte).

### 4.3 Dashboard (`DashboardWidget`)
Título "ESTADÍSTICAS DEL REPOSITORIO". Es **solo informativo: no contiene botones ni redirecciones**.

| Sección | Contenido |
| --- | --- |
| Gauges (4) | PDFs totales, Espacio usado, Personas, Empresas |
| Tarjeta AES-256 GCM | Indicador decorativo de cifrado |
| Donut | Documentos por empresa (top 6) |
| Gráfico temporal | Subidas por día + línea de tendencia (regresión lineal), predicción del siguiente día y R² |

Se regenera con `cargar_dashboard()` al iniciar sesión, agregar o eliminar un PDF y al cambiar el tema.

### 4.4 Toolbar

**Búsqueda:** campo "Buscar PDF, cédula, persona…" + botón `Buscar`. Búsqueda automática con *debounce* de 400 ms. Filtra por nombre, descripción, cédula, nombres y empresa.

**Botones de acción sobre PDFs:**

| Botón | Destino |
| --- | --- |
| `Agregar` | Modal **Agregar PDF** (§5.1) |
| `Ver Todos` | Recarga la lista completa |
| `Detalles` | Modal **Detalles del PDF** (§5.2) |
| `Editar` | Modal **Editar Metadatos** (§5.2) |
| `Exportar` | Diálogo guardar → descifra y escribe el PDF |
| `Eliminar` | `ConfirmDialog` → borra el PDF |
| `Mosaico` / `Lista` | Alterna la vista del área de contenido |

### 4.5 Área de contenido
Tres bloques que conviven; la vista central alterna entre lista y mosaico.

**a) Vista Lista (`Treeview`)**
- Columnas: ID, Nombre, Descripción, Tamaño, Fecha, Cédula, Nombres, Empresa (ordenables por clic en el encabezado).
- Doble clic → abre el **Visor PDF**.
- Clic derecho → **menú contextual**: Abrir / Desencriptar · Ver Detalles · Editar Metadatos · Exportar PDF · *(separador)* · Eliminar.

**b) Vista Mosaico (`_mosaic_frame`)**
- Tarjetas en cuadrícula de 4 columnas con color, ícono, nombre, persona, empresa, tamaño y fecha.
- Clic selecciona (borde amarillo) y actualiza el panel lateral; doble clic abre el visor; clic derecho abre el mismo menú contextual.
- Estado vacío: "No hay documentos para mostrar".

**c) Panel lateral "Detalle del Documento"**
- Muestra nombre, descripción, tamaño, fecha, cédula, persona, empresa y "AES-256-GCM Encriptado".
- **Botones:** `Abrir` (visor), `Exportar`, `Editar`, `Eliminar`.

### 4.6 Barra de estado
Etiqueta inferior con mensajes ("Sesión activa: …", "Se muestran N PDFs", etc.).

### 4.7 Atajos y comportamientos globales
| Elemento | Acción |
| --- | --- |
| `Ctrl+Q` | Salir (con confirmación si hay sesión) |
| `Ctrl+F` | Foco en la búsqueda |
| `Ctrl+N` | Agregar PDF |
| `Supr` | Eliminar PDF seleccionado |
| `F11` | Pantalla completa/maximizar |
| Inactividad | Aviso a los 30 s antes de cerrar; logout automático (10 min por defecto, `session_timeout_minutes`) |

---

## 5. Modales del Panel Principal

### 5.1 Agregar PDF (`GestorPDF.mostrar_agregar`)
- `Seleccionar Archivo PDF` (diálogo de archivos).
- Campos: Descripción, Cédula\*, Nombres completos\*, Empresa (\* obligatorios).
- **Botones:** `Agregar y Encriptar (AES-256-GCM)`, `Cancelar`.
- Al terminar: refresca dashboard y lista.

### 5.2 Detalles y Edición de PDF
**Detalles del PDF** — ficha con ID, nombre, descripción, tamaño, fecha, cédula, nombres, empresa y cifrado.
- **Botones:** `Abrir` (visor), `Exportar`, `Cerrar`.

**Editar Metadatos** — campos: Nombre del archivo, Descripción, Cédula, Nombres, Empresa.
- **Botones:** `Guardar Cambios`, `Cancelar`.

### 5.3 Gestión de Personas (`GestorPersonas.mostrar`)
- Header morado + barra de búsqueda (cédula, nombre o empresa; filtra al escribir) + contador.
- Tabla: ID, Cédula, Nombres, Empresa, Documentos (auto-refresh cada 10 s, doble clic edita).
- **Botones:** `Agregar Persona`, `Editar`, `Eliminar`, `Refrescar` (con hora de la última actualización).
- **Formulario Agregar/Editar** (sub-modal): Cédula (solo lectura al editar), Nombres, Empresa; botones `Cancelar` y `Agregar`/`Guardar`.
- Eliminar advierte si la persona tiene documentos vinculados (quedan sin titular).

### 5.4 Log de Auditoría (`GestorAuditoria.mostrar`)
- Filtros: **Desde**, **Hasta** (`YYYY-MM-DD`), **Acción** (texto); botones `Filtrar` y `Limpiar`.
- Tabla: Fecha, Acción, PDF_ID, Usuario (máx. 2000 registros, carga por lotes en hilo secundario).
- **Botones inferiores:**
  - `Log del Sistema` → sub-modal de solo lectura con `datenjager.log`/`app.log` o, si no existen, información del sistema + últimos 500 eventos de auditoría (botón `Cerrar`).
  - `Refrescar`
  - `Limpiar Historial` → `ConfirmDialog` → borra todo y deja un registro de evidencia.

### 5.5 Configuración de Cuenta (`abrir_configuracion_cuenta`)
Ventana con **3 pestañas**:

| Pestaña | Contenido |
| --- | --- |
| **Contraseña** | Contraseña actual, nueva + barra de fortaleza, confirmación y código 2FA → `Cambiar Contraseña` (re-cifra secreto TOTP y códigos de respaldo, invalida el token de confianza) |
| **Códigos 2FA** | Lista de códigos de respaldo disponibles + `Copiar todos` y `Regenerar` |
| **Confianza** | Selector "Siempre solicitar / 24 horas / 48 horas / 7 días" + `Guardar preferencia` |

### 5.6 Visor PDF (`PDFViewerWindow`)
- Renderizado en memoria con PyMuPDF (el descifrado nunca se escribe a disco).
- Controles: `◀` / `▶` (página), `−` / `+` (zoom 50 %–200 %), etiqueta de página y zoom.
- Atajos: flechas, Re Pág/Av Pág, `+`/`-`, rueda del ratón.

---

## 6. Asistente IA (`ChatbotPanel`, ventana propia)
- Cabecera "Asistente IA – DatenJäger".
- **Botones de cabecera:**
  - `🧠 Reflexión` → sub-modal "Declaración Persona Transhumana" (declaración, pilares y frase aleatoria; botón `Cerrar`).
  - `Limpiar chat`
- Área de mensajes (burbujas usuario/bot, indicador "IA pensando…").
- Entrada de texto + `Enviar` (también Enter).
- Pie con la declaración principal (se muestra al iniciar sesión de chat).
- Mensaje de bienvenida automático; se cierra la sesión del chat al cerrar la ventana o al cerrar sesión.
- Si falla la API (403) usa respuestas de "modo local de prueba".

---

## 7. Reporte (sin panel propio)
Botón `Reporte` → diálogo de guardado → `ReporteInventario.generar_pdf`:

| Página | Contenido |
| --- | --- |
| 1. Portada | Resumen ejecutivo (4 tarjetas) y distribución por empresa |
| 2+. Inventario | Tabla de documentos paginada |
| Última | Gráfico de barras por empresa |

> El generador CSV (`generar_csv`) existe pero **no tiene botón** que lo invoque hoy.

---

## 8. Componentes transversales reutilizados

| Componente | Uso |
| --- | --- |
| `Notification` | Toasts apilables (éxito, error, advertencia, info) en todas las pantallas |
| `ConfirmDialog` | Logout, salir, eliminar PDF/persona, limpiar historial, regenerar códigos |
| `ProgressBarModerno` | Panel Principal |
| `PasswordStrengthBar` | Registro, Reset, Mi Cuenta |
| `CosmicBackground` | Intro y pantallas de acceso |
| `get_icon` / `get_dynamic_colors` | Íconos PNG y colores por tema (Claro/Oscuro) |

---

## 9. Observaciones detectadas durante el mapeo

Útiles para las fases de refactor (no se modificó nada):

1. **Reset de contraseña, paso 3:** `main.py` llama `PasswordStrengthBar(step_frame, width=380)` y `strength_bar.set_strength(...)`, pero la clase en `ui_components.py` solo acepta `parent` y expone `update()`. Ese paso probablemente lanza un error al abrirse.
2. **Reset de contraseña con 2FA cifrado:** como el secreto TOTP se guarda como `ENCK:` (con la clave de sesión), el flujo de reset siempre cae en el paso alternativo, y este tampoco puede descifrar los códigos de respaldo (también `ENCK:`), así que **el reset no puede completarse** para usuarios nuevos.
3. **Íconos (por verificar):** el reset de contraseña pide el ícono `arrow-right`. `EMOJI_MAP` es solo referencia y no se usa al ejecutar, así que lo que cuenta es si existe `assets/icons/arrow-right.png`. Si no existe, `get_icon` devuelve una imagen transparente y no falla. No se pudo comprobar porque la carpeta `assets` no estaba entre los archivos revisados.
4. **Métodos delegados sin uso en UI:** `mostrar_gestion_personas`, `mostrar_auditoria`, `slide_in_frame`, `_on_pdf_added`, etc. en `main.py` son envoltorios que ningún botón llama directamente.
5. **Colores hexadecimales sueltos:** siguen presentes en casi todos los módulos (candidato directo a la Fase 1, sección 1).
6. **Estados vacíos/carga:** solo existe estado vacío en el mosaico y "Cargando…" en Auditoría; el resto usa la barra de progreso (candidato a Fase 1, sección 3).
