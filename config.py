
# : utf-8 -*-
"""
# Copyright (c) 2024 DatenJäger. All rights reserved.
config.py - Módulo de Configuración
Gestiona configuración persistente para el JSON generado
"""

import json
import os

class Config:
    """Gestiona configuración persistente"""

    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.data = self.load()

    def load(self):
        """Carga configuración"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return self.default()
        return self.default()

    def default(self):
        """Configuración por defecto"""
        return {
            "theme": "System",
            "fullscreen": False,
            "window_size": "1000x700",
            "encryption_enabled": True,
            "2fa_enabled": True
        }

    def save(self):
        """Guarda configuración"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error guardando config: {e}")

    def get(self, key, default=None):
        """Obtiene valor"""
        return self.data.get(key, default)

    def set(self, key, value):
        """Establece valor"""
        self.data[key] = value
        self.save()

# Copyright (c) 2024 DatenJäger. All rights reserved.