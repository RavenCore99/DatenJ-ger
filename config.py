
# 
"""
# Copyright (c) 2024 DatenJäger. All rights reserved.
config.py - Módulo de Configuración
Gestion de configuracion persistente con integridad HMAC-SHA256.
Los valores sensibles de seguridad (2FA, cifrado) se controlan exclusivamente
desde la base de datos — no desde este archivo.
"""

import json
import os
import hmac
import hashlib

# clave interna para verificar integridad del config.json.
# impide que un usuario modifique el archivo manualmente sin ser detectado.
_HMAC_KEY = b"DatenJager_config_integrity_2024_v2"

def _compute_hmac(data: dict) -> str:
    """Calcula HMAC-SHA256 sobre el contenido del config (excluyendo el campo _hmac)."""
    payload = {k: v for k, v in sorted(data.items()) if k != "_hmac"}
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hmac.new(_HMAC_KEY, raw.encode('utf-8'), hashlib.sha256).hexdigest()

def _verify_hmac(data: dict) -> bool:
    """Verifica que el HMAC almacenado coincide con el contenido actual."""
    stored = data.get("_hmac")
    if not stored:
        return False
    expected = _compute_hmac(data)
    return hmac.compare_digest(stored, expected)


class Config:
    """Gestiona configuración persistente con verificación de integridad."""

    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.data = self.load()

    def load(self):
        """Carga configuracion y verifica integridad HMAC.
        Si el archivo no existe, fue alterado o está corrupto → restaura defaults."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                if _verify_hmac(data):
                    # eliminar el campo interno antes de exponer los datos
                    data.pop("_hmac", None)
                    return data
                else:
                    # HMAC inválido: archivo alterado o de versión anterior → defaults
                    print("[Config] Integridad HMAC inválida — restaurando configuración por defecto.")
            except Exception:
                pass
        return self.default()

    def default(self):
        """Configuracion por defecto. Solo preferencias de UI — nunca flags de seguridad."""
        return {
            "theme": "System",
            "window_size": "1100x760",
            "window_maximized": False,
        }

    def save(self):
        """Guarda configuracion con HMAC de integridad."""
        try:
            payload = dict(self.data)
            payload["_hmac"] = _compute_hmac(payload)
            with open(self.config_file, 'w') as f:
                json.dump(payload, f, indent=4)
        except Exception as e:
            print(f"Error guardando config: {e}")

    def get(self, key, default=None):
        """Obtiene valor de configuración."""
        return self.data.get(key, default)

    def set(self, key, value):
        """Establece valor y persiste con HMAC actualizado."""
        self.data[key] = value
        self.save()

# Copyright (c) 2024 DatenJäger. All rights reserved.
