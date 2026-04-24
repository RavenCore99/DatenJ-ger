<div align="center">

# DatenJager -- Sistema de Gestion Documental

*Digitalizacion, organizacion y consulta segura de documentos para el sector minero*

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-4CAF50?logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/Base%20de%20datos-SQLite-003B57?logo=sqlite&logoColor=white)
![AES-256](https://img.shields.io/badge/Encriptaci%C3%B3n-AES--256-FF9800?logo=letsencrypt&logoColor=white)
![2FA](https://img.shields.io/badge/Autenticaci%C3%B3n-2FA%20TOTP-2196F3?logo=google-authenticator&logoColor=white)
![Licencia](https://img.shields.io/badge/Licencia-MIT-4CAF50)

</div>

---

## Equipo del Proyecto

|                 Nombre                     |          Rol           |                 Contacto                         |
|--------------------------------------------|------------------------|--------------------------------------------------|
| Jorge Nicolas Castro Ballesteros           | DevOps Leader          |  jncastro@ucundinamarca.edu.co                   |
|  Yaderli Catalina Rodriguez Medina         | DevOps Support         |  ycatalinarodriguez@ucundinamarca.edu.co         |

> **Institucion:** Universidad de Cundinamarca Seccional Ubate 
> **Programa:**    Ingenieria de Sistemas y Computacion
> **Ano:**         2026

---

## Tabla de Contenidos

1. [Descripcion del Proyecto](#descripcion-del-proyecto)
2. [Capturas del Sistema](#capturas-del-sistema)
3. [Caracteristicas Principales](#caracteristicas-principales)
4. [Stack Tecnologico](#stack-tecnologico)
5. [Arquitectura del Proyecto](#arquitectura-del-proyecto)
6. [Descripcion de Modulos](#descripcion-de-modulos)
7. [Esquema de Base de Datos](#esquema-de-base-de-datos)
8. [Seguridad](#seguridad)
9. [Requisitos Previos](#requisitos-previos)
10. [Instalacion y Ejecucion](#instalacion-y-ejecucion)
11. [Guia de Uso](#guia-de-uso)
12. [Configuracion](#configuracion)
13. [Referencias](#referencias)

---

## Descripcion del Proyecto

**DatenJager** (del aleman: *"cazador de datos"*) es un sistema de gestion documental de escritorio disenado para optimizar el almacenamiento, organizacion y consulta de documentos en empresas del **sector minero**.

### Problematica

Muchas organizaciones continuan realizando su gestion documental mediante archivos fisicos, lo que genera:

- Desorden en los registros y dificultad para localizar documentos
- Perdida de documentos y deterioro de la informacion
- Altos tiempos de busqueda y consulta de informacion
- Costos operativos elevados por uso de papel y almacenamiento fisico
- Riesgos en la seguridad y confidencialidad de los datos

### Solucion Propuesta

DatenJager digitaliza los documentos e implementa un sistema de gestion documental centralizado con:

- Base de datos **SQLite** para centralizar la informacion
- **Encriptacion AES-256** para proteger los datos almacenados
- **Autenticacion de dos factores (2FA)** para reforzar la seguridad de acceso
- Interfaz grafica moderna e intuitiva con soporte de tema oscuro/claro
- Clasificacion de documentos por persona, etiquetas y descripcion
- Registro de auditoria para trazabilidad de acciones

---

## Capturas del Sistema

```
A continuacion podras ver un vistazo rapido de la version actual del sistema
```

### Pantalla de Login y Registro

![Login](docs/screenshots/login.png)

```
[Imagen: Pantalla de creacion de usuario con validacion de fortaleza de contrasena]
```
![R. debil](docs/screenshots/debil.png)

![R. regular](docs/screenshots/regular.png)

![R. fuerte](docs/screenshots/fuerte.png)

![R. muy fuerte](docs/screenshots/Mfuerte.png)

---

### Configuracion de Autenticacion de Dos Factores (2FA)

```
[Imagen: Configuracion del codigo QR para Google Authenticator]
```
![2FA](docs/screenshots/2fa.png)

---

### Panel Principal -- Dashboard

```
[Imagen: Panel principal mostrando estadisticas (PDFs totales, espacio usado, personas)]
```
![Panel Principal](docs/screenshots/panel.png)

---

### Gestion de Documentos

```
[Imagen: Vista de lista de documentos con filtros y etiquetas]
```
![Estadisticas](docs/screenshots/estats.png)

---

### Subida y Registro de Documentos

```
[Imagen: Formulario de subida de PDF con asociacion a persona y etiquetas]
```
![Formulario para datos](docs/screenshots/formulario.png)

---

### Modo Oscuro / Modo Claro

```
[Imagenes: Comparativa del sistema en modo oscuro vs modo claro]
```

![Modo Oscuro](docs/screenshots/oscuro.png)

![Modo Claro](docs/screenshots/claro.png)

---

## Caracteristicas Principales

| Modulo | Funcionalidad |
|--------|--------------|
| **Autenticacion** | Login con usuario/contrasena + 2FA (TOTP compatible con Google Authenticator) |
| **Seguridad** | Encriptacion AES-256 (Fernet) de documentos almacenados |
| **Contrasenas** | Hashing PBKDF2-HMAC-SHA256 con 260 000 iteraciones y salt aleatorio |
| **Proteccion** | Bloqueo de cuenta tras 5 intentos fallidos (15 min de espera) |
| **Documentos** | Subida, visualizacion, descarga y eliminacion de archivos PDF |
| **Busqueda** | Busqueda en tiempo real por nombre, descripcion y persona asociada |
| **Etiquetas** | Clasificacion de documentos con etiquetas personalizables |
| **Personas** | Asociacion de documentos a personas identificadas por cedula |
| **Dashboard** | Panel con estadisticas: total PDFs, espacio usado, personas registradas |
| **Auditoria** | Registro completo de acciones realizadas en el sistema |
| **Temas** | Soporte de modo oscuro, claro y automatico (segun el sistema) |
| **Atajos** | Atajos de teclado (`Ctrl+N`, `Ctrl+F`, `Ctrl+Q`, `F11`) |
| **Config** | Persistencia de configuracion de usuario (tema, tamano de ventana, etc.) |

---

## Stack Tecnologico

### Lenguajes y Runtime

| Tecnologia | Version | Descripcion |
|-----------|---------|-------------|
| **Python** | 3.10+ | Lenguaje principal del proyecto |

### Frameworks y Librerias UI

| Tecnologia | Version | Descripcion |
|-----------|---------|-------------|
| **CustomTkinter** | Latest | Framework de interfaz grafica moderna basado en Tkinter |
| **Tkinter (ttk)** | Built-in | Widgets nativos (Treeview, Scrollbar, Menu, Style) |
| **Pillow (PIL)** | Latest | Procesamiento y carga de imagenes e iconos PNG |

### Base de Datos

| Tecnologia | Version | Descripcion |
|-----------|---------|-------------|
| **SQLite** | Built-in | Motor de base de datos relacional local (modo WAL) |

### Seguridad y Criptografia

| Tecnologia | Version | Descripcion |
|-----------|---------|-------------|
| **cryptography (Fernet)** | Latest | Encriptacion AES-256 de PDFs y derivacion de session key |
| **pyotp** | Latest | Generacion y validacion de tokens TOTP para 2FA |
| **qrcode** | Latest | Generacion de codigos QR para configuracion 2FA |
| **hashlib / hmac / secrets** | Built-in | Hashing PBKDF2, HMAC-SHA256 y generacion de sales |

### Reportes y Documentos

| Tecnologia | Version | Descripcion |
|-----------|---------|-------------|
| **PyMuPDF (fitz)** | Latest | Renderizado de PDFs por paginas (visor inline con zoom y scroll) |

---

## Arquitectura del Proyecto

```
DatenJager/
|
|-- main.py              # Aplicacion principal  --  UI, auth, navegacion
|-- database.py          # Modulo de base de datos (SQLite, hashing, rate-limiting)
|-- encryption.py        # Modulo de encriptacion AES-256 (Fernet + PBKDF2)
|-- config.py            # Configuracion persistente del usuario (JSON)
|-- ui_components.py     # Componentes UI reutilizables (notificaciones, barras, dialogos)
|-- icons.py             # Sistema de iconos PNG (carga y cache de assets)
|-- reporter.py          # Generacion de reportes (CSV y PDF)
|
|-- pdf_manager.py       # Modulo de operaciones CRUD de PDFs
|-- personas.py          # Modulo de gestion de personas (CRUD titular)
|-- audit.py             # Modulo de auditoria (visor de logs y registro de eventos)
|
|-- assets/
|   |-- icons/           # Iconos PNG del sistema (44 iconos Lucide)
|
|-- docs/
|   |-- screenshots/     # Capturas de pantalla para documentacion
|
|-- base_datos_pdfs.db   # Base de datos SQLite (generada en tiempo de ejecucion)
|-- config.json          # Archivo de configuracion (generado en ejecucion)
|
|-- requirements.txt     # Dependencias del proyecto
|-- README.md            # Este archivo
```

---

## Descripcion de Modulos

### Modulos Core (infraestructura del sistema)

| Archivo | Tipo | Responsabilidad |
|---------|------|----------------|
| `main.py` | Core | Punto de entrada. Contiene la clase `AppDBPDF` con la UI principal: pantallas de intro, login, registro, dashboard, navegacion, 2FA, configuracion de cuenta y control de sesion |
| `database.py` | Core | Gestion de la base de datos SQLite: creacion de tablas, indices, hashing de contrasenas (PBKDF2), verificacion, rate-limiting y utilidades de formato |
| `config.py` | Core | Clase `Config` para lectura y escritura del archivo `config.json` con preferencias persistentes del usuario |

### Modulos de Seguridad

| Archivo | Tipo | Responsabilidad |
|---------|------|----------------|
| `encryption.py` | Seguridad | Clase `EncryptionManager` que gestiona la derivacion de claves y la encriptacion/desencriptacion AES-256 de los datos almacenados |

### Modulos de Logica de Negocio

| Archivo | Tipo | Responsabilidad |
|---------|------|----------------|
| `pdf_manager.py` | Logica | Clase `GestorPDF` con todas las operaciones CRUD de documentos: agregar, listar, buscar, ver detalles, abrir/descifrar, editar metadatos, eliminar y exportar |
| `personas.py` | Logica | Clase `GestorPersonas` con el CRUD de titulares de documentos: agregar, editar, eliminar personas, busqueda en tiempo real y auto-refresco |
| `audit.py` | Logica | Clase `GestorAuditoria` con el visor de log de auditoria (filtros por fecha y accion), visor de log backend y el metodo de registro de eventos |
| `reporter.py` | Logica | Clase `ReporteInventario` para generacion de reportes en formatos CSV y PDF con estadisticas del sistema |

### Modulos de Interfaz

| Archivo | Tipo | Responsabilidad |
|---------|------|----------------|
| `ui_components.py` | UI | Componentes visuales reutilizables: `Notification` (toasts apilables), `PasswordStrengthBar`, `GradientBackground` animado, `ProgressBarModerno`, `DashboardWidget`, `ConfirmDialog` y `PDFViewerWindow` |
| `icons.py` | UI | Sistema de carga y cache de iconos PNG desde `assets/icons/`. Provee la funcion `get_icon()` utilizada en toda la interfaz |

---

## Esquema de Base de Datos

```sql
Usuarios
|-- id               INTEGER PK AUTOINCREMENT
|-- nombre           TEXT UNIQUE NOT NULL
|-- contrasena       TEXT NOT NULL          -- Hash PBKDF2-HMAC-SHA256
|-- totp_secret      TEXT                   -- Secreto TOTP para 2FA
|-- totp_enabled     INTEGER DEFAULT 0
|-- backup_codes     TEXT                   -- Codigos de respaldo 2FA
|-- fecha_creacion   TEXT NOT NULL
|-- failed_attempts  INTEGER DEFAULT 0      -- Intentos fallidos de login
|-- locked_until     TEXT                   -- Bloqueo temporal de cuenta

Personas
|-- id               INTEGER PK AUTOINCREMENT
|-- cedula           TEXT UNIQUE NOT NULL
|-- nombres          TEXT NOT NULL

PDFs
|-- id               INTEGER PK AUTOINCREMENT
|-- nombre           TEXT NOT NULL
|-- descripcion      TEXT
|-- datos            BLOB NOT NULL          -- Contenido encriptado AES-256
|-- datos_encriptados INTEGER DEFAULT 1
|-- tamano           INTEGER NOT NULL
|-- fecha_subida     TEXT NOT NULL
|-- usuario_id       INTEGER FK -> Usuarios(id)
|-- persona_id       INTEGER FK -> Personas(id)

Etiquetas
|-- id               INTEGER PK AUTOINCREMENT
|-- nombre           TEXT UNIQUE NOT NULL

PDF_Etiquetas                               -- Tabla pivote N:M
|-- pdf_id           INTEGER FK -> PDFs(id)
|-- etiqueta_id      INTEGER FK -> Etiquetas(id)

Auditoria
|-- id               INTEGER PK AUTOINCREMENT
|-- accion           TEXT NOT NULL
|-- pdf_id           INTEGER
|-- usuario_id       INTEGER
|-- fecha            TEXT NOT NULL
```

---

## Seguridad

El sistema implementa multiples capas de seguridad:

### Autenticacion
- **Hashing de contrasenas:** PBKDF2-HMAC-SHA256 con **260 000 iteraciones** y salt aleatorio de 16 bytes. Formato almacenado: `pbkdf2:<salt_hex>:<hash_hex>`.
- **Compatibilidad retroactiva:** Soporta migracion automatica desde hashes SHA-256 legacy (sin salt) al nuevo formato PBKDF2 en el siguiente inicio de sesion exitoso.
- **Indicador de fortaleza:** Validacion visual de la contrasena durante el registro (Muy debil -> Muy fuerte).
- **Rate limiting:** Bloqueo de cuenta tras **5 intentos fallidos** durante **15 minutos**.

### 2FA (Autenticacion de Dos Factores)
- Basado en el estandar **TOTP (RFC 6238)**, compatible con **Google Authenticator** y otras apps TOTP.
- Configuracion mediante codigo QR generado con la clave secreta del usuario.
- **Codigos de respaldo** para recuperacion de cuenta.

### Encriptacion de Documentos
- Los PDFs se almacenan **encriptados** en la base de datos mediante **AES-256 (Fernet)**.
- La clave de encriptacion se deriva de la contrasena del usuario usando **PBKDF2-HMAC-SHA256** con **600 000 iteraciones** (numero de iteraciones mayor al del hashing de contrasenas ya que aqui se prioriza maxima resistencia a fuerza bruta sobre el tiempo de desbloqueo de sesion).
- Los documentos solo pueden ser desencriptados con la contrasena correcta del usuario.

### Base de Datos
- **WAL mode** (Write-Ahead Logging) para mayor concurrencia y rendimiento.
- Indices optimizados sobre columnas de busqueda frecuente.

---

## Requisitos Previos

- **Python 3.10** o superior
- **pip** (gestor de paquetes de Python)
- Sistema operativo: Windows, Linux o macOS

### Dependencias

```bash
pip install customtkinter cryptography pyotp qrcode Pillow PyMuPDF
```

O si dispones de un archivo `requirements.txt`:

```bash
pip install -r requirements.txt
```

---

## Instalacion y Ejecucion (DEV)

### 1. Clonar el repositorio

```bash
git clone https://github.com/RavenCore99/DatenJ-ger.git
cd DatenJ-ger
```

### 2. Crear un entorno virtual (recomendado)

```bash
# Crear entorno virtual
python -m venv venv

# Activar -- Windows
venv\Scripts\activate

# Activar -- Linux / macOS
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install customtkinter cryptography pyotp qrcode Pillow PyMuPDF
```

### 4. Ejecutar la aplicacion

```bash
python main.py
```

Al primer inicio, la base de datos `base_datos_pdfs.db` y el archivo de configuracion `config.json` se crearan automaticamente en el directorio del proyecto.

---

## Guia de Uso

### Primer Acceso

1. **Ejecuta** `python main.py` para iniciar el sistema.
2. En la pantalla de inicio, haz clic en **"Acceder al Sistema"** o pulsa en el titulo.
3. Como es la primera vez, selecciona la pestana **"Registrarse"**.
4. Ingresa un nombre de usuario y una contrasena segura (el indicador de fortaleza te guiara).
5. Opcionalmente, configura la **autenticacion de dos factores (2FA)** con Google Authenticator.

### Gestion de Documentos

| Accion | Como hacerlo |
|--------|-------------|
| **Subir PDF** | Boton "Agregar PDF" o `Ctrl+N` |
| **Buscar** | Campo de busqueda en tiempo real o `Ctrl+F` |
| **Ver/Descargar** | Seleccionar documento y hacer doble clic o boton "Abrir" |
| **Eliminar** | Seleccionar documento y boton "Eliminar" o tecla `Delete` |
| **Exportar** | Seleccionar documento y boton "Exportar" |

### Asociar Documentos a Personas

Al subir un documento es posible asignarlo a una persona registrada por cedula. Esto facilita la busqueda y organizacion de los documentos laborales por empleado.

### Atajos de Teclado

| Atajo | Accion |
|-------|--------|
| `Ctrl + N` | Agregar nuevo PDF |
| `Ctrl + F` | Enfocar campo de busqueda |
| `Ctrl + Q` | Cerrar la aplicacion |
| `F11` | Pantalla completa / Maximizar |
| `Delete` | Eliminar documento seleccionado |

---

## Configuracion

El archivo `config.json` se genera automaticamente y almacena las preferencias del usuario:

```json
{
    "theme": "System",
    "fullscreen": false,
    "window_size": "1100x760",
    "encryption_enabled": true,
    "2fa_enabled": true
}
```

| Clave | Valores posibles | Descripcion |
|-------|-----------------|-------------|
| `theme` | `"Dark"`, `"Light"`, `"System"` | Tema visual de la interfaz |
| `fullscreen` | `true` / `false` | Estado de pantalla completa |
| `window_size` | `"1100x760"` | Tamano de la ventana en pixeles |
| `encryption_enabled` | `true` / `false` | Habilita encriptacion AES-256 de PDFs |
| `2fa_enabled` | `true` / `false` | Habilita el modulo de 2FA |

El tema puede cambiarse desde la interfaz del sistema sin necesidad de editar el archivo manualmente.

---

## Referencias

- International Council on Archives (2016). *Principles and Functional Requirements for Records in Electronic Office Environments.*
- Davenport, T. H. & Prusak, L. (1998). *Working Knowledge: How Organizations Manage What They Know.* Harvard Business School Press.
- UNESCO (2015). *UNESCO Recommendation concerning the Preservation of, and Access to, Documentary Heritage.*
- Python Software Foundation. [https://www.python.org](https://www.python.org)
- CustomTkinter. [https://github.com/TomSchimansky/CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- cryptography.io -- Fernet (AES-256). [https://cryptography.io](https://cryptography.io)
- RFC 6238 -- TOTP: Time-Based One-Time Password Algorithm. [https://tools.ietf.org/html/rfc6238](https://tools.ietf.org/html/rfc6238)

---

<div align="center">

**DatenJager v.2.0** -- Gestion Documental 

*"La informacion es poder; protegerla es responsabilidad."*

</div>
