# Copyright (c) 2024 DatenJäger. All rights reserved.
# tests/test_auditoria.py - registro y consulta de auditoría sin Tkinter

"""Pruebas del servicio de auditoría."""

from __future__ import annotations

import os
import unittest

from tests.soporte import BaseBackendTest, assert_sin_tkinter
from backend.services import auditoria


class TestAuditoria(BaseBackendTest):

    def test_registrar_evento_con_y_sin_documento(self):
        self.assertTrue(auditoria.registrar_evento(
            self.conn, self.cursor, "Login exitoso", self.usuario_id))
        self.assertTrue(auditoria.registrar_evento(
            self.conn, self.cursor, "Abrir / Descifrar PDF", self.usuario_id, documento_id=7))

        eventos = auditoria.listar_eventos(self.conn, self.cursor)
        self.assertEqual(len(eventos), 2)
        # más reciente primero
        self.assertEqual(eventos[0]["documento_id"], 7)
        self.assertIsNone(eventos[1]["documento_id"])
        self.assertEqual(eventos[0]["usuario"], self.usuario_nombre)
        assert_sin_tkinter(self)

    def test_registrar_evento_sin_accion_no_escribe(self):
        self.assertFalse(auditoria.registrar_evento(self.conn, self.cursor, ""))
        self.assertEqual(auditoria.contar_eventos(self.conn, self.cursor), 0)

    def test_registrar_evento_nunca_propaga_error(self):
        class CursorRoto:
            def execute(self, *a, **k):
                raise RuntimeError("base caída")

        self.assertFalse(auditoria.registrar_evento(self.conn, CursorRoto(), "Acción cualquiera"))

    def test_filtros_de_consulta(self):
        auditoria.registrar_evento(self.conn, self.cursor, "Login exitoso", self.usuario_id)
        auditoria.registrar_evento(self.conn, self.cursor, "Eliminar PDF", self.usuario_id)
        auditoria.registrar_evento(self.conn, self.cursor, "Login fallido", self.usuario_id)

        self.assertEqual(len(auditoria.listar_eventos(self.conn, self.cursor, accion="Login")), 2)
        self.assertEqual(len(auditoria.listar_eventos(self.conn, self.cursor, accion="Eliminar")), 1)
        self.assertEqual(len(auditoria.listar_eventos(self.conn, self.cursor, desde="2000-01-01")), 3)
        self.assertEqual(len(auditoria.listar_eventos(self.conn, self.cursor, limite=1)), 1)

    def test_contar_eventos(self):
        self.assertEqual(auditoria.contar_eventos(self.conn, self.cursor), 0)
        auditoria.registrar_evento(self.conn, self.cursor, "Uno", self.usuario_id)
        self.assertEqual(auditoria.contar_eventos(self.conn, self.cursor), 1)

    def test_limpiar_historial_deja_constancia(self):
        for accion in ("Uno", "Dos", "Tres"):
            auditoria.registrar_evento(self.conn, self.cursor, accion, self.usuario_id)

        eliminados = auditoria.limpiar_historial(self.conn, self.cursor, self.usuario_id)

        self.assertEqual(eliminados, 3)
        restantes = auditoria.listar_eventos(self.conn, self.cursor)
        self.assertEqual(len(restantes), 1)
        self.assertIn(auditoria.ACCION_LIMPIEZA, restantes[0]["accion"])
        self.assertIn("3 registros eliminados", restantes[0]["accion"])

    def test_limpiar_historial_vacio(self):
        self.assertEqual(auditoria.limpiar_historial(self.conn, self.cursor), 0)

    def test_log_sistema_desde_archivo_y_en_memoria(self):
        auditoria.registrar_evento(self.conn, self.cursor, "Evento visible", self.usuario_id)

        contenido, origen = auditoria.construir_log_sistema(
            self.conn, self.cursor, self.tmpdir)
        self.assertEqual(origen, "(generado en memoria)")
        self.assertIn("Evento visible", contenido)

        ruta_log = os.path.join(self.tmpdir, "app.log")
        with open(ruta_log, "w", encoding="utf-8") as archivo:
            archivo.write("linea de log\n")

        contenido, origen = auditoria.construir_log_sistema(
            self.conn, self.cursor, self.tmpdir)
        self.assertEqual(origen, ruta_log)
        self.assertEqual(contenido, "linea de log\n")


if __name__ == "__main__":
    unittest.main()