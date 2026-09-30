# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/state.py - estado de aplicación consultable

"""Capa de estado de aplicación.

Hasta ahora la sesión, el tema, la configuración y la temporización de
inactividad vivían como atributos implícitos de la clase principal de
``main.py`` (``self.usuario_actual``, ``self._session_key``,
``self.config``...). Este módulo los vuelve explícitos en un objeto único
que la interfaz y el servidor local consultan de la misma forma.

La clase **no** importa Tkinter: el tema se guarda como dato, y es la
interfaz la que lo aplica a CustomTkinter. La conexión de base de datos se
recibe ya creada (``database.conectar_db``) para no cambiar el ciclo de
vida actual.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

#: Minutos de inactividad antes de cerrar la sesión, si la configuración no
#: trae un valor propio.
TIMEOUT_INACTIVIDAD_DEFECTO = 10


@dataclass
class SesionUsuario:
    """Datos del usuario autenticado en la sesión activa."""

    usuario_id: Optional[int] = None
    nombre: Optional[str] = None
    #: Clave de sesión derivada de la contraseña (AES), no se persiste.
    session_key: Any = None

    @property
    def activa(self) -> bool:
        return self.usuario_id is not None

    def limpiar(self) -> None:
        self.usuario_id = None
        self.nombre = None
        self.session_key = None


class AppState:
    """Estado consultable de la aplicación.

    Args:
        conn: conexión SQLite activa.
        cursor: cursor de esa conexión.
        db_lock: candado que serializa el acceso a la conexión entre hilos.
        config: instancia de ``config.Config``.
        tema: modo de apariencia activo ("Light", "Dark" o "System").
    """

    def __init__(self, conn=None, cursor=None, db_lock=None, config=None, tema: str = "System"):
        self.conn = conn
        self.cursor = cursor
        self.db_lock = db_lock
        self.config = config
        self.tema = tema
        self.sesion = SesionUsuario()

    # ------------------------------------------------------------------ #
    # Sesión
    # ------------------------------------------------------------------ #

    @property
    def usuario_actual(self) -> Optional[int]:
        """Id del usuario autenticado (``None`` si no hay sesión)."""
        return self.sesion.usuario_id

    @usuario_actual.setter
    def usuario_actual(self, valor: Optional[int]) -> None:
        self.sesion.usuario_id = valor

    @property
    def usuario_nombre(self) -> Optional[str]:
        """Nombre del usuario autenticado."""
        return self.sesion.nombre

    @usuario_nombre.setter
    def usuario_nombre(self, valor: Optional[str]) -> None:
        self.sesion.nombre = valor

    @property
    def session_key(self) -> Any:
        """Clave de sesión derivada de la contraseña."""
        return self.sesion.session_key

    @session_key.setter
    def session_key(self, valor: Any) -> None:
        self.sesion.session_key = valor

    @property
    def is_authenticated(self) -> bool:
        """Indica si hay una sesión de usuario activa."""
        return self.sesion.activa

    def iniciar_sesion(
        self,
        usuario_id: int,
        nombre: str,
        session_key: Any = None,
    ) -> None:
        """Registra la sesión del usuario autenticado."""
        self.sesion.usuario_id = usuario_id
        self.sesion.nombre = nombre
        self.sesion.session_key = session_key

    def cerrar_sesion(self) -> None:
        """Descarta los datos de la sesión activa."""
        self.sesion.limpiar()

    # ------------------------------------------------------------------ #
    # Configuración y temporización
    # ------------------------------------------------------------------ #

    def minutos_inactividad(self) -> int:
        """Minutos de inactividad antes del cierre automático de sesión."""
        if self.config is None:
            return TIMEOUT_INACTIVIDAD_DEFECTO
        try:
            return int(self.config.get("session_timeout_minutes", TIMEOUT_INACTIVIDAD_DEFECTO))
        except (TypeError, ValueError):
            return TIMEOUT_INACTIVIDAD_DEFECTO

    def segundos_inactividad(self) -> int:
        """El mismo intervalo expresado en segundos."""
        return self.minutos_inactividad() * 60

    def obtener(self, clave: str, defecto: Any = None) -> Any:
        """Lee una preferencia de la configuración activa."""
        if self.config is None:
            return defecto
        return self.config.get(clave, defecto)

    def guardar(self, clave: str, valor: Any) -> None:
        """Persiste una preferencia en la configuración activa."""
        if self.config is not None:
            self.config.set(clave, valor)

    def cambiar_tema(self, tema: str, persistir: bool = True) -> None:
        """Actualiza el tema activo; la interfaz decide cómo aplicarlo.

        Args:
            tema: "Light", "Dark" o "System".
            persistir: guardar el tema en la configuración.
        """
        self.tema = tema
        if persistir:
            self.guardar("theme", tema)