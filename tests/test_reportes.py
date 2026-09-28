# Copyright (c) 2024 DatenJäger. All rights reserved.
# tests/test_reportes.py - métricas y exportación sin Tkinter

"""Pruebas del servicio de reportes."""

from __future__ import annotations

import os
import unittest

from tests.soporte import BaseBackendTest, PDF_MINIMO, assert_sin_tkinter
from backend.errors import DatosInvalidosError
from backend.services import reportes


class TestReportes(BaseBackendTest):

    def setUp(self):
        super().setUp()
        self._sembrar_documentos()

    def _sembrar_documentos(self):
        for nombre, cedula, titular, empresa in (
            ("uno.pdf", "111", "Ana Diaz", "Minera A"),
            ("dos.pdf", "111", "Ana Diaz", "Minera A"),
            ("tres.pdf", "222", "Luis Gomez", "Minera B"),
        ):
            self.comandos.agregar_documento_bytes(
                nombre=nombre, datos=PDF_MINIMO,
                cedula=cedula, nombres=titular, empresa=empresa)

    def test_estadisticas_del_dashboard(self):
        stats = reportes.estadisticas(self.conn, self.cursor, self.usuario_id)

        self.assertEqual(stats["total_pdfs"], 3)
        self.assertEqual(stats["total_personas"], 2)
        self.assertEqual(stats["total_empresas"], 2)
        self.assertTrue(stats["total_size_str"].endswith("B"))
        assert_sin_tkinter(self)

    def test_documentos_por_empresa_y_por_dia(self):
        por_empresa = reportes.documentos_por_empresa(self.conn, self.cursor, self.usuario_id)
        self.assertEqual(por_empresa[0], ("Minera A", 2))

        por_dia = reportes.documentos_por_dia(self.conn, self.cursor, self.usuario_id)
        self.assertEqual(sum(total for _dia, total in por_dia), 3)

    def test_datos_de_inventario(self):
        filas, stats = reportes.datos_inventario(self.conn, self.cursor, self.usuario_id)

        self.assertEqual(len(filas), 3)
        self.assertEqual(stats["total_pdfs"], 3)
        self.assertEqual(stats["total_empresas"], 2)
        self.assertEqual(len(stats["empresas_data"]), 2)

    def test_exportar_pdf_y_csv(self):
        for formato in ("pdf", "csv"):
            with self.subTest(formato=formato):
                destino = self.ruta_temporal(f"reporte.{formato}")
                escrito = reportes.exportar_inventario(
                    self.conn, self.cursor,
                    usuario_id=self.usuario_id,
                    usuario_nombre=self.usuario_nombre,
                    destino=destino,
                    formato=formato,
                )
                self.assertEqual(escrito, destino)
                self.assertTrue(os.path.isfile(destino))
                self.assertGreater(os.path.getsize(destino), 0)

        acciones = self.eventos()
        self.assertIn(reportes.ACCION_REPORTE.format(formato="PDF"), acciones)
        self.assertIn(reportes.ACCION_REPORTE.format(formato="CSV"), acciones)

    def test_formato_desconocido_cae_a_pdf(self):
        destino = self.ruta_temporal("reporte.xyz")
        reportes.exportar_inventario(
            self.conn, self.cursor,
            usuario_id=self.usuario_id,
            usuario_nombre=self.usuario_nombre,
            destino=destino,
            formato="docx",
        )
        self.assertTrue(os.path.isfile(destino))
        self.assertIn(reportes.ACCION_REPORTE.format(formato="PDF"), self.eventos())

    def test_exportar_sin_destino(self):
        with self.assertRaises(DatosInvalidosError):
            reportes.exportar_inventario(
                self.conn, self.cursor,
                usuario_id=self.usuario_id,
                usuario_nombre=self.usuario_nombre,
                destino="",
            )

    def test_usuario_sin_documentos(self):
        stats = reportes.estadisticas(self.conn, self.cursor, 999)
        self.assertEqual(stats["total_pdfs"], 0)
        filas, _stats = reportes.datos_inventario(self.conn, self.cursor, 999)
        self.assertEqual(filas, [])


if __name__ == "__main__":
    unittest.main()