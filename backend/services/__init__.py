# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/services/__init__.py - servicios de negocio invocables sin UI

"""Servicios de negocio de DatenJäger.

Cada servicio recibe explícitamente la conexión SQLite y el identificador
de usuario; no lee estado desde una clase de UI.
"""