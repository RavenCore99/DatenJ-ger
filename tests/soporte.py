# Copyright (c) 2024 DatenJäger. All rights reserved.
# tests/soporte.py - utilidades compartidas por las pruebas

"""Soporte común de las pruebas: base temporal real y entorno aislado.

Cada prueba trabaja sobre una base SQLite temporal creada con el esquema
real (``database.conectar_db`` acepta una ruta alternativa), de modo que
las pruebas nunca tocan ``base_datos_pdfs.db``.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from database import conectar_db            # noqa: E402
from backend.state import AppState          # noqa: E402
from backend.commands import ComandosDatenJager  # noqa: E402

#: Datos del usuario de pruebas.
USUARIO_ID = 1
USUARIO_NOMBRE = "raven"
SESSION_KEY = b"clave-de-sesion-de-prueba"

#: Contenido mínimo de un PDF de prueba (el servicio no valida el formato).
PDF_MINIMO = b"%PDF-1.4\ncontenido de prueba\n%%EOF\n"

#: Prefijos de los módulos de interfaz que la capa backend no debe cargar.
MODULOS_UI = ("tkinter", "customtkinter")


def assert_sin_tkinter(caso: unittest.TestCase) -> None:
    """Falla si algún módulo de interfaz quedó cargado en el proceso."""
    cargados = [nombre for nombre in sys.modules if nombre.startswith(MODULOS_UI)]
    caso.assertEqual(
        cargados, [],
        f"La capa backend no debe cargar módulos de interfaz: {cargados}",
    )


class BaseBackendTest(unittest.TestCase):
    """Base con una base temporal, estado y fachada de comandos lista."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="datenjager_test_")
        self.db_path = os.path.join(self.tmpdir, "pruebas.db")

        self.conn, self.cursor = conectar_db(self.db_path)
        self.cursor.execute(
            "INSERT INTO Usuarios (nombre, contrasena, fecha_creacion) VALUES (?, ?, ?)",
            (USUARIO_NOMBRE, "pbkdf2:sal:hash", "2026-01-01T00:00:00"),
        )
        self.conn.commit()

        self.state = AppState(
            conn=self.conn,
            cursor=self.cursor,
            db_lock=threading.Lock(),
            config=None,
            tema="Light",
        )
        self.comandos = ComandosDatenJager(self.state)
        self.comandos.iniciar_sesion(USUARIO_ID, USUARIO_NOMBRE, SESSION_KEY)

    def tearDown(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ------------------------------------------------------------------ #
    # Datos de sesión de la prueba
    # ------------------------------------------------------------------ #

    @property
    def usuario_id(self) -> int:
        return USUARIO_ID

    @property
    def usuario_nombre(self) -> str:
        return USUARIO_NOMBRE

    # ------------------------------------------------------------------ #
    # Utilidades
    # ------------------------------------------------------------------ #

    def ruta_temporal(self, nombre: str) -> str:
        """Ruta dentro del directorio temporal de la prueba."""
        return os.path.join(self.tmpdir, nombre)

    def crear_pdf(self, nombre: str = "documento.pdf", contenido: bytes | None = None) -> str:
        """Escribe un PDF de prueba en disco y devuelve su ruta."""
        ruta = self.ruta_temporal(nombre)
        with open(ruta, "wb") as archivo:
            archivo.write(contenido if contenido is not None else PDF_MINIMO)
        return ruta

    def eventos(self) -> list[str]:
        """Acciones registradas en auditoría, en orden de inserción."""
        self.cursor.execute("SELECT accion FROM Auditoria ORDER BY id")
        return [fila[0] for fila in self.cursor.fetchall()]