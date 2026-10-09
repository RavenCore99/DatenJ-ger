# Copyright (c) 2024 DatenJäger. All rights reserved.
# scripts/semantico/buscar.py - consulta por significado

"""Busca en el índice semántico y muestra los fragmentos más parecidos.

Uso:

    ./venv/bin/python scripts/semantico/buscar.py --db /tmp/corpus.db --usuario semantica-test \\
        "contratos de trabajo en altura"
"""

from __future__ import annotations

import argparse
import sys

from _comun import abrir_base, abrir_indice, resolver_usuario  # noqa: E402
from backend.services import semantica  # noqa: E402


def _metadatos(cursor, documento_id: int) -> dict:
    cursor.execute(
        """
        SELECT p.nombre, pe.cedula, pe.nombres, pe.empresa
        FROM PDFs p
        LEFT JOIN Personas pe ON p.persona_id = pe.id
        WHERE p.id = ?
        """,
        (documento_id,),
    )
    fila = cursor.fetchone()
    if not fila:
        return {"nombre": f"#{documento_id}", "cedula": "", "titular": "", "empresa": ""}
    return {
        "nombre": fila[0],
        "cedula": fila[1] or "",
        "titular": fila[2] or "",
        "empresa": fila[3] or "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Búsqueda semántica")
    parser.add_argument("--db", default=None, help="base SQLite (por defecto la del proyecto)")
    parser.add_argument("--usuario", default=None, help="cuenta cuyo corpus se consulta")
    parser.add_argument("--indice", default=None, help="archivo de índice (deriva de --db)")
    parser.add_argument("-k", type=int, default=5, help="resultados a mostrar (default 5)")
    parser.add_argument("consulta", help="texto de la consulta")
    args = parser.parse_args()

    conn, cursor = abrir_base(args.db)
    usuario_id, usuario_nombre = resolver_usuario(cursor, args.usuario)
    indice_conn = abrir_indice(args.indice, args.db)

    resultados = semantica.buscar(
        indice_conn,
        consulta=args.consulta,
        usuario_id=usuario_id,
        usuario_nombre=usuario_nombre,
        k=args.k,
    )

    print(f"Consulta: «{args.consulta}»  ({len(resultados)} resultado(s))\n")
    if not resultados:
        print("  (sin resultados: ¿índice vacío? corre indexar.py)")
        return 0

    for i, r in enumerate(resultados, 1):
        meta = _metadatos(cursor, r["documento_id"])
        snippet = " ".join(r["texto"].split())
        if len(snippet) > 200:
            snippet = snippet[:200] + "…"
        print(f"{i}. [score {r['score']:.3f}] {meta['nombre']}")
        if meta["titular"]:
            print(f"   titular: {meta['titular']} · cedula {meta['cedula']}")
        if meta["empresa"]:
            print(f"   empresa: {meta['empresa']}")
        print(f"   «{snippet}»\n")

    conn.close()
    indice_conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())