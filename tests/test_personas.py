# Copyright (c) 2024 DatenJäger. All rights reserved.
# tests/test_personas.py - CRUD de personas sin Tkinter

"""Pruebas del servicio de personas."""

from __future__ import annotations

import unittest

from tests.soporte import BaseBackendTest, PDF_MINIMO, assert_sin_tkinter
from backend.errors import ConflictoError, DatosInvalidosError, NoEncontradoError
from backend.services import personas


class TestPersonas(BaseBackendTest):

    def test_crear_y_listar(self):
        personas.crear_persona(
            self.conn, self.cursor,
            cedula="1023", nombres="Ana Diaz", empresa="Minera Ubaté",
            usuario_id=self.usuario_id,
        )
        personas.crear_persona(
            self.conn, self.cursor, cedula="2044", nombres="Luis Gomez")

        listado = personas.listar_personas(self.conn, self.cursor)
        self.assertEqual([p["nombres"] for p in listado], ["Ana Diaz", "Luis Gomez"])
        self.assertEqual(listado[0]["empresa"], "Minera Ubaté")
        self.assertEqual(listado[0]["documentos"], 0)
        # empresa ausente: la interfaz mostraba el marcador
        self.assertEqual(listado[1]["empresa"], personas.SIN_EMPRESA)

        self.assertEqual(personas.contar_personas(self.conn, self.cursor), 2)
        assert_sin_tkinter(self)

    def test_cedula_duplicada(self):
        personas.crear_persona(self.conn, self.cursor, cedula="1023", nombres="Ana Diaz")
        with self.assertRaises(ConflictoError):
            personas.crear_persona(self.conn, self.cursor, cedula="1023", nombres="Otra")

    def test_validacion_de_campos(self):
        with self.assertRaises(DatosInvalidosError):
            personas.crear_persona(self.conn, self.cursor, cedula="", nombres="")
        with self.assertRaises(DatosInvalidosError):
            personas.crear_persona(self.conn, self.cursor, cedula="1", nombres="  ")

    def test_actualizar_persona(self):
        creada = personas.crear_persona(
            self.conn, self.cursor, cedula="555", nombres="Ana Diaz", empresa="A")

        actualizada = personas.actualizar_persona(
            self.conn, self.cursor,
            persona_id=creada["id"], nombres="Ana Diaz Rojas", empresa="B",
            usuario_id=self.usuario_id,
        )

        self.assertEqual(actualizada["nombres"], "Ana Diaz Rojas")
        self.assertEqual(actualizada["empresa"], "B")
        self.assertEqual(actualizada["cedula"], "555")
        self.assertIn(personas.ACCION_EDITAR, self.eventos())

    def test_actualizar_persona_inexistente(self):
        with self.assertRaises(NoEncontradoError):
            personas.actualizar_persona(
                self.conn, self.cursor, persona_id=404, nombres="Nadie")

    def test_documentos_vinculados_se_cuentan_y_quedan_sin_titular(self):
        creada = personas.crear_persona(self.conn, self.cursor, cedula="777", nombres="Ana Diaz")
        self.cursor.execute(
            "INSERT INTO PDFs (nombre, datos, datos_encriptados, tamano, fecha_subida, "
            "usuario_id, persona_id) VALUES (?, ?, 1, ?, ?, ?, ?)",
            ("doc.pdf", b"x", len(PDF_MINIMO), "2026-01-01T00:00:00", self.usuario_id, creada["id"]),
        )
        self.conn.commit()

        self.assertEqual(personas.obtener_persona(
            self.conn, self.cursor, creada["id"])["documentos"], 1)

        eliminada = personas.eliminar_persona(
            self.conn, self.cursor, persona_id=creada["id"], usuario_id=self.usuario_id)
        self.assertEqual(eliminada["documentos"], 1)

        self.cursor.execute("SELECT persona_id FROM PDFs")
        self.assertIsNone(self.cursor.fetchone()[0])
        self.assertIn(personas.ACCION_ELIMINAR, self.eventos())

    def test_filtro_por_nombre_empresa_y_cedula(self):
        personas.crear_persona(
            self.conn, self.cursor, cedula="1023", nombres="Ana Diaz", empresa="Minera Ubaté")
        personas.crear_persona(
            self.conn, self.cursor, cedula="2044", nombres="Luis Gomez", empresa="Carbones SAS")

        for filtro, esperado in (("Ana", "Ana Diaz"), ("Carbones", "Luis Gomez"), ("2044", "Luis Gomez")):
            with self.subTest(filtro=filtro):
                encontrados = personas.listar_personas(self.conn, self.cursor, filtro)
                self.assertEqual([p["nombres"] for p in encontrados], [esperado])

    def test_persona_inexistente(self):
        with self.assertRaises(NoEncontradoError):
            personas.obtener_persona(self.conn, self.cursor, 404)


if __name__ == "__main__":
    unittest.main()