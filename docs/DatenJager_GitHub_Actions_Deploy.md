# Flujo de despliegue de DatenJäger con GitHub Actions
usar las rutas del proyecto. esta explicacion es para servir de apoyo y guia
Guía práctica para un proyecto con:

- **Backend:** Python
- **Base de datos:** SQLite local
- **Frontend:** React
- **Estilos:** Tailwind CSS
- **Desktop shell:** Electron
- **Desarrollo:** `npm run dev` / `npm run start`
- **Distribución:** Windows (`.exe`) y Linux (`.AppImage` / `.deb`)
- **CI/CD:** GitHub Actions
- **Empaquetado de Python:** PyInstaller
- **Empaquetado de Electron:** ejemplo con Electron Builder

> **Idea principal:** GitHub Actions no recibe los `.exe` ni los `.AppImage` para después instalarlos. Recibe tu **código fuente + archivos de configuración del build** y ejecuta el proceso de compilación dentro de runners de Windows y Linux. Los instaladores resultantes se publican como artefactos y/o dentro de una GitHub Release.

---

## 1. Flujo completo

El flujo recomendado es:

```text
Código fuente
    │
    ├── Python
    ├── React
    ├── Tailwind
    └── Electron
          │
          ▼
   Push a GitHub
          │
          ▼
   GitHub Actions
          │
      ┌───┴────┐
      │        │
      ▼        ▼
   Windows    Linux
      │        │
  PyInstaller PyInstaller
      │        │
      └───┬────┘
          ▼
   Build de Electron
          │
          ▼
   Instaladores
      │        │
      ▼        ▼
    .exe    .AppImage/.deb
          │
          ▼
    GitHub Release
```

El punto crítico es que **Python y Electron deben conservar rutas previsibles tanto en desarrollo como después del empaquetado**.

---

# 2. Estructura de carpetas recomendada

Una estructura razonable para DatenJäger sería:

```text
DatenJager/
│
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── database/
│   │   ├── services/
│   │   └── ...
│   └── ...
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── index.html
│   ├── package.json
│   └── ...
│
├── electron/
│   ├── main.js
│   └── preload.js
│
├── scripts/
│   └── build-python.py
│
├── package.json
├── package-lock.json
├── electron-builder.yml
├── .gitignore
│
└── .github/
    └── workflows/
        └── release.yml
```

## ¿Por qué es tan importante la estructura?

Porque Electron tendrá que localizar al proceso Python en dos situaciones distintas:

### Desarrollo

```text
DatenJager/
├── electron/main.js
├── backend/main.py
└── frontend/...
```

Electron puede ejecutar directamente:

```text
python backend/main.py
```

### Aplicación empaquetada

Después del build, el archivo Python ya no tiene por qué estar en `backend/main.py`.
Puede terminar dentro de algo parecido a:

```text
resources/
└── backend/
    └── datenjaeger-backend.exe
```

Por eso **no conviene dejar rutas absolutas escritas a mano** como:

```python
C:\Users\Nicolas\Desktop\DatenJager\backend\main.py
```

ni asumir que siempre existe:

```text
./backend/main.py
```

La aplicación debe resolver las rutas según el entorno en el que se esté ejecutando.

---

# 3. Preparar el backend Python

Desde Linux, entra al proyecto:

```bash
cd ~/DatenJager
```

Crea el entorno virtual si todavía no existe:

```bash
python -m venv .venv
source .venv/bin/activate
```

Instala las dependencias:

```bash
pip install -r backend/requirements.txt
```

Instala PyInstaller:

```bash
pip install pyinstaller
```

Comprueba que el backend funciona:

```bash
python backend/main.py
```

> Antes de pensar en GitHub Actions, el backend debe funcionar correctamente de forma local.

---

# 4. Crear el ejecutable del backend con PyInstaller

Inicialmente es mejor utilizar `onedir` durante las pruebas porque facilita detectar archivos que falten.

Ejemplo:

```bash
pyinstaller \
  --name DatenJagerBackend \
  --onedir \
  --noconfirm \
  backend/main.py
```

Resultado aproximado:

```text
DatenJager/
└── dist/
    └── DatenJagerBackend/
        ├── DatenJagerBackend
        ├── Python runtime
        ├── librerías
        └── dependencias
```

Cuando el build sea estable se puede evaluar `--onefile`, pero no es obligatorio y no siempre es la mejor opción para una aplicación que necesita varios recursos.

---

# 5. La SQLite NO debe vivir dentro de la carpeta de instalación

Este punto es especialmente importante para DatenJäger.

No conviene hacer esto:

```text
C:\Program Files\DatenJager\database.db
```

ni esto:

```text
AppImage/resources/database.db
```

porque el directorio de instalación pertenece a la aplicación y puede ser reemplazado durante una actualización.

La base de datos debe vivir en el directorio de datos del usuario.

Por ejemplo, conceptualmente:

### Windows

```text
%APPDATA%\DatenJager\database.db
```

### Linux

```text
~/.local/share/DatenJager/database.db
```

El backend debe:

1. Resolver el directorio de datos del usuario.
2. Crear la carpeta si no existe.
3. Comprobar si existe la SQLite.
4. Si no existe, crearla.
5. Ejecutar las tablas/migraciones iniciales.

Ejemplo conceptual en Python:

```python
from pathlib import Path
import os
import sqlite3


def get_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.getenv("APPDATA", Path.home()))
    else:
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    data_dir = base / "DatenJager"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


DB_PATH = get_data_dir() / "datenjager.db"

connection = sqlite3.connect(DB_PATH)
```

La primera ejecución crea:

```text
DatenJager/
└── datos del usuario
    └── datenjager.db
```

La siguiente ejecución reutiliza esa misma base.

---

# 6. Preparar Electron

En `electron/main.js`, la idea es diferenciar desarrollo y producción.

Durante desarrollo puedes lanzar Python así:

```text
python backend/main.py
```

En producción, Electron debe lanzar el ejecutable generado por PyInstaller.

Una estrategia habitual es colocar el backend dentro de los recursos de Electron:

```text
resources/
└── backend/
    └── DatenJagerBackend(.exe)
```

Entonces Electron puede hacer algo parecido a:

```js
const isDev = !app.isPackaged;
```

Y seleccionar el backend correspondiente:

```js
if (isDev) {
    // Ejecutar Python del proyecto
} else {
    // Ejecutar el backend empaquetado dentro de resources
}
```

**No mezcles las rutas de desarrollo con las rutas del instalador.**

---

# 7. Preparar React + Tailwind

Desde la raíz del proyecto:

```bash
npm install
```

Para comprobar el frontend:

```bash
npm run build
```

El resultado dependerá de tu configuración de React/Vite/Webpack, por ejemplo:

```text
frontend/
└── dist/
    ├── index.html
    └── assets/
```

Electron debe cargar esos archivos en producción.

En desarrollo puede cargar algo como:

```text
http://localhost:5173
```

mientras que en producción puede cargar:

```text
file:///.../dist/index.html
```

La ruta exacta depende de cómo tengas configurado React y Electron.

---

# 8. Añadir Electron Builder

Desde la raíz:

```bash
npm install --save-dev electron-builder
```

También debe existir Electron como dependencia de desarrollo:

```bash
npm install --save-dev electron
```

El `package.json` puede tener una sección aproximada como:

```json
{
  "scripts": {
    "dev": "...",
    "start": "...",
    "build:frontend": "...",
    "build": "npm run build:frontend",
    "dist": "electron-builder"
  }
}
```

> **No copies este bloque literalmente todavía.** El comando exacto depende de si actualmente utilizas Vite, CRA, Webpack u otro sistema para React.

---

# 9. Configurar los archivos que Electron Builder debe incluir

Una configuración conceptual de `electron-builder.yml` podría ser:

```yaml
appId: com.datenjager.app
productName: DatenJager

files:
  - electron/**
  - frontend/dist/**
  - package.json

extraResources:
  - from: dist/DatenJagerBackend/
    to: backend

win:
  target:
    - nsis

linux:
  target:
    - AppImage
    - deb
```

La parte crítica es:

```yaml
extraResources:
  - from: dist/DatenJagerBackend/
    to: backend
```

Eso indica que el backend generado por PyInstaller debe viajar dentro del paquete final.

---

# 10. Prueba local completa en Linux

Antes de usar GitHub Actions, prueba el pipeline local.

### Backend

```bash
rm -rf build dist

pyinstaller \
  --name DatenJagerBackend \
  --onedir \
  --noconfirm \
  backend/main.py
```

### Frontend

```bash
npm run build
```

### Electron

```bash
npm run dist
```

El resultado debería aparecer en una carpeta del tipo:

```text
release/
└── DatenJager-<version>.AppImage
```

O en la carpeta de distribución que tengas configurada.

---

# 11. Preparar Git

Comprueba el estado:

```bash
git status
```

Añade los archivos fuente y configuración:

```bash
git add .
```

Haz el commit:

```bash
git commit -m "chore: prepare desktop release pipeline"
```

Sube el código:

```bash
git push origin main
```

---

# 12. No subas los builds al repositorio

En `.gitignore` deberían estar, como mínimo, carpetas generadas como:

```gitignore
node_modules/
.venv/
__pycache__/
.pytest_cache/

build/
dist/
release/

*.pyc
*.log
```

La idea es:

```text
GitHub Repository
    = código fuente + configuración
```

No:

```text
GitHub Repository
    = código + .exe + AppImage + builds temporales
```

Los instaladores se publican mediante **GitHub Releases**.

---

# 13. Crear el workflow de GitHub Actions

Crea la carpeta:

```bash
mkdir -p .github/workflows
```

Crea el archivo:

```bash
touch .github/workflows/release.yml
```

La estructura queda:

```text
.github/
└── workflows/
    └── release.yml
```

---

# 14. Workflow conceptual para Windows y Linux

Un ejemplo inicial sería:

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  build:
    strategy:
      matrix:
        os: [windows-latest, ubuntu-latest]

    runs-on: ${{ matrix.os }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: npm

      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r backend/requirements.txt
          pip install pyinstaller

      - name: Install Node dependencies
        run: npm ci

      - name: Build Python backend
        run: pyinstaller --name DatenJagerBackend --onedir --noconfirm backend/main.py

      - name: Build frontend
        run: npm run build

      - name: Build Electron application
        run: npm run dist

      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: DatenJager-${{ matrix.os }}
          path: |
            release/**
            dist/**
```

> Este workflow es una **plantilla de referencia**. La ruta exacta de salida de Electron Builder, el comando de React y los archivos que necesite PyInstaller dependen de tu proyecto actual.

---

# 15. ¿Cómo llega el instalador a GitHub Releases?

El `upload-artifact` anterior guarda el resultado dentro de la ejecución de GitHub Actions.

Para una publicación real, hay que añadir un paso que cree/actualice una **GitHub Release** y adjunte los instaladores generados.

Una forma habitual es usar una acción de release, por ejemplo:

```yaml
- name: Publish Release
  uses: softprops/action-gh-release@v2
  with:
    files: |
      release/**/*.exe
      release/**/*.AppImage
      release/**/*.deb
```

Como la compilación ocurre en dos sistemas operativos, en un pipeline definitivo suele ser más limpio separar los jobs de build y después ejecutar un job final que recopile los artefactos y cree la Release.

---

# 16. Crear una versión

Cuando todo esté funcionando:

```bash
git add .
git commit -m "release: 1.0.0"
git push origin main
```

Crear el tag:

```bash
git tag v1.0.0
```

Subir el tag:

```bash
git push origin v1.0.0
```

Ese `push` del tag activa:

```yaml
on:
  push:
    tags:
      - 'v*.*.*'
```

Y GitHub Actions comienza a construir.

---

# 17. Qué ocurre después del `git push origin v1.0.0`

GitHub recibe el tag:

```text
v1.0.0
```

Después:

```text
GitHub Actions
      │
      ├── Windows Runner
      │      ├── Python
      │      ├── PyInstaller
      │      ├── React
      │      └── Electron Builder
      │
      └── Linux Runner
             ├── Python
             ├── PyInstaller
             ├── React
             └── Electron Builder
```

Resultado:

```text
Windows
└── DatenJager Setup 1.0.0.exe

Linux
├── DatenJager-1.0.0.AppImage
└── DatenJager-1.0.0.deb
```

Finalmente:

```text
GitHub
└── Releases
    └── v1.0.0
        ├── DatenJager Setup 1.0.0.exe
        ├── DatenJager-1.0.0.AppImage
        └── DatenJager-1.0.0.deb
```

---

# 18. El usuario final no necesita Python ni Node

El usuario final debe recibir solamente el resultado empaquetado.

### Windows

```text
DatenJager-Setup.exe
```

Instala la aplicación.

### Linux

Puede descargar:

```text
DatenJager.AppImage
```

o:

```text
DatenJager.deb
```

El usuario no debería necesitar instalar manualmente:

```text
Python
Node.js
npm
React
Tailwind
PyInstaller
```

Todo eso debe quedar resuelto durante la compilación y el empaquetado.

---

# 19. Sobre instalar mediante curl en Linux

Una opción sencilla es distribuir el AppImage directamente desde GitHub Releases.

Por ejemplo, el usuario podría descargarlo con:

```bash
curl -L -o DatenJager.AppImage \
  https://github.com/USUARIO/DatenJager/releases/download/v1.0.0/DatenJager-1.0.0.AppImage
```

Luego:

```bash
chmod +x DatenJager.AppImage
```

Y ejecutar:

```bash
./DatenJager.AppImage
```

Posteriormente puedes crear un script de instalación más cómodo si deseas que el usuario solamente ejecute un único comando.

---

# 20. Rutas: regla de oro para DatenJäger

Hay tres tipos de rutas y conviene mantenerlas separadas.

## A. Código fuente

Ejemplo:

```text
backend/main.py
frontend/src/...
electron/main.js
```

Son rutas del proyecto.

## B. Recursos empaquetados

Ejemplo:

```text
resources/backend/DatenJagerBackend
resources/frontend/...
```

Son rutas de instalación/ejecución de la aplicación.

## C. Datos del usuario

Ejemplo:

```text
%APPDATA%/DatenJager/
~/.local/share/DatenJager/
```

Aquí deben vivir:

```text
SQLite
configuración
preferencias
cache propia de la aplicación
```

**No mezclar A, B y C.**

---

# 21. Checklist antes de crear la primera Release

```text
[ ] npm run dev funciona
[ ] npm run build funciona
[ ] Python inicia correctamente
[ ] SQLite se crea automáticamente
[ ] SQLite está fuera de la carpeta de instalación
[ ] PyInstaller genera el backend
[ ] Electron encuentra el backend en desarrollo
[ ] Electron encuentra el backend en producción
[ ] Las rutas son relativas/dinámicas
[ ] node_modules está en .gitignore
[ ] dist/build/release están en .gitignore
[ ] GitHub Actions puede instalar las dependencias
[ ] Windows ejecuta el backend empaquetado
[ ] Linux ejecuta el backend empaquetado
[ ] El instalador conserva los datos del usuario al actualizar
```

---

# 22. Flujo diario después de dejarlo configurado

Una vez terminada toda la configuración, el flujo ideal será:

```bash
git add .
git commit -m "feat: nueva funcionalidad"
git push origin main
```

Cuando tengas una versión lista:

```bash
git tag v1.1.0
git push origin v1.1.0
```

Y a partir de ahí:

```text
GitHub Actions
      ↓
Compila Windows
      ↓
Compila Linux
      ↓
Genera instaladores
      ↓
Crea GitHub Release
      ↓
Usuario descarga
```

---

# 23. Punto que debe adaptarse al proyecto real

Antes de copiar y pegar todo el workflow, hay cuatro datos que deben coincidir exactamente con DatenJäger:

1. **Dónde está el entry point de Python**, por ejemplo `backend/main.py`.
2. **Cómo se construye actualmente React**, por ejemplo `npm run build` y si genera `dist/`.
3. **Dónde está el `main.js` de Electron**.
4. **Dónde quieres que Electron coloque el ejecutable PyInstaller dentro de `resources/`.**

Además, si Python utiliza archivos adicionales como:

```text
JSON
YAML
modelos
plantillas
iconos
migraciones SQL
certificados
```

PyInstaller o Electron Builder tendrán que incluirlos explícitamente.

---

# 24. Resultado final esperado para DatenJäger

La arquitectura final debería verse conceptualmente así:

```text
DatenJäger
│
├── Python Backend
│      └── PyInstaller
│             ↓
│       Backend ejecutable
│
├── React + Tailwind
│      └── npm run build
│             ↓
│       Frontend estático
│
├── Electron
│      ├── main.js
│      └── preload.js
│             ↓
│       Aplicación Desktop
│
└── Electron Builder
       │
       ├── Windows → .exe
       └── Linux   → .AppImage / .deb
                       │
                       ▼
                 GitHub Release
```

La idea más importante es esta:

```text
GitHub Repository
        ≠
Instalador

GitHub Repository
        =
Código + configuración del build

GitHub Release
        =
Instaladores compilados
```

Y:

```text
Aplicación instalada
        ≠
Base de datos del usuario
```

La aplicación se puede actualizar y reinstalar sin destruir la SQLite del usuario siempre que la base esté almacenada en el directorio de datos apropiado y el código la busque mediante una ruta dinámica.
