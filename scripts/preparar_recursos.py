# Copyright (c) 2024 DatenJäger. All rights reserved.
# scripts/preparar_recursos.py — iconos que exige el instalador
# Trazabilidad Jira: SCRUM-54 (DatenJäger — Electron).

"""Prepara los iconos del instalador (Fase 5).

El material de marca del repositorio es un PNG de 500×500 y un `.ico` de un
solo tamaño (256). Ninguno de los dos sirve tal cual para empaquetar: Linux
exige un PNG de **512×512 como mínimo** y Windows agradece un `.ico`
multi-resolución, porque un solo tamaño se ve borroso al escalar en la barra de
tareas.

Los archivos que genera este guion van a ``empaquetado/recursos/``, **no** a
``assets/logo/``: el material de marca original no se toca y el icono del
instalador se regenera siempre igual, que es lo que permite que el
empaquetado sea reproducible y no dependa de un binario editado a mano.

    ./venv/bin/python scripts/preparar_recursos.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

#: Raíz del proyecto.
RAIZ = Path(__file__).resolve().parent.parent

#: Material de marca original.
ORIGEN_PNG = RAIZ / "assets" / "logo" / "logo.png"

#: Carpeta de recursos de empaquetado. `electron-builder.yml` la lee de aquí.
DESTINO = RAIZ / "empaquetado" / "recursos"

#: Lado del PNG para Linux. El mínimo que acepta electron-builder es 512.
LADO_LINUX = 512

#: Tamaños del `.ico` de Windows, de mayor a menor. Windows elige el que
#: necesita en cada sitio (escritorio, barra de tareas, menú de inicio).
TAMANOS_WINDOWS = (256, 128, 64, 48, 32, 16)


def main() -> int:
    if not ORIGEN_PNG.exists():
        print(f"[recursos] falta el logo de origen: {ORIGEN_PNG}", file=sys.stderr)
        return 1

    DESTINO.mkdir(parents=True, exist_ok=True)
    origen = Image.open(ORIGEN_PNG).convert("RGBA")

    icono_png = DESTINO / "icono.png"
    origen.resize((LADO_LINUX, LADO_LINUX), Image.Resampling.LANCZOS).save(icono_png, "PNG")
    print(f"[recursos] {icono_png} ({LADO_LINUX}×{LADO_LINUX})")

    icono_ico = DESTINO / "icono.ico"
    # Pillow deriva cada tamaño del propio original, no de escalar el anterior:
    # encadenar reducciones acumula pérdida.
    origen.save(icono_ico, "ICO", sizes=[(lado, lado) for lado in TAMANOS_WINDOWS])
    tamano = ", ".join(str(lado) for lado in TAMANOS_WINDOWS)
    print(f"[recursos] {icono_ico} ({tamano})")

    return 0


if __name__ == "__main__":
    sys.exit(main())