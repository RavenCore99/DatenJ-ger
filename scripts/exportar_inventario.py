# Copyright (c) 2024 DatenJäger. All rights reserved.
# scripts/exportar_inventario.py - reporte de inventario sin abrir la aplicación

"""Genera el reporte de inventario documental desde la línea de comandos.

Uso:

    ./venv/bin/python scripts/exportar_inventario.py --listar
    ./venv/bin/python scripts/exportar_inventario.py --usuario Raven
    ./venv/bin/python scripts/exportar_inventario.py --usuario Raven --formato csv
    ./venv/bin/python scripts/exportar_inventario.py --usuario Raven --destino /tmp/inv.pdf

El PDF sale con la identidad del proyecto —portada con el logo, tarjetas de
resumen, distribución por empresa, tabla de inventario y gráfico por empresa—,
reutilizando `reporter.ReporteInventario`, que es el mismo generador que usa la
aplicación. No hay una segunda plantilla que se desincronice.

**Alcance y honestidad sobre el acceso.** El script corre en el mismo equipo y
sobre el mismo archivo SQLite que la aplicación, así que adopta la sesión del
usuario indicado en lugar de pedir credenciales: quien puede leer el archivo
puede ejecutarlo, y exigir la contraseña aquí daría una sensación de control que
no aporta nada. Lo que **no** hace es descifrar documentos: el reporte solo usa
metadatos (nombre, tamaño, fecha, titular y empresa), que no están cifrados.
Abrir un PDF sigue exigiendo la contraseña del usuario y el flujo de la
aplicación.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from backend.commands import ComandosDatenJager  # noqa: E402
from backend.services import reportes  # noqa: E402
from backend.state import AppState  # noqa: E402
from database import conectar_db  # noqa: E402


def ruta_base_por_defecto() -> Path:
    """Base del proyecto, salvo que `DATENJAGER_DB` apunte a otra."""
    return Path(os.environ.get("DATENJAGER_DB") or (RAIZ / "base_datos_pdfs.db"))


def usuarios_disponibles(cursor) -> list[tuple[int, str]]:
    cursor.execute("SELECT id, nombre FROM Usuarios ORDER BY nombre")
    return cursor.fetchall()


def resolver_usuario(cursor, nombre: str | None) -> tuple[int, str]:
    """Devuelve `(id, nombre)` del usuario pedido, o falla explicando qué hay.

    Sin `--usuario` se resuelve solo cuando la base tiene exactamente una cuenta;
    con varias, elegir por ti sería adivinar.
    """
    disponibles = usuarios_disponibles(cursor)

    if not disponibles:
        raise SystemExit("La base no tiene ninguna cuenta registrada: no hay inventario que reportar.")

    if nombre:
        for usuario_id, usuario_nombre in disponibles:
            if usuario_nombre.lower() == nombre.lower():
                return usuario_id, usuario_nombre
        nombres = ", ".join(nombre for _id, nombre in disponibles)
        raise SystemExit(f"No existe el usuario '{nombre}'. Cuentas disponibles: {nombres}")

    if len(disponibles) > 1:
        nombres = ", ".join(nombre for _id, nombre in disponibles)
        raise SystemExit(
            f"La base tiene {len(disponibles)} cuentas; indica cuál con --usuario. "
            f"Disponibles: {nombres}")

    return disponibles[0]


def destino_por_defecto(usuario: str, formato: str) -> Path:
    sello = datetime.now().strftime("%Y%m%d-%H%M")
    return Path.cwd() / f"reporte_inventario_{usuario}_{sello}.{formato}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera el reporte de inventario documental de DatenJäger")
    parser.add_argument("--db", default=None,
                        help="base SQLite alternativa (por defecto la del proyecto)")
    parser.add_argument("--usuario", default=None,
                        help="cuenta cuyo inventario se reporta")
    parser.add_argument("--destino", default=None,
                        help="ruta del reporte a escribir")
    parser.add_argument("--formato", default="pdf", choices=list(reportes.FORMATOS),
                        help="formato del reporte (por defecto pdf)")
    parser.add_argument("--listar", action="store_true",
                        help="solo muestra las cuentas disponibles")
    argumentos = parser.parse_args()

    db_path = Path(argumentos.db) if argumentos.db else ruta_base_por_defecto()
    if not db_path.exists():
        raise SystemExit(f"No se encontró la base en {db_path}. Usa --db para indicar otra.")

    conn, cursor = conectar_db(str(db_path))
    try:
        if argumentos.listar:
            cuentas = usuarios_disponibles(cursor)
            if not cuentas:
                print("La base no tiene cuentas registradas.")
                return 0
            print(f"Cuentas en {db_path}:")
            for usuario_id, nombre in cuentas:
                cursor.execute(
                    "SELECT COUNT(*) FROM PDFs WHERE usuario_id = ?", (usuario_id,))
                print(f"  - {nombre} ({cursor.fetchone()[0]} documento(s))")
            return 0

        usuario_id, usuario_nombre = resolver_usuario(cursor, argumentos.usuario)

        # La sesión se adopta: ver la nota de alcance del encabezado del módulo.
        state = AppState(conn=conn, cursor=cursor, db_lock=threading.Lock())
        comandos = ComandosDatenJager(state)
        state.iniciar_sesion(usuario_id, usuario_nombre)

        destino = Path(argumentos.destino) if argumentos.destino else destino_por_defecto(
            usuario_nombre, argumentos.formato)
        destino.parent.mkdir(parents=True, exist_ok=True)

        escritos = comandos.exportar_inventario(str(destino), argumentos.formato)

        metricas = comandos.estadisticas_dashboard()
        print(f"Reporte {argumentos.formato.upper()} de «{usuario_nombre}»: {escritos}")
        print(f"  Documentos: {metricas['total_pdfs']}  ·  "
              f"Personas: {metricas['total_personas']}  ·  "
              f"Empresas: {metricas['total_empresas']}  ·  "
              f"Volumen: {metricas['total_size_str']}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())