# Copyright (c) 2024 DatenJäger. All rights reserved.
# tests/test_tokens.py - almacén cifrado de tokens de confianza

"""Pruebas del almacén de tokens de confianza (SCRUM-25)."""

from __future__ import annotations

import os
import stat
import tempfile
import unittest

from backend import tokens


class TestAlmacenDeTokens(unittest.TestCase):

    def setUp(self):
        self.raiz = tempfile.mkdtemp(prefix="dj-tokens-")
        self.otra = tempfile.mkdtemp(prefix="dj-tokens-otro-")
        self.usuario = "raven"
        self.token = "9f2b" * 16

    def tearDown(self):
        import shutil

        shutil.rmtree(self.raiz, ignore_errors=True)
        shutil.rmtree(self.otra, ignore_errors=True)

    # ------------------------------------------------------------------ #

    def test_guardar_y_leer(self):
        tokens.guardar(self.raiz, self.usuario, self.token)
        self.assertEqual(tokens.leer(self.raiz, self.usuario), self.token)
        self.assertTrue(tokens.hay_almacen(self.raiz, self.usuario))

    def test_sin_token_guardado(self):
        self.assertIsNone(tokens.leer(self.raiz, self.usuario))
        self.assertFalse(tokens.hay_almacen(self.raiz, self.usuario))

    def test_borrar(self):
        tokens.guardar(self.raiz, self.usuario, self.token)

        self.assertTrue(tokens.borrar(self.raiz, self.usuario))
        self.assertIsNone(tokens.leer(self.raiz, self.usuario))
        self.assertFalse(tokens.borrar(self.raiz, self.usuario))

    def test_el_token_no_queda_en_claro_en_disco(self):
        archivo = tokens.guardar(self.raiz, self.usuario, self.token)
        contenido = archivo.read_bytes()

        self.assertNotIn(self.token.encode(), contenido)
        self.assertTrue(contenido.startswith(b"ENCK:"))

    def test_permisos_restringidos(self):
        archivo = tokens.guardar(self.raiz, self.usuario, self.token)
        directorio = archivo.parent

        self.assertEqual(stat.S_IMODE(directorio.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(archivo.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((directorio / tokens.NOMBRE_CLAVE).stat().st_mode), 0o600)

    def test_el_nombre_del_usuario_no_aparece_en_el_archivo(self):
        archivo = tokens.guardar(self.raiz, self.usuario, self.token)
        self.assertNotIn(self.usuario, archivo.name)

    def test_cuentas_independientes(self):
        tokens.guardar(self.raiz, "raven", "token-de-raven")
        tokens.guardar(self.raiz, "ana", "token-de-ana")

        self.assertEqual(tokens.leer(self.raiz, "raven"), "token-de-raven")
        self.assertEqual(tokens.leer(self.raiz, "ana"), "token-de-ana")

        tokens.borrar(self.raiz, "raven")
        self.assertIsNone(tokens.leer(self.raiz, "raven"))
        self.assertEqual(tokens.leer(self.raiz, "ana"), "token-de-ana")

    def test_otra_clave_no_descifra_los_tokens(self):
        tokens.guardar(self.raiz, self.usuario, self.token)
        archivo = tokens._archivo_de(tokens.ruta_almacen(self.raiz), self.usuario)

        # Se traslada el archivo cifrado a un almacén con otra clave.
        otro = tokens.ruta_almacen(self.otra)
        destino = otro / archivo.name
        destino.write_bytes(archivo.read_bytes())

        # Sin la clave que lo cifró, el token no se recupera y no hay error.
        self.assertIsNone(tokens.leer(self.otra, self.usuario))

    def test_reemplazo_del_token(self):
        tokens.guardar(self.raiz, self.usuario, "viejo")
        tokens.guardar(self.raiz, self.usuario, "nuevo")

        self.assertEqual(tokens.leer(self.raiz, self.usuario), "nuevo")

    def test_archivo_corrupto_no_rompe_el_acceso(self):
        archivo = tokens.guardar(self.raiz, self.usuario, self.token)
        archivo.write_bytes(b"basura que no es un token cifrado")

        self.assertIsNone(tokens.leer(self.raiz, self.usuario))

    def test_migracion_desde_config(self):
        en_claro = {"raven": "token-uno", "ana": "token-dos", "": "", "otro": None}

        resumen = tokens.migrar_desde_config(self.raiz, en_claro)

        self.assertEqual(resumen["migrados"], ["ana", "raven"])
        self.assertNotIn("", resumen["migrados"])
        self.assertNotIn("otro", resumen["migrados"])
        self.assertEqual(tokens.leer(self.raiz, "raven"), "token-uno")
        self.assertEqual(tokens.leer(self.raiz, "ana"), "token-dos")

    def test_migracion_sin_tokens(self):
        resumen = tokens.migrar_desde_config(self.raiz, None)
        self.assertEqual(resumen, {"migrados": [], "conservados": []})


if __name__ == "__main__":
    unittest.main()