# Copyright (c) 2024 DatenJäger. All rights reserved.
# scripts/semantico/medir.py - consumo de hardware (latencia, RAM, tiempo)

"""Mide el consumo real de hardware del índice semántico.

Reporta lo que el anteproyecto pide evaluar («consumo de hardware»): tiempo de
carga del modelo, RAM pico del proceso, tiempo de indexado por documento y
latencia de consulta. La RAM pico se lee con `resource.getrusage` (Linux/macOS);
en Windows se omite.

Uso:

    ./venv/bin/python scripts/semantico/medir.py --db /tmp/corpus.db --usuario semantica-test \\
        --consulta "contratos de trabajo en altura"
"""

from __future__ import annotations

import argparse
import sys
import time

from _comun import abrir_base, abrir_indice, resolver_usuario  # noqa: E402
from backend.services import semantica  # noqa: E402


def _ram_pico_mb() -> float | None:
    try:
        import resource  # noqa: F401  (Unix)
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Mide consumo de hardware del índice")
    parser.add_argument("--db", default=None, help="base SQLite (por defecto la del proyecto)")
    parser.add_argument("--usuario", default=None, help="cuenta cuyo corpus se mide")
    parser.add_argument("--indice", default=None, help="archivo de índice (deriva de --db)")
    parser.add_argument("--consulta", default="contratos de trabajo en altura",
                        help="consulta de prueba para medir latencia")
    parser.add_argument("--reindexar", action="store_true",
                        help="reconstruye el índice midiendo el tiempo de indexado")
    args = parser.parse_args()

    conn, cursor = abrir_base(args.db)
    usuario_id, usuario_nombre = resolver_usuario(cursor, args.usuario)
    indice_conn = abrir_indice(args.indice, args.db)

    print("Midiendo consumo de hardware...\n")

    # 1. Carga del modelo (primera vez incluye descarga).
    t0 = time.time()
    semantica._obtener_modelo()
    t_carga = time.time() - t0
    print(f"Carga del modelo          : {t_carga:.2f} s")

    # 2. RAM pico tras cargar el modelo.
    ram_modelo = _ram_pico_mb()
    if ram_modelo is not None:
        print(f"RAM pico (modelo cargado) : {ram_modelo:.1f} MB")

    # 3. Indexado: se reconstruye siempre para cronometrar el coste real.
    t0 = time.time()
    resultado = semantica.indexar_corpus(
        conn, cursor, usuario_id=usuario_id, usuario_nombre=usuario_nombre,
        indice_conn=indice_conn)
    t_idx = time.time() - t0
    n_docs = resultado["documentos"]
    por_doc = t_idx / n_docs if n_docs else float("nan")
    print(f"Indexado                  : {t_idx:.2f} s "
          f"({resultado['fragmentos']} fragmentos, {por_doc:.2f} s/documento)")

    ram_pico = _ram_pico_mb()
    if ram_pico is not None:
        print(f"RAM pico total            : {ram_pico:.1f} MB")

    # 4. Latencia de consulta (10 repeticiones, mediana).
    latencias = []
    for _ in range(10):
        t0 = time.time()
        semantica.buscar(indice_conn, consulta=args.consulta,
                         usuario_id=usuario_id, usuario_nombre=usuario_nombre, k=5)
        latencias.append(time.time() - t0)
    latencias.sort()
    mediana = latencias[len(latencias) // 2]
    print(f"Latencia de consulta      : {mediana*1000:.1f} ms (mediana de 10)")

    conn.close()
    indice_conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())