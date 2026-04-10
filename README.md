<div align="center">

# 🔐 DatenJäger — Sistema de Gestión Documental

*Digitalización, organización y consulta segura de documentos para el sector minero*

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-4CAF50?logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/Base%20de%20datos-SQLite-003B57?logo=sqlite&logoColor=white)
![AES-256](https://img.shields.io/badge/Encriptaci%C3%B3n-AES--256-FF9800?logo=letsencrypt&logoColor=white)
![2FA](https://img.shields.io/badge/Autenticaci%C3%B3n-2FA%20TOTP-2196F3?logo=google-authenticator&logoColor=white)
![Licencia](https://img.shields.io/badge/Licencia-MIT-4CAF50)

</div>

---

## 👥 Equipo del Proyecto



|                 Nombre                     |          Rol           |                 Contacto                         |
|--------------------------------------------|------------------------|--------------------------------------------------|
| Jorge Nicolas Castro Ballesteros           | DevOps Leader          |  jncastro@ucundinamarca.edu.co                   |
|  Yaderli Catalina Rodriguez Medina         | DevOps Support         |  ycatalinarodriguez@ucundinamarca.edu.co         |


> **Institución:** Universidad de Cundinamarca Seccional Ubaté 
> **Programa:**    Ingenieria de Sistemas y Computación
> **Año:**         2026
---

## 📋 Tabla de Contenidos

1. [Descripción del Proyecto](#-descripción-del-proyecto)
2. [Capturas del Sistema](#-capturas-del-sistema)
3. [Características Principales](#-características-principales)
4. [Stack Tecnológico](#-stack-tecnológico)
5. [Arquitectura del Proyecto](#-arquitectura-del-proyecto)
6. [Esquema de Base de Datos](#-esquema-de-base-de-datos)
7. [Seguridad](#-seguridad)
8. [Requisitos Previos](#-requisitos-previos)
9. [Instalación y Ejecución](#-instalación-y-ejecución)
10. [Guía de Uso](#-guía-de-uso)
11. [Configuración](#-configuración)
12. [Referencias](#-referencias)

---

## 📖 Descripción del Proyecto

**DatenJäger** (del alemán: *"cazador de datos"*) es un sistema de gestión documental de escritorio diseñado para optimizar el almacenamiento, organización y consulta de documentos en empresas del **sector minero**.

### Problemática

Muchas organizaciones continúan realizando su gestión documental mediante archivos físicos, lo que genera:

- 🗂️ Desorden en los registros y dificultad para localizar documentos
- 📄 Pérdida de documentos y deterioro de la información
- ⏱️ Altos tiempos de búsqueda y consulta de información
- 💰 Costos operativos elevados por uso de papel y almacenamiento físico
- 🔓 Riesgos en la seguridad y confidencialidad de los datos

### Solución Propuesta

DatenJäger digitaliza los documentos e implementa un sistema de gestión documental centralizado con:

- Base de datos **SQLite** para centralizar la información
- **Encriptación AES-256** para proteger los datos almacenados
- **Autenticación de dos factores (2FA)** para reforzar la seguridad de acceso
- Interfaz gráfica moderna e intuitiva con soporte de tema oscuro/claro
- Clasificación de documentos por persona, etiquetas y descripción
- Registro de auditoría para trazabilidad de acciones

---

## 📸 Capturas del Sistema
```
A continuación podrás ver un vistazo rapido de la versión actual del sistema
```
### Pantalla de Login y Registro

![Login](docs/screenshots/login.png)

```
[📷 Imagen: Pantalla de creación de usuario con validación de fortaleza de contraseña]
```
![R. debil](docs/screenshots/debil.png)

![R. regular](docs/screenshots/regular.png)

![R. fuerte](docs/screenshots/fuerte.png)

![R. muy fuerte](docs/screenshots/Mfuerte.png)
---

### Configuración de Autenticación de Dos Factores (2FA)

```
[📷 Imagen: Configuración del código QR para Google Authenticator]
```
![2FA](docs/screenshots/2fa.png)
---
### Panel Principal — Dashboard

```
[📷 Imagen: Panel principal mostrando estadísticas (PDFs totales, espacio usado, personas)]
```
![Panel Principal](docs/screenshots/panel.png)
---

### Gestión de Documentos
```
[📷 Imagen: Vista de lista de documentos con filtros y etiquetas]
```
![Estadisticas](docs/screenshots/estats.png)
---

### Subida y Registro de Documentos

```
[📷 Imagen: Formulario de subida de PDF con asociación a persona y etiquetas]
```
![Formulario para datos](docs/screenshots/formulario.png)
---

### Modo Oscuro / Modo Claro

```
[📷 Imagenes: Comparativa del sistema en modo oscuro vs modo claro]


```
[📷 Imagen: modo oscuro]

![Modo Oscuro](docs/screenshots/oscuro.png)

[📷 Imagen: modo claro]

![Modo Claro](docs/screenshots/claro.png)
---

## ✨ Características Principales

| Módulo | Funcionalidad |
|--------|--------------|
| 🔐 **Autenticación** | Login con usuario/contraseña + 2FA (TOTP compatible con Google Authenticator) |
| 🔒 **Seguridad** | Encriptación AES-256 (Fernet) de documentos almacenados |
| 🔑 **Contraseñas** | Hashing PBKDF2-HMAC-SHA256 con 260 000 iteraciones y salt aleatorio |
| 🚫 **Protección** | Bloqueo de cuenta tras 5 intentos fallidos (15 min de espera) |
| 📄 **Documentos** | Subida, visualización, descarga y eliminación de archivos PDF |
| 🔍 **Búsqueda** | Búsqueda en tiempo real por nombre, descripción y persona asociada |
| 🏷️ **Etiquetas** | Clasificación de documentos con etiquetas personalizables |
| 👤 **Personas** | Asociación de documentos a personas identificadas por cédula |
| 📊 **Dashboard** | Panel con estadísticas: total PDFs, espacio usado, personas registradas |
| 📋 **Auditoría** | Registro completo de acciones realizadas en el sistema |
| 🎨 **Temas** | Soporte de modo oscuro, claro y automático (según el sistema) |
| ⌨️ **Atajos** | Atajos de teclado (`Ctrl+N`, `Ctrl+F`, `Ctrl+Q`, `F11`) |
| 💾 **Config** | Persistencia de configuración de usuario (tema, tamaño de ventana, etc.) |

---

## 🛠️ Stack Tecnológico

| Tecnología | Versión | Uso |
|-----------|---------|-----|
| **Python** | 3.10+ | Lenguaje principal |
| **CustomTkinter** | Latest | Interfaz gráfica moderna |
| **SQLite** | Built-in | Base de datos local |
| **cryptography (Fernet)** | Latest | Encriptación AES-256 de PDFs y session key |
| **pyotp** | Latest | Generación/validación de tokens TOTP (2FA) |
| **qrcode** | Latest | Generación de códigos QR para 2FA |
| **Pillow (PIL)** | Latest | Procesamiento de imágenes |
| **PyMuPDF (fitz)** | Latest | Visor PDF inline (renderizado por páginas, zoom, scroll) |
| **hashlib / hmac / secrets** | Built-in | Hashing PBKDF2, HMAC-SHA256 en config y generación de sales |

---

## 🏗️ Arquitectura del Proyecto

```
DatenJäger/
│
├── main.py              # Aplicación principal — UI y lógica de negocio
├── database.py          # Módulo de base de datos (SQLite, hashing, rate-limiting)
├── encryption.py        # Módulo de encriptación AES-256 (Fernet + PBKDF2)
├── config.py            # Módulo de configuración persistente (JSON)
├── ui_components.py     # Componentes UI reutilizables (notificaciones, barras, diálogos)
│
├── base_datos_pdfs.db   # Base de datos SQLite (generada en tiempo de ejecución)
├── config.json          # Archivo de configuración del usuario (generado en ejecución)
│
└── README.md            # Este archivo
```

### Descripción de Módulos

| Archivo | Responsabilidad |
|---------|----------------|
| `main.py` | Punto de entrada de la aplicación. Contiene la clase `AppDBPDF` con toda la lógica de la UI: pantallas de intro, login, registro, gestión de PDFs, 2FA, configuración y auditoría |
| `database.py` | Gestión de la base de datos SQLite: creación de tablas, índices, hashing de contraseñas (PBKDF2), verificación, rate-limiting, y utilidades de formato |
| `encryption.py` | Clase `EncryptionManager` que gestiona la derivación de claves y la encriptación/desencriptación AES-256 de los datos almacenados |
| `config.py` | Clase `Config` que lee y escribe el archivo `config.json` con la configuración persistente del usuario |
| `ui_components.py` | Componentes visuales reutilizables: `Notification` (toasts apilables), `PasswordStrengthBar`, `GradientBackground` animado, `ProgressBarModerno`, `DashboardWidget` y `ConfirmDialog` |

---

## 🗄️ Esquema de Base de Datos

```sql
Usuarios
├── id               INTEGER PK AUTOINCREMENT
├── nombre           TEXT UNIQUE NOT NULL
├── contrasena       TEXT NOT NULL          -- Hash PBKDF2-HMAC-SHA256
├── totp_secret      TEXT                   -- Secreto TOTP para 2FA
├── totp_enabled     INTEGER DEFAULT 0
├── backup_codes     TEXT                   -- Códigos de respaldo 2FA
├── fecha_creacion   TEXT NOT NULL
├── failed_attempts  INTEGER DEFAULT 0      -- Intentos fallidos de login
└── locked_until     TEXT                   -- Bloqueo temporal de cuenta

Personas
├── id               INTEGER PK AUTOINCREMENT
├── cedula           TEXT UNIQUE NOT NULL
└── nombres          TEXT NOT NULL

PDFs
├── id               INTEGER PK AUTOINCREMENT
├── nombre           TEXT NOT NULL
├── descripcion      TEXT
├── datos            BLOB NOT NULL          -- Contenido encriptado AES-256
├── datos_encriptados INTEGER DEFAULT 1
├── tamano           INTEGER NOT NULL
├── fecha_subida     TEXT NOT NULL
├── usuario_id       INTEGER FK → Usuarios(id)
└── persona_id       INTEGER FK → Personas(id)

Etiquetas
├── id               INTEGER PK AUTOINCREMENT
└── nombre           TEXT UNIQUE NOT NULL

PDF_Etiquetas                               -- Tabla pivote N:M
├── pdf_id           INTEGER FK → PDFs(id)
└── etiqueta_id      INTEGER FK → Etiquetas(id)

Auditoria
├── id               INTEGER PK AUTOINCREMENT
├── accion           TEXT NOT NULL
├── pdf_id           INTEGER
├── usuario_id       INTEGER
└── fecha            TEXT NOT NULL
```

---

## 🔒 Seguridad

El sistema implementa múltiples capas de seguridad:

### Autenticación
- **Hashing de contraseñas:** PBKDF2-HMAC-SHA256 con **260 000 iteraciones** y salt aleatorio de 16 bytes. Formato almacenado: `pbkdf2:<salt_hex>:<hash_hex>`.
- **Compatibilidad retroactiva:** Soporta migración automática desde hashes SHA-256 legacy (sin salt) al nuevo formato PBKDF2 en el siguiente inicio de sesión exitoso.
- **Indicador de fortaleza:** Validación visual de la contraseña durante el registro (Muy débil → Muy fuerte).
- **Rate limiting:** Bloqueo de cuenta tras **5 intentos fallidos** durante **15 minutos**.

### 2FA (Autenticación de Dos Factores)
- Basado en el estándar **TOTP (RFC 6238)**, compatible con **Google Authenticator** y otras apps TOTP.
- Configuración mediante código QR generado con la clave secreta del usuario.
- **Códigos de respaldo** para recuperación de cuenta.

### Encriptación de Documentos
- Los PDFs se almacenan **encriptados** en la base de datos mediante **AES-256 (Fernet)**.
- La clave de encriptación se deriva de la contraseña del usuario usando **PBKDF2-HMAC-SHA256** con **600 000 iteraciones** (número de iteraciones mayor al del hashing de contraseñas ya que aquí se prioriza máxima resistencia a fuerza bruta sobre el tiempo de desbloqueo de sesión).
- Los documentos solo pueden ser desencriptados con la contraseña correcta del usuario.

### Base de Datos
- **WAL mode** (Write-Ahead Logging) para mayor concurrencia y rendimiento.
- Índices optimizados sobre columnas de búsqueda frecuente.

---

## 📦 Requisitos Previos

- **Python 3.10** o superior
- **pip** (gestor de paquetes de Python)
- Sistema operativo: Windows, Linux o macOS

### Dependencias

```bash
pip install customtkinter cryptography pyotp qrcode Pillow
```

O si dispones de un archivo `requirements.txt`:

```bash
pip install -r requirements.txt
```

---

## 🚀 Instalación y Ejecución

### 1. Clonar el repositorio

```bash
git clone https://github.com/RavenCore99/DatenJ-ger.git
cd DatenJ-ger
```

### 2. Crear un entorno virtual (recomendado)

```bash
# Crear entorno virtual
python -m venv venv

# Activar — Windows
venv\Scripts\activate

# Activar — Linux / macOS
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install customtkinter cryptography pyotp qrcode Pillow
```

### 4. Ejecutar la aplicación

```bash
python main.py
```

Al primer inicio, la base de datos `base_datos_pdfs.db` y el archivo de configuración `config.json` se crearán automáticamente en el directorio del proyecto.

<!-- Inserta aquí una imagen o GIF del proceso de instalación si lo deseas -->
<!-- Ejemplo: ![Instalación](docs/images/instalacion.gif) -->

---

## 📖 Guía de Uso

### Primer Acceso

1. **Ejecuta** `python main.py` para iniciar el sistema.
2. En la pantalla de inicio, haz clic en **"Acceder al Sistema"** o pulsa en el título.
3. Como es la primera vez, selecciona la pestaña **"Registrarse"**.
4. Ingresa un nombre de usuario y una contraseña segura (el indicador de fortaleza te guiará).
5. Opcionalmente, configura la **autenticación de dos factores (2FA)** con Google Authenticator.

<!-- Inserta aquí una imagen del flujo de primer acceso -->
```
[📷 Imagen: Flujo de registro de nuevo usuario]
```

### Gestión de Documentos

| Acción | Cómo hacerlo |
|--------|-------------|
| **Subir PDF** | Botón "📄 Agregar PDF" o `Ctrl+N` |
| **Buscar** | Campo de búsqueda en tiempo real o `Ctrl+F` |
| **Ver/Descargar** | Seleccionar documento → Botón "👁 Ver PDF" |
| **Eliminar** | Seleccionar documento → Botón "🗑 Eliminar" o tecla `Delete` |
| **Filtrar por etiqueta** | Selector de etiquetas en la barra de herramientas |

### Asociar Documentos a Personas

Al subir un documento es posible asignarlo a una persona registrada por cédula. Esto facilita la búsqueda y organización de los documentos laborales por empleado.

### Atajos de Teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl + N` | Agregar nuevo PDF |
| `Ctrl + F` | Enfocar campo de búsqueda |
| `Ctrl + Q` | Cerrar la aplicación |
| `F11` | Pantalla completa / Maximizar |
| `Delete` | Eliminar documento seleccionado |

---

## ⚙️ Configuración

El archivo `config.json` se genera automáticamente y almacena las preferencias del usuario:

```json
{
    "theme": "System",
    "fullscreen": false,
    "window_size": "1100x760",
    "encryption_enabled": true,
    "2fa_enabled": true
}
```

| Clave | Valores posibles | Descripción |
|-------|-----------------|-------------|
| `theme` | `"Dark"`, `"Light"`, `"System"` | Tema visual de la interfaz |
| `fullscreen` | `true` / `false` | Estado de pantalla completa |
| `window_size` | `"1100x760"` | Tamaño de la ventana en píxeles |
| `encryption_enabled` | `true` / `false` | Habilita encriptación AES-256 de PDFs |
| `2fa_enabled` | `true` / `false` | Habilita el módulo de 2FA |

El tema puede cambiarse desde la interfaz del sistema sin necesidad de editar el archivo manualmente.

---

## 📚 Referencias

- International Council on Archives (2016). *Principles and Functional Requirements for Records in Electronic Office Environments.*
- Davenport, T. H. & Prusak, L. (1998). *Working Knowledge: How Organizations Manage What They Know.* Harvard Business School Press.
- UNESCO (2015). *UNESCO Recommendation concerning the Preservation of, and Access to, Documentary Heritage.*
- Python Software Foundation. [https://www.python.org](https://www.python.org)
- CustomTkinter. [https://github.com/TomSchimansky/CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- cryptography.io — Fernet (AES-256). [https://cryptography.io](https://cryptography.io)
- RFC 6238 — TOTP: Time-Based One-Time Password Algorithm. [https://tools.ietf.org/html/rfc6238](https://tools.ietf.org/html/rfc6238)

---

<div align="center">

**DatenJäger v.2.0** — Desarrollado con ❤️ para la gestión documental segura

*"La información es poder; protegerla es responsabilidad."*

</div>
