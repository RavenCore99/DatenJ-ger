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


class TestTendenciaYGraficos(BaseBackendTest):
    """Regresión, predicción, R² y paleta extraídas al backend (SCRUM-81).

    La clase no siembra documentos en ``setUp``: cada prueba arma su propia
    serie temporal con fechas explícitas, que es lo único que hace
    reproducible la recta por mínimos cuadrados.
    """

    def _sembrar_serie(self, por_dia):
        """Inserta ``cantidad`` documentos en cada día indicado."""
        for dia, cantidad in por_dia:
            for indice in range(cantidad):
                self.cursor.execute(
                    "INSERT INTO PDFs (nombre, datos, tamano, fecha_subida, usuario_id) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (f"{dia}-{indice}.pdf", b"x", 1, f"{dia}T10:00:00", self.usuario_id),
                )
        self.conn.commit()

    def test_serie_vacia_no_ajusta(self):
        resultado = reportes.tendencia(self.conn, self.cursor, self.usuario_id)

        self.assertFalse(resultado["suficiente"])
        self.assertEqual(resultado["dias"], [])
        self.assertEqual(resultado["valores"], [])
        self.assertEqual(resultado["linea"], [])
        self.assertIsNone(resultado["pendiente"])
        self.assertIsNone(resultado["intercepto"])
        self.assertIsNone(resultado["prediccion"])
        self.assertIsNone(resultado["r2"])
        assert_sin_tkinter(self)

    def test_un_solo_dia_no_ajusta_la_recta(self):
        self._sembrar_serie([("2026-02-01", 4)])

        resultado = reportes.tendencia(self.conn, self.cursor, self.usuario_id)

        self.assertFalse(resultado["suficiente"])
        self.assertIsNone(resultado["r2"])
        self.assertEqual(resultado["valores"], [4])

    def test_regresion_prediccion_y_r2(self):
        self._sembrar_serie([("2026-01-01", 1), ("2026-01-02", 2), ("2026-01-03", 3)])

        resultado = reportes.tendencia(self.conn, self.cursor, self.usuario_id)

        self.assertTrue(resultado["suficiente"])
        self.assertEqual(resultado["dias"], ["2026-01-01", "2026-01-02", "2026-01-03"])
        self.assertEqual(resultado["valores"], [1, 2, 3])
        self.assertAlmostEqual(resultado["pendiente"], 1.0, places=6)
        self.assertAlmostEqual(resultado["intercepto"], 1.0, places=6)
        # La recta evaluada en los días observados y el día siguiente.
        self.assertEqual(len(resultado["linea"]), 3)
        self.assertAlmostEqual(resultado["linea"][2], 3.0, places=6)
        self.assertAlmostEqual(resultado["prediccion"], 4.0, places=6)
        self.assertAlmostEqual(resultado["r2"], 1.0, places=6)

    def test_prediccion_no_baja_de_cero(self):
        self._sembrar_serie([("2026-03-01", 5), ("2026-03-02", 2)])

        resultado = reportes.tendencia(self.conn, self.cursor, self.usuario_id)

        self.assertGreaterEqual(resultado["prediccion"], 0.0)
        self.assertLess(resultado["pendiente"], 0)

    def test_paleta_por_roles_semanticos(self):
        paleta = reportes.PALETA_GRAFICOS

        self.assertEqual(paleta["tendencia"], "alerta")
        self.assertEqual(paleta["prediccion"], "peligro")
        self.assertEqual(paleta["barras_temporales"], "primario")
        self.assertIn("primario", paleta["series"])

        # La paleta viaja en la respuesta para que el frontend la resuelva
        # contra sus tokens, sin colores incrustados en el servicio.
        resultado = reportes.tendencia(self.conn, self.cursor, self.usuario_id)
        self.assertEqual(resultado["paleta"], dict(paleta))


if __name__ == "__main__":
    unittest.main()