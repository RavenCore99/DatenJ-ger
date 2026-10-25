#!/usr/bin/env python3
"""Ejecuta la suite unittest y reporta el avance test a test.

Uso:
    DATENJAGER_PROGRESO=/ruta/progreso.txt \
        python scripts/validacion/runner_progreso.py




"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

_ARCHIVO = None
_TOTAL = 0


class ResultadoConProgreso(unittest.TextTestResult):
    """Resultado de unittest que escribe el avance en un archivo."""

    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self._hechos = 0
        self._reportar("")

    def _reportar(self, actual: str) -> None:
        if _ARCHIVO is None:
            return
        fallos = len(self.failures) + len(self.errors) + len(self.unexpectedSuccesses)
        omitidos = len(self.skipped)
        ok = max(0, self._hechos - fallos - omitidos)
        actual = actual.replace("\t", " ").replace("\n", " ")
        _ARCHIVO.seek(0)
        _ARCHIVO.truncate()
        _ARCHIVO.write(
            f"{self._hechos}/{_TOTAL}\t{ok}\t{fallos}\t{omitidos}\t{actual}\n"
        )
        _ARCHIVO.flush()

    def startTest(self, test) -> None:  # noqa: N802 - API de unittest
        super().startTest(test)
        self._reportar(test.id())

    def stopTest(self, test) -> None:  # noqa: N802 - API de unittest
        super().stopTest(test)
        self._hechos += 1
        self._reportar("")


def main() -> int:
    global _ARCHIVO, _TOTAL

    ruta = os.environ.get("DATENJAGER_PROGRESO")
    if ruta:
        _ARCHIVO = open(ruta, "w", encoding="utf-8")

    try:
        suite = unittest.TestLoader().discover("tests", top_level_dir=".")
    except Exception as exc:  # pragma: no cover - solo diagnóstico
        print(f"ERROR al descubrir las pruebas: {exc}", file=sys.stderr)
        if _ARCHIVO is not None:
            _ARCHIVO.close()
        return 2

    _TOTAL = suite.countTestCases()
    if _ARCHIVO is not None:
        _ARCHIVO.seek(0)
        _ARCHIVO.truncate()
        _ARCHIVO.write(f"0/{_TOTAL}\t0\t0\t0\t\n")
        _ARCHIVO.flush()

    resultado = unittest.TextTestRunner(
        verbosity=0, resultclass=ResultadoConProgreso
    ).run(suite)

    if _ARCHIVO is not None:
        _ARCHIVO.close()

    return 0 if resultado.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
