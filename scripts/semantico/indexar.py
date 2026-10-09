# Copyright (c) 2024 DatenJäger. All rights reserved.
# scripts/semantico/indexar.py - construir el índice semántico

"""Construye (o reconstruye) el índice semántico de una cuenta.

Descifra cada documento, extrae el texto, lo trocea y guarda fragmento cifrado
+ embedding en el índice SQLite. Es idempotente: vuelve a indexar al usuario
indicado desde cero.

Uso:

    ./venv/bin/python scripts/semantico/indexar.py --db /tmp/corpus.db --usuario semantica-test
    ./venv/bin/python scripts/semantico/indexar.py --db /tmp/corpus.db --usuario semantica-test --indice /tmp/indice.db
"""

from __future__ import annotations

import argparse
import sys

from _comun import abrir_base, abrir_indice, resolver_usuario  # noqa: E402
from backend.services import semantica  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Construye el índice semántico")
    parser.add_argument("--db", default=None, help="base SQLite (por defecto la del proyecto)")
    parser.add_argument("--usuario", default=None, help="cuenta cuyo corpus se indexa")
    parser.add_argument("--indice", default=None, help="archivo de índice (deriva de --db)")
    args = parser.parse_args()

    conn, cursor = abrir_base(args.db)
    usuario_id, usuario_nombre = resolver_usuario(cursor, args.usuario)
    indice_conn = abrir_indice(args.indice, args.db)

    print(f"Indexando documentos de «{usuario_nombre}» (id {usuario_id})...")
    resultado = semantica.indexar_corpus(
        conn,
        cursor,
        usuario_id=usuario_id,
        usuario_nombre=usuario_nombre,
        indice_conn=indice_conn,
        registrar_progreso=print,
    )

    print("\nÍndice construido:")
    print(f"  documentos indexados : {resultado['documentos']}")
    print(f"  fragmentos           : {resultado['fragmentos']}")
    print(f"  caracteres extraídos : {resultado['caracteres']}")
    print(f"  tiempo               : {resultado['segundos']} s")
    print(f"  modelo               : {resultado['modelo']}")

    conn.close()
    indice_conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())