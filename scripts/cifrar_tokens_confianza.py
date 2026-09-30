# Copyright (c) 2024 DatenJäger. All rights reserved.
# scripts/cifrar_tokens_confianza.py - traslada los tokens en claro de config.json

"""Migra los tokens de confianza de `config.json` al almacén cifrado.

Uso:

    ./venv/bin/python scripts/cifrar_tokens_confianza.py             # traslada y limpia
    ./venv/bin/python scripts/cifrar_tokens_confianza.py --simular   # solo informa

Los tokens quedan cifrados en `tokens_confianza/`. Los que se hayan movido se
retiran de `config.json` (con copia previa `config.json.respaldo`), para que no
sigan en claro en un archivo que se comparte con las preferencias.

Si el almacén no tiene clave, se crea una con permisos 0600. Los tokens que se
guarden con esa clave solo se pueden descifrar en este equipo: si se pierde
`tokens_confianza/llave.bin`, los dispositivos de confianza dejan de serlo y el
sistema vuelve a pedir el segundo factor (no se pierde ninguna cuenta).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from backend import tokens  # noqa: E402
from config import Config  # noqa: E402

RESPALDO = "config.json.respaldo"


def main() -> int:
    parser = argparse.ArgumentParser(description="Cifra los tokens de confianza")
    parser.add_argument("--simular", action="store_true", help="no escribe cambios")
    argumentos = parser.parse_args()

    config = Config()
    guardados = config.get("trust_tokens", {}) or {}

    if not guardados:
        print("No hay tokens de confianza en config.json: nada que migrar.")
        return 0

    print(f"Tokens en claro encontrados: {len(guardados)}")

    if argumentos.simular:
        for usuario in sorted(guardados):
            print(f"  - {usuario} (se cifraría en {tokens.NOMBRE_DIRECTORIO}/)")
        return 0

    resumen = tokens.migrar_desde_config(RAIZ, guardados)
    if not resumen["migrados"]:
        print("Ningún token utilizable: config.json queda intacto.")
        return 1

    ruta_config = Path(config.config_file)
    if ruta_config.exists():
        shutil.copy2(ruta_config, ruta_config.parent / RESPALDO)
        print(f"Copia de seguridad: {RESPALDO}")

    # Solo se retiran los que ya están cifrados en el almacén.
    restantes = {u: t for u, t in guardados.items() if u not in resumen["migrados"]}
    config.set("trust_tokens", restantes)
    config.save()  # recalcula el HMAC de integridad
    print(f"Cifrados: {len(resumen['migrados'])} -> {tokens.NOMBRE_DIRECTORIO}/")
    for usuario in resumen["migrados"]:
        print(f"  - {usuario}")
    if restantes:
        print(f"Sin migrar (no eran tokens válidos): {', '.join(sorted(restantes))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())