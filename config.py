
import json
import os
import hmac
import hashlib
# Copyright (c) 2024 DatenJäger. All rights reserved.

def _load_env_file(env_path: str = ".env") -> None:
    """Carga variables desde un archivo .env sencillo sin dependencias externas."""
    if not os.path.exists(env_path):
        return

    try:
        with open(env_path, "r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        # si falla la carga del .env, la app sigue con variables ya presentes
        pass


_load_env_file()

# config.py - configuracion del sistema
# guarda preferencias en json con verificacion hmac

# clave para verificar que no manipulen el json
_HMAC_KEY = b"DatenJager_config_integrity_2024_v2"

def _compute_hmac(data: dict) -> str:
    # calcula hmac del contenido
    payload = {k: v for k, v in sorted(data.items()) if k != "_hmac"}
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hmac.new(_HMAC_KEY, raw.encode('utf-8'), hashlib.sha256).hexdigest()

def _verify_hmac(data: dict) -> bool:
    # verifica hmac
    stored = data.get("_hmac")
    if not stored:
        return False
    expected = _compute_hmac(data)
    return hmac.compare_digest(stored, expected)


class Config:
    # maneja la config con verificacion de integridad

    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.data = self.load()

    def load(self):
        # Carga configuracion y verifica integridad HMAC.
        # Si el archivo no existe, fue alterado o está corrupto → restaura defaults.
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                if _verify_hmac(data):
                    # quitar el hmac antes de devolver
                    data.pop("_hmac", None)
                    return data
                else:
                    # hmac invalido, volver a defaults
                    print("[Config] Integridad HMAC inválida — restaurando configuración por defecto.")
            except Exception:
                pass
        return self.default()

    def default(self):
        # valores por defecto
        return {
            "theme": "System",
            "window_size": "1100x760",
            "window_maximized": False,
            "2fa_trust_hours": 0,
            "trust_tokens": {},
            "session_timeout_minutes": 10,
        }

    def save(self):
        # guarda con hmac
        try:
            payload = dict(self.data)
            payload["_hmac"] = _compute_hmac(payload)
            with open(self.config_file, 'w') as f:
                json.dump(payload, f, indent=4)
        except Exception as e:
            print(f"Error guardando config: {e}")

    def get(self, key, default=None):
        # obtener valor
        return self.data.get(key, default)

    def set(self, key, value):
        # setear valor y guardar
        self.data[key] = value
        self.save()

# Copyright (c) 2024 DatenJäger. All rights reserved.
