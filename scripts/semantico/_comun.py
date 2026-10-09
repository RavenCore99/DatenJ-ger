# Copyright (c) 2024 DatenJäger. All rights reserved.
# scripts/semantico/_comun.py - utilidades compartidas de los CLI de evaluación

"""Helpers compartidos por los scripts de evaluación semántica.

Resolución de usuario y apertura de la base/índice, con el mismo criterio de
`scripts/exportar_inventario.py`: los scripts corren en el mismo equipo y sobre
el mismo SQLite que la aplicación, así que adoptan la cuenta indicada en lugar
de pedir credenciales.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ))

from database import conectar_db  # noqa: E402
from backend.services import semantica  # noqa: E402


def usuarios_disponibles(cursor):
    cursor.execute("SELECT id, nombre FROM Usuarios ORDER BY nombre")
    return cursor.fetchall()


def resolver_usuario(cursor, nombre: str | None) -> tuple[int, str]:
    """Devuelve ``(id, nombre)`` de la cuenta pedida, o falla explicando qué hay."""
    disponibles = usuarios_disponibles(cursor)

    if not disponibles:
        raise SystemExit("La base no tiene cuentas registradas.")

    if nombre:
        for usuario_id, usuario_nombre in disponibles:
            if usuario_nombre.lower() == nombre.lower():
                return usuario_id, usuario_nombre
        nombres = ", ".join(n for _id, n in disponibles)
        raise SystemExit(f"No existe '{nombre}'. Cuentas: {nombres}")

    if len(disponibles) > 1:
        nombres = ", ".join(n for _id, n in disponibles)
        raise SystemExit(f"Hay {len(disponibles)} cuentas; indica --usuario. {nombres}")

    return disponibles[0]


def abrir_base(db: str | None):
    """Abre la base principal (argumento, `DATENJAGER_DB` o la del proyecto)."""
    if db:
        ruta = str(db)
    else:
        ruta = os.environ.get("DATENJAGER_DB") or str(RAIZ / "base_datos_pdfs.db")
    if not Path(ruta).exists():
        raise SystemExit(f"No se encontró la base en {ruta}. Usa --db.")
    return conectar_db(ruta)


def abrir_indice(indice: str | None, db: str | None):
    """Abre (o crea) el índice semántico, derivado de la base si no se indica."""
    base = db or os.environ.get("DATENJAGER_DB") or str(RAIZ / "base_datos_pdfs.db")
    ruta = indice or semantica.ruta_indice(base)
    return semantica.conectar_indice(ruta)