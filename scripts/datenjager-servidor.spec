# -*- mode: python ; coding: utf-8 -*-
# Copyright (c) 2024 DatenJäger. All rights reserved.
# scripts/datenjager-servidor.spec — empaquetado del backend Python
# Trazabilidad Jira: SCRUM-54 (DatenJäger — Electron).

"""Receta de PyInstaller para el servicio local de DatenJäger (Fase 5).

Se usa una receta (`spec`) y no una lista de argumentos en la línea de comandos
para que el empaquetado sea **reproducible**: los imports ocultos, los metadatos
y las exclusiones viven en el repositorio, no en la memoria de quien lo lanza.

Decisiones:

* **`--onedir`, no `--onefile`.** `onefile` descomprime todo el paquete en un
  directorio temporal **en cada arranque**, lo que encarece el arranque en frío y
  deja a las bibliotecas nativas (`cryptography`, `PyMuPDF`) dependiendo de rutas
  volátiles. En `onedir` el árbol se instala una vez y el binario arranca directo.
* **Nada de Tk.** El servicio es backend puro; `customtkinter`, `tkinter` y el
  motor de dibujo de matplotlib para Tk solo engordarían el paquete sin usarse.
* **Metadatos copiados.** FastAPI, Starlette, Uvicorn y Pydantic se inspeccionan
  a sí mismos con `importlib.metadata`; sin sus metadatos, el binario arranca y
  falla al construir la aplicación.

Uso (a través del guion, que además fija las carpetas):

    ./venv/bin/python scripts/empaquetar_backend.py
"""

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

#: `SPECPATH` lo inyecta PyInstaller: es el directorio de esta receta. Con él la
#: receta se puede invocar desde cualquier directorio de trabajo, que es lo que
#: necesita GitHub Actions.
import os  # noqa: E402

AQUI = os.path.abspath(SPECPATH)
RAIZ = os.path.abspath(os.path.join(AQUI, ".."))
ENTRADA = os.path.join(AQUI, "servidor_entry.py")

# `collect_submodules` importa el paquete para recorrerlo: la raíz tiene que
# estar en el camino de búsqueda del propio PyInstaller, no solo en `pathex`.
import sys  # noqa: E402

if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

#: Bloques de Uvicorn que se cargan por cadena de texto, no por import: sin
#: declararlos aquí, PyInstaller no los ve y el servidor no levanta el socket.
OCULTOS_UVICORN = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
]

# --------------------------------------------------------------------------- #
# Búsqueda semántica (Fase 6)
# --------------------------------------------------------------------------- #

# `fastembed` se importa de forma perezosa dentro de
# `backend/services/semantica.py` (`_obtener_modelo`), así que el análisis
# estático de PyInstaller no lo sigue por el grafo de imports: se declara
# explícitamente junto con sus dependencias nativas.
#
# El modelo de embeddings (~220 MB) **no** se empaqueta: se descarga del hub de
# Hugging Face al primer uso (`~/.cache/huggingface`), que es lo que mantiene el
# instalador ligero y sin estado del equipo del desarrollador.
OCULTOS_SEMANTICA = [
    "fastembed",
    "onnxruntime",
    "tokenizers",
    "huggingface_hub",
]

# `onnxruntime` tiene su propio hook en pyinstaller-hooks-contrib (recoge los
# binarios de `capi/`); `tokenizers` exporta un binario Rust
# (`tokenizers.abi3.so`) que conviene recoger a mano para no depender solo del
# análisis de binarios.
BINARIOS_SEMANTICA = collect_dynamic_libs("tokenizers")

#: Distribuciones cuyos metadatos hacen falta en tiempo de ejecución.
#: FastAPI, Starlette y Uvicorn se inspeccionan a sí mismos con
#: `importlib.metadata`; sin sus metadatos el binario arranca y falla al
#: construir la aplicación. `copy_metadata` devuelve pares `(origen, destino)`,
#: que es el formato que espera `Analysis(datas=…)`.
from PyInstaller.utils.hooks import copy_metadata  # noqa: E402

CON_METADATOS = []
for _distribución in ("fastapi", "starlette", "uvicorn", "pydantic", "pydantic_core"):
    try:
        CON_METADATOS += copy_metadata(_distribución)
    except Exception as _error:  # noqa: BLE001
        print(f"[empaquetado] sin metadatos de {_distribución}: {_error}")

#: Paquetes que se excluyen explícitamente: son interfaz de escritorio y este
#: binario no tiene interfaz.
EXCLUIDOS = [
    "tkinter",
    "customtkinter",
    "matplotlib.backends.backend_tkagg",
    "matplotlib.backends._backend_tk",
    "PIL.ImageTk",
]

#: Recursos que el backend lee **por ruta relativa a su propio archivo**, no por
#: el directorio de trabajo. Hoy es el logo: `reporter.ruta_logo()` lo busca con
#: `Path(__file__).parent / "assets" / "logo" / "logo.png"`, así que dentro del
#: binario tiene que estar en la misma disposición o los reportes PDF salen sin
#: marca (el código lo tolera, pero en silencio).
DATOS = CON_METADATOS + [
    (os.path.join(RAIZ, "assets", "logo", "logo.png"), os.path.join("assets", "logo")),
]

análisis = Analysis(
    [ENTRADA],
    pathex=[RAIZ, AQUI],
    binaries=BINARIOS_SEMANTICA,
    datas=DATOS,
    hiddenimports=OCULTOS_UVICORN + OCULTOS_SEMANTICA + collect_submodules("backend"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUIDOS,
    noarchive=False,
)

pyz = PYZ(análisis.pure)

exe = EXE(
    pyz,
    análisis.scripts,
    [],
    exclude_binaries=True,
    name="datenjager-servidor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

colección = COLLECT(
    exe,
    análisis.binaries,
    análisis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="datenjager-servidor",
)
