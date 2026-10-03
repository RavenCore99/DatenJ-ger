# Copyright (c) 2024 DatenJäger. All rights reserved.
# scripts/empaquetar_backend.py — congela el backend para el instalador
# Trazabilidad Jira: SCRUM-54 (DatenJäger — Electron).

"""Congela el backend Python con PyInstaller (Fase 5).

Deja el servicio local como un programa autónomo en
``empaquetado/servidor/datenjager-servidor/``, que es lo que
``electron-builder.yml`` mete en el instalador como recurso del paquete.

El objetivo de este guion es que empaquetar sea **una orden** y siempre igual:
las carpetas, la receta y la limpieza viven aquí, no en la cabeza de quien lo
lanza. Por eso existe en vez de documentar la línea de PyInstaller.

    ./venv/bin/python scripts/empaquetar_backend.py

Opciones:

    --sin-limpiar   conserva los archivos intermedios de PyInstaller (para
                    depurar por qué falta un módulo)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

#: Raíz del proyecto. Este archivo vive en `scripts/`.
RAIZ = Path(__file__).resolve().parent.parent

#: Dónde queda el backend congelado. Única carpeta de artefactos de servicio;
#: `electron-builder.yml` la toma de aquí.
SALIDA = RAIZ / "empaquetado" / "servidor"

#: Archivos intermedios de PyInstaller. Separados de la salida para que la
#: carpeta que se empaqueta solo tenga lo que se distribuye.
TEMPORAL = RAIZ / "empaquetado" / "temporal"

#: Receta de PyInstaller. Reproducible y versionada, no una lista de argumentos.
RECETA = RAIZ / "scripts" / "datenjager-servidor.spec"

#: Nombre del programa final, según la plataforma.
NOMBRE_BINARIO = "datenjager-servidor.exe" if sys.platform == "win32" else "datenjager-servidor"


def tamano_legible(ruta: Path) -> str:
    """Tamaño real en disco de un directorio, sin contar dos veces lo mismo.

    PyInstaller deja las bibliotecas nativas compartidas (libmupdf, OpenBLAS)
    en su carpeta y un **enlace simbólico** en la raíz. Seguir los enlaces
    contaría esos 57 MB dos veces y daría un peso que no es el del instalador,
    así que se mide con `lstat` y se descartan los enlaces.
    """
    total = 0
    for entrada in ruta.rglob("*"):
        try:
            informacion = entrada.lstat()
        except OSError:
            continue
        if not entrada.is_symlink() and entrada.is_file():
            total += informacion.st_size

    unidades = ("B", "KB", "MB", "GB")
    indice = 0
    tamano = float(total)
    while tamano >= 1024 and indice < len(unidades) - 1:
        tamano /= 1024
        indice += 1
    return f"{tamano:.0f} B" if indice == 0 else f"{tamano:.1f} {unidades[indice]}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Congela el backend de DatenJäger")
    parser.add_argument(
        "--sin-limpiar",
        action="store_true",
        help="conserva los archivos intermedios de PyInstaller",
    )
    argumentos = parser.parse_args()

    if not RECETA.exists():
        print(f"[empaquetado] falta la receta: {RECETA}", file=sys.stderr)
        return 1

    orden = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--log-level",
        "WARN",
        "--distpath",
        str(SALIDA),
        "--workpath",
        str(TEMPORAL),
        str(RECETA),
    ]
    if not argumentos.sin_limpiar:
        orden.insert(4, "--clean")

    print(f"[empaquetado] congelando el backend con {Path(sys.executable).name}…")
    resultado = subprocess.run(orden, cwd=RAIZ)
    if resultado.returncode != 0:
        print("[empaquetado] PyInstaller falló", file=sys.stderr)
        return resultado.returncode

    binario = SALIDA / "datenjager-servidor" / NOMBRE_BINARIO
    if not binario.exists():
        print(f"[empaquetado] no se encontró el binario esperado: {binario}", file=sys.stderr)
        return 1

    print()
    print(f"[empaquetado] backend congelado: {binario}")
    print(f"[empaquetado] peso: {tamano_legible(SALIDA / 'datenjager-servidor')}")

    # El árbol intermedio no se distribuye y pesa cientos de megas: se retira
    # salvo que se haya pedido conservarlo para depurar.
    if not argumentos.sin_limpiar and TEMPORAL.exists():
        shutil.rmtree(TEMPORAL, ignore_errors=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
