# Copyright (c) 2024 DatenJäger. All rights reserved.
# tests/test_documentos.py - CRUD de documentos sin Tkinter

"""Pruebas del servicio de documentos."""

from __future__ import annotations

import os
import unittest

from tests.soporte import BaseBackendTest, PDF_MINIMO, assert_sin_tkinter
from backend.errors import (
    DatosInvalidosError,
    NoAutenticadoError,
    NoEncontradoError,
)
from backend.services import documentos


class TestDocumentos(BaseBackendTest):

    # ------------------------------------------------------------------ #
    # Escritura
    # ------------------------------------------------------------------ #

    def test_crear_desde_archivo_guarda_cifrado(self):
        ruta = self.crear_pdf("afiliacion.pdf")

        resultado = documentos.crear_documento_desde_archivo(
            self.conn, self.cursor,
            usuario_id=self.usuario_id,
            usuario_nombre=self.usuario_nombre,
            ruta=ruta,
            descripcion="Afiliación EPS",
            cedula="1023",
            nombres="Ana Diaz",
            empresa="Minera Ubaté",
        )

        self.assertEqual(resultado["nombre"], "afiliacion.pdf")
        self.assertEqual(resultado["tamano"], len(PDF_MINIMO))
        self.assertIsNotNone(resultado["persona_id"])

        # el blob guardado no debe contener el PDF en claro
        self.cursor.execute(
            "SELECT datos, datos_encriptados FROM PDFs WHERE id = ?", (resultado["id"],))
        blob, encriptado = self.cursor.fetchone()
        self.assertEqual(encriptado, 1)
        self.assertNotIn(b"%PDF-1.4", bytes(blob))

        assert_sin_tkinter(self)

    def test_crear_desde_bytes_sin_titular(self):
        resultado = documentos.crear_documento(
            self.conn, self.cursor,
            usuario_id=self.usuario_id,
            usuario_nombre=self.usuario_nombre,
            nombre="contrato.pdf",
            datos=b"x" * 512,
        )
        self.assertEqual(resultado["tamano"], 512)
        self.assertIsNone(resultado["persona_id"])

    def test_actualizar_documento_y_titular(self):
        creado = self.crear_documento(cedula="333", nombres="Ana Diaz", empresa="Minera A")

        actualizado = documentos.actualizar_documento(
            self.conn, self.cursor,
            usuario_id=self.usuario_id,
            documento_id=creado["id"],
            nombre="renombrado.pdf",
            descripcion="corregido",
            cedula="333",
            nombres="Ana Diaz Rojas",
            empresa="Minera A SAS",
        )

        self.assertEqual(actualizado["nombre"], "renombrado.pdf")
        self.assertEqual(actualizado["nombres"], "Ana Diaz Rojas")
        self.assertEqual(actualizado["empresa"], "Minera A SAS")
        self.assertIn(documentos.ACCION_EDITAR, self.eventos())

    def test_eliminar_quita_el_documento(self):
        creado = self.crear_documento()
        eliminado = documentos.eliminar_documento(
            self.conn, self.cursor, self.usuario_id, creado["id"])

        self.assertEqual(eliminado["id"], creado["id"])
        self.assertIn(documentos.ACCION_ELIMINAR, self.eventos())
        with self.assertRaises(NoEncontradoError):
            documentos.obtener_documento(
                self.conn, self.cursor, self.usuario_id, creado["id"])

    # ------------------------------------------------------------------ #
    # Lectura
    # ------------------------------------------------------------------ #

    def test_leer_devuelve_el_contenido_original(self):
        contenido = b"%PDF-1.4 reporte \xf0\x9f\x93\x84" + b"z" * 100
        ruta = self.crear_pdf("reporte.pdf", contenido)
        creado = documentos.crear_documento_desde_archivo(
            self.conn, self.cursor,
            usuario_id=self.usuario_id,
            usuario_nombre=self.usuario_nombre,
            ruta=ruta,
        )

        datos, nombre = documentos.leer_documento(
            self.conn, self.cursor,
            usuario_id=self.usuario_id,
            documento_id=creado["id"],
            usuario_nombre=self.usuario_nombre,
        )

        self.assertEqual(datos, contenido)
        self.assertEqual(nombre, "reporte.pdf")
        self.assertIn(documentos.ACCION_ABRIR, self.eventos())

    def test_listar_y_buscar(self):
        self.crear_documento(nombre="uno.pdf", cedula="111", nombres="Ana Diaz", empresa="Minera A")
        self.crear_documento(nombre="dos.pdf", cedula="222", nombres="Luis Gomez", empresa="Minera B")

        todos = documentos.listar_documentos(self.conn, self.cursor, self.usuario_id)
        self.assertEqual(len(todos), 2)

        filtrado = documentos.listar_documentos(self.conn, self.cursor, self.usuario_id, "Ana")
        self.assertEqual([d["nombre"] for d in filtrado], ["uno.pdf"])

        self.assertEqual(
            documentos.contar_documentos(self.conn, self.cursor, self.usuario_id), 2)

    def test_exportar_escribe_el_archivo_descifrado(self):
        ruta = self.crear_pdf("exportable.pdf")
        creado = documentos.crear_documento_desde_archivo(
            self.conn, self.cursor,
            usuario_id=self.usuario_id,
            usuario_nombre=self.usuario_nombre,
            ruta=ruta,
        )
        destino = self.ruta_temporal("copia.pdf")

        documentos.exportar_documento(
            self.conn, self.cursor,
            usuario_id=self.usuario_id,
            documento_id=creado["id"],
            usuario_nombre=self.usuario_nombre,
            destino=destino,
        )

        self.assertTrue(os.path.isfile(destino))
        with open(destino, "rb") as archivo:
            self.assertEqual(archivo.read(), PDF_MINIMO)
        self.assertIn(documentos.ACCION_EXPORTAR, self.eventos())

    # ------------------------------------------------------------------ #
    # Límites y errores
    # ------------------------------------------------------------------ #

    def test_sin_sesion_no_permite_nada(self):
        with self.assertRaises(NoAutenticadoError):
            documentos.listar_documentos(self.conn, self.cursor, None)
        with self.assertRaises(NoAutenticadoError):
            documentos.crear_documento(
                self.conn, self.cursor,
                usuario_id=None, usuario_nombre="", nombre="x.pdf", datos=b"x")

    def test_documento_de_otro_usuario_no_es_visible(self):
        creado = self.crear_documento()
        with self.assertRaises(NoEncontradoError):
            documentos.obtener_documento(self.conn, self.cursor, 999, creado["id"])

    def test_errores_de_validacion(self):
        casos = [
            dict(nombre="", datos=b"x"),
            dict(nombre="a.pdf", datos=b""),
            dict(nombre="a.pdf", datos=b"x", cedula="1023"),   # cédula sin nombres
        ]
        for caso in casos:
            with self.subTest(caso=caso):
                with self.assertRaises(DatosInvalidosError):
                    documentos.crear_documento(
                        self.conn, self.cursor,
                        usuario_id=self.usuario_id,
                        usuario_nombre=self.usuario_nombre,
                        **caso,
                    )

        with self.assertRaises(DatosInvalidosError):
            documentos.crear_documento_desde_archivo(
                self.conn, self.cursor,
                usuario_id=self.usuario_id,
                usuario_nombre=self.usuario_nombre,
                ruta=self.ruta_temporal("no_existe.pdf"),
            )

    def test_actualizar_exige_nombre(self):
        creado = self.crear_documento()
        with self.assertRaises(DatosInvalidosError):
            documentos.actualizar_documento(
                self.conn, self.cursor,
                usuario_id=self.usuario_id,
                documento_id=creado["id"],
                nombre="   ",
            )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def crear_documento(self, nombre: str = "prueba.pdf", **titular) -> dict:
        return documentos.crear_documento(
            self.conn, self.cursor,
            usuario_id=self.usuario_id,
            usuario_nombre=self.usuario_nombre,
            nombre=nombre,
            datos=PDF_MINIMO,
            **titular,
        )


if __name__ == "__main__":
    unittest.main()