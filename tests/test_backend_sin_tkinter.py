# Copyright (c) 2024 DatenJäger. All rights reserved.
# tests/test_backend_sin_tkinter.py - la capa backend corre sin interfaz

"""Pruebas de aislamiento: el backend funciona sin Tkinter ni pantalla.

Se ejecutan en un procesos hijo con ``DISPLAY`` y ``WAYLAND_DISPLAY``
eliminados del entorno, de modo que un import accidental de
``customtkinter`` (o cualquier intento de abrir una ventana) falla de
forma visible en lugar de pasar desapercibido.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

#: Módulos cuyo import debe bastar para ejercitar todo el backend.
MODULOS_BACKEND = (
    "backend.errors",
    "backend.state",
    "backend.commands",
    "backend.services.auditoria",
    "backend.services.autenticacion",
    "backend.services.documentos",
    "backend.services.personas",
    "backend.services.reportes",
    "chatbot",
)

GUION = textwrap.dedent(
    """
    import os, sys, threading, tempfile
    sys.path.insert(0, {raiz!r})

    import importlib
    for nombre in {modulos!r}:
        importlib.import_module(nombre)

    from database import conectar_db
    from backend.state import AppState
    from backend.commands import ComandosDatenJager

    carpeta = tempfile.mkdtemp(prefix="datenjager_sin_ui_")
    conn, cursor = conectar_db(os.path.join(carpeta, "t.db"))
    cursor.execute(
        "INSERT INTO Usuarios (nombre, contrasena, fecha_creacion) VALUES (?, ?, ?)",
        ("raven", "pbkdf2:sal:hash", "2026-01-01T00:00:00"),
    )
    conn.commit()

    comandos = ComandosDatenJager(
        AppState(conn=conn, cursor=cursor, db_lock=threading.Lock())
    )
    comandos.iniciar_sesion(1, "raven", b"k")

    ruta = os.path.join(carpeta, "doc.pdf")
    with open(ruta, "wb") as archivo:
        archivo.write(b"%PDF-1.4\\nprueba\\n%%EOF\\n")

    creado = comandos.agregar_documento(ruta, "prueba", "1", "Titular", "Empresa")
    datos, nombre = comandos.abrir_documento(creado["id"])
    assert datos.startswith(b"%PDF"), "el documento no se descifro"
    assert len(comandos.listar_documentos()) == 1

    interfaz = sorted(m for m in sys.modules if m.startswith(("tkinter", "customtkinter")))
    print("UI_CARGADA=" + ",".join(interfaz))
    print("PANELES=1")
    """
)


class TestBackendSinTkinter(unittest.TestCase):

    def test_backend_completo_sin_display(self):
        entorno = dict(os.environ)
        entorno.pop("DISPLAY", None)
        entorno.pop("WAYLAND_DISPLAY", None)
        entorno["QT_QPA_PLATFORM"] = "offscreen"

        guion = GUION.format(raiz=str(RAIZ), modulos=list(MODULOS_BACKEND))
        resultado = subprocess.run(
            [sys.executable, "-c", guion],
            cwd=str(RAIZ),
            env=entorno,
            capture_output=True,
            text=True,
            timeout=120,
        )

        self.assertEqual(
            resultado.returncode, 0,
            f"El backend falló sin pantalla:\n{resultado.stdout}\n{resultado.stderr}",
        )
        self.assertIn("PANELES=1", resultado.stdout)
        self.assertIn("UI_CARGADA=", resultado.stdout)
        cargados = resultado.stdout.split("UI_CARGADA=")[1].splitlines()[0].strip()
        self.assertEqual(cargados, "", f"Se cargaron módulos de interfaz: {cargados}")

    def test_ningun_modulo_backend_importa_tkinter(self):
        """Ningún archivo de backend/ importa la interfaz directamente."""
        prohibidos = ("import tkinter", "from tkinter", "import customtkinter", "from customtkinter")

        for archivo in (RAIZ / "backend").rglob("*.py"):
            contenido = archivo.read_text(encoding="utf-8")
            for linea in contenido.splitlines():
                limpia = linea.strip()
                if limpia.startswith("#"):
                    continue
                for prohibido in prohibidos:
                    self.assertFalse(
                        limpia.startswith(prohibido),
                        f"{archivo.name} importa interfaz: {limpia}",
                    )

    def test_los_modulos_de_servicio_no_importan_componentes_de_ui(self):
        """Los servicios tampoco deben depender de los módulos de pantalla."""
        prohibidos = ("ui_components", "pdf_manager", "personas.py", "audit.py", "chatbot_ui")

        for archivo in (RAIZ / "backend").rglob("*.py"):
            contenido = archivo.read_text(encoding="utf-8")
            for prohibido in prohibidos:
                self.assertNotIn(
                    f"import {prohibido}", contenido,
                    f"{archivo.name} depende de la capa de interfaz ({prohibido})",
                )


if __name__ == "__main__":
    unittest.main()