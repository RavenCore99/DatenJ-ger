# Copyright (c) 2024 DatenJäger. All rights reserved.
# tests/test_semantica.py - servicio de búsqueda semántica (Fase 6)

"""Pruebas de las piezas deterministas del servicio semántico.

Se prueban aquí solo las funciones que **no** cargan el modelo de embeddings
(troceado, clasificación por reglas, derivación de rutas y el cifrado de
fragmentos): son deterministas y corren sin red ni `fastembed`. El modelo en
sí se valida con los guiones de `scripts/semantico/`, no en la suite rápida.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.services import semantica  # noqa: E402


class TroceadoTest(unittest.TestCase):
    def test_texto_vacio_no_produce_fragmentos(self):
        self.assertEqual(semantica.trocear(""), [])
        self.assertEqual(semantica.trocear("   \n  "), [])

    def test_texto_corto_es_un_solo_fragmento(self):
        self.assertEqual(semantica.trocear("hola mundo"), ["hola mundo"])

    def test_texto_largo_se_trocea_en_varios_fragmentos(self):
        texto = " ".join(["palabra"] * 500)  # ~3500 caracteres
        fragmentos = semantica.trocear(texto, tamaño=600, solape=100)
        self.assertGreater(len(fragmentos), 1)
        # Ningún fragmento supera el tamaño objetivo más el solape.
        for fragmento in fragmentos:
            self.assertLessEqual(len(fragmento), 600 + 100)
            self.assertTrue(fragmento.strip())


class ClasificacionTest(unittest.TestCase):
    def test_contrato(self):
        texto = "contrato de trabajo a término fijo con cláusula de salario y jornada laboral"
        self.assertEqual(semantica.clasificar_texto(texto), "contrato_laboral")

    def test_afiliacion(self):
        texto = "formulario de afiliación del cotizante con novedad de ingreso"
        self.assertEqual(semantica.clasificar_texto(texto), "afiliacion")

    def test_reporte_seguridad_social(self):
        texto = "planilla de aportes a seguridad social con cotización y pensión"
        self.assertEqual(semantica.clasificar_texto(texto), "reporte_seguridad_social")

    def test_sin_categoria(self):
        self.assertEqual(semantica.clasificar_texto(""), "sin_clasificar")
        self.assertEqual(semantica.clasificar_texto("asdf qwer zxcv"), "sin_clasificar")

    def test_no_distingue_mayusculas(self):
        texto = "CONTRATO DE TRABAJO A TÉRMINO FIJO"
        self.assertEqual(semantica.clasificar_texto(texto), "contrato_laboral")


class RutaIndiceTest(unittest.TestCase):
    def test_deriva_al_lado_de_la_base(self):
        self.assertEqual(
            semantica.ruta_indice("/datos/base_datos_pdfs.db"),
            "/datos/base_datos_pdfs.semantico.db",
        )

    def test_sin_directorio(self):
        self.assertEqual(
            semantica.ruta_indice("base.db"),
            "base.semantico.db",
        )


class CifradoFragmentosTest(unittest.TestCase):
    """El cifrado de fragmentos (opción B) debe ser de ida y vuelta exacta."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="semantica_test_")
        self.indice = semantica.conectar_indice(
            os.path.join(self.tmp, "indice.db"))

    def tearDown(self):
        self.indice.close()
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cifra_y_descifra_con_la_misma_clave(self):
        clave = semantica._clave_fragmentos(self.indice, "usuario-de-prueba")
        original = "fragmento sensible con datos personales y trabajo en altura"
        cifrado = semantica._cifrar_fragmento(original, clave)

        # El texto no viaja en claro dentro del blob.
        self.assertNotIn(original.encode("utf-8"), cifrado)

        # La misma clave lo recupera idéntico.
        self.assertEqual(semantica._descifrar_fragmento(cifrado, clave), original)

    def test_la_clave_es_estable_entre_llamadas(self):
        a = semantica._clave_fragmentos(self.indice, "usuario-de-prueba")
        b = semantica._clave_fragmentos(self.indice, "usuario-de-prueba")
        self.assertEqual(a, b)

    def test_estado_indice_vacio(self):
        estado = semantica.estado_indice(self.indice, usuario_id=1)
        self.assertFalse(estado["indexado"])
        self.assertEqual(estado["fragmentos"], 0)
        self.assertEqual(estado["documentos"], 0)


if __name__ == "__main__":
    unittest.main()