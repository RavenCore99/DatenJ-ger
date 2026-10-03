# Copyright (c) 2024 DatenJäger. All rights reserved.
# scripts/servidor_entry.py — punto de entrada del backend congelado
# Trazabilidad Jira: SCRUM-54 (DatenJäger — Electron).

"""Punto de entrada del servicio local cuando se empaqueta (Fase 5).

PyInstaller necesita un guion de arranque; no puede tomar `backend/server.py`
como entrada porque ese módulo importa `backend.commands` y solo funcionaría si
el directorio **padre** del paquete estuviera en `sys.path`.

Además, el binario congelado no tiene un directorio de proyecto alrededor: el
programa va dentro del paquete y el estado —base de datos, `.env`, almacenes
cifrados y `config.json`— no puede escribirse ahí. Este guion resuelve las dos
cosas:

* **Datos locales.** Se decide un directorio de datos por usuario y se trabaja
  desde él, de modo que la instalación cree su propio estado y no dependa de
  que el lanzador (Electron) lo pase. `DATENJAGER_DATOS` manda si está definido;
  `electron/backend.js` lo define con el directorio de datos de la aplicación.
* **Base de datos, sin tocar `database.py`.** `conectar_db()` cae en
  `sys.MEIPASS` (atributo del PyInstaller antiguo, hoy inexistente) cuando corre
  congelado y nadie le pasa `--db`: eso revienta con `AttributeError` y además
  apuntaría al directorio temporal de extracción, donde los datos se pierden al
  cerrar. Aquí se inyecta un `--db` por defecto dentro del directorio de datos
  **antes** de delegar en `main()`, así que el camino congelado nunca lo pisa.
  `DATENJAGER_DB` y un `--db` explícito siguen teniendo prioridad.

Ejecución manual del binario:

    ./datenjager-servidor --puerto 8756
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: Nombre del directorio de datos, usado como nombre de la aplicación.
NOMBRE_APLICACION = "DatenJager"

#: Variable que fija el directorio de datos. La define `electron/backend.js`
#: con el directorio de datos de la aplicación; si falta, se deduce por sistema.
VARIABLE_DATOS = "DATENJAGER_DATOS"

#: Nombre del archivo de base de datos dentro del directorio de datos.
NOMBRE_BASE = "base_datos_pdfs.db"


def directorio_de_datos() -> Path:
    """Directorio de datos del usuario, según la convención de cada sistema.

    No se usa `appdirs`/`platformdirs` para no añadir una dependencia por ocho
    líneas. Las rutas son las que espera cada plataforma: `%APPDATA%` en
    Windows, `Application Support` en macOS y `XDG_DATA_HOME` en Linux.
    """
    definido = os.environ.get(VARIABLE_DATOS)
    if definido:
        return Path(definido).expanduser()

    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"
        return Path(base) / NOMBRE_APLICACION

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / NOMBRE_APLICACION

    base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / NOMBRE_APLICACION


def preparar_datos(argumentos: list[str]) -> None:
    """Deja el proceso trabajando en el directorio de datos.

    Se ejecuta en cualquier modo, no solo congelado: así el binario y el guion
    se comportan igual, y una instalación nunca escribe en el directorio del
    programa (que en Linux suele ser de solo lectura).
    """
    datos = directorio_de_datos()
    datos.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chdir(datos)

    # `DATENJAGER_DB` apunta la base a otro sitio en las pruebas y las sondas:
    # si viene definida, manda y no se inyecta nada.
    if os.environ.get("DATENJAGER_DB"):
        return

    if "--db" not in argumentos:
        sys.argv[1:1] = ["--db", str(datos / NOMBRE_BASE)]


def main() -> int:
    preparar_datos(sys.argv[1:])

    # Ejecutado como guion (`python scripts/servidor_entry.py`), `sys.path[0]`
    # es `scripts/`, no la raíz: sin esto el import de `backend` falla. Dentro
    # del binario congelado el paquete ya viaja en el archivo, así que no se
    # toca el camino de búsqueda.
    if not getattr(sys, "frozen", False):
        raiz = str(Path(__file__).resolve().parent.parent)
        if raiz not in sys.path:
            sys.path.insert(0, raiz)

    from backend.server import main as main_servidor

    return main_servidor()


if __name__ == "__main__":
    sys.exit(main())
