# Copyright (c) 2024 DatenJäger. All rights reserved.
# scripts/semantico/clasificar.py - evaluación de la clasificación por reglas

"""Evalúa la línea base de clasificación automática (Uso B) sobre un corpus.

A cada documento se le extrae el texto (descifrando), se clasifica con las
reglas de palabras clave y se compara contra las etiquetas de referencia
(`corpus_etiquetas.json`). Reporta exactitud global, y precisión/exhaustividad
por categoría, más la matriz de confusión.

Uso:

    ./venv/bin/python scripts/semantico/clasificar.py \\
        --db /tmp/corpus_semantico.db --usu semantica-test \\
        --etiquetas /tmp/corpus_semantico.etiquetas.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict

from _comun import abrir_base, resolver_usuario  # noqa: E402
from backend.services import documentos  # noqa: E402
from backend.services import semantica  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Evalúa la clasificación por reglas")
    parser.add_argument("--db", default=None, help="base SQLite (por defecto la del proyecto)")
    parser.add_argument("--usuario", default=None, help="cuenta cuyo corpus se clasifica")
    parser.add_argument("--etiquetas", required=True,
                        help="JSON documento_id -> categoría de referencia")
    args = parser.parse_args()

    conn, cursor = abrir_base(args.db)
    usuario_id, usuario_nombre = resolver_usuario(cursor, args.usuario)

    with open(args.etiquetas, encoding="utf-8") as f:
        etiquetas = json.load(f)

    cursor.execute("SELECT id FROM PDFs WHERE usuario_id = ? ORDER BY id", (usuario_id,))
    ids = [fila[0] for fila in cursor.fetchall()]

    aciertos = 0
    reales: Counter = Counter()
    predichas: Counter = Counter()
    confusion: dict[str, Counter] = defaultdict(Counter)

    for documento_id in ids:
        real = etiquetas.get(str(documento_id), "sin_clasificar")
        try:
            pdf_bytes, _ = documentos.leer_documento(
                conn, cursor, usuario_id=usuario_id, documento_id=documento_id,
                usuario_nombre=usuario_nombre, registrar_apertura=False)
            texto = semantica.texto_pdf(pdf_bytes)
        except Exception as exc:  # noqa: BLE001
            print(f"  [omitido] documento {documento_id}: {exc}")
            continue

        predicha = semantica.clasificar_texto(texto)
        reales[real] += 1
        predichas[predicha] += 1
        confusion[real][predicha] += 1
        if predicha == real:
            aciertos += 1

    total = sum(reales.values())
    exactitud = aciertos / total if total else 0.0

    print(f"Documentos evaluados: {total}")
    print(f"Exactitud global    : {exactitud:.1%}\n")

    categorias = sorted(set(reales) | set(predichas))
    print(f"{'categoría':26} {'real':>5} {'pred':>5} {'prec':>7} {'rec':>7}")
    for cat in categorias:
        vp = confusion[cat][cat]
        prec = vp / predichas[cat] if predichas[cat] else 0.0
        rec = vp / reales[cat] if reales[cat] else 0.0
        print(f"{cat:26} {reales[cat]:>5} {predichas[cat]:>5} {prec:>7.1%} {rec:>7.1%}")

    print("\nMatriz de confusión (filas = real, columnas = predicha):")
    print(f"{'':26}" + "".join(f"{c[:18]:>20}" for c in categorias))
    for r in categorias:
        print(f"{r:26}" + "".join(f"{confusion[r][c]:>20}" for c in categorias))

    # Diagnóstico de reglas que nunca aciertan (útil para ajustar la línea base).
    sin_acierto = [c for c in categorias if confusion[c][c] == 0 and reales[c] > 0]
    if sin_acierto:
        print(f"\nCategorías con cero aciertos (revisar claves): {', '.join(sin_acierto)}")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())