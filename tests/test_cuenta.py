# Copyright (c) 2024 DatenJäger. All rights reserved.
# tests/test_cuenta.py - gestión de la propia cuenta

"""Pruebas de contraseña, 2FA, códigos de respaldo y confianza (SCRUM-25)."""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest

import pyotp

from tests.soporte import BaseBackendTest
from backend import tokens
from backend.errors import (
    CredencialesInvalidasError,
    DatosInvalidosError,
    SegundoFactorInvalidoError,
)
from backend.services import autenticacion
from database import hash_contrasena

CONTRASENA = "Secreta-2026!"
NUEVA = "OtraClave-2026!"


class BaseCuentaTest(BaseBackendTest):

    def setUp(self):
        super().setUp()
        # El almacén de tokens nunca debe apuntar al proyecto real en pruebas.
        self.almacen = tempfile.mkdtemp(prefix="dj-tokens-test-")
        self._entorno_previo = os.environ.get("DATENJAGER_TOKENS")
        os.environ["DATENJAGER_TOKENS"] = self.almacen

        self.cursor.execute(
            "UPDATE Usuarios SET contrasena = ? WHERE id = ?",
            (hash_contrasena(CONTRASENA), self.usuario_id),
        )
        self.conn.commit()

        self.comandos.iniciar_sesion(
            self.usuario_id, self.usuario_nombre,
            autenticacion.autenticar(
                self.conn, self.cursor,
                nombre=self.usuario_nombre, contrasena=CONTRASENA)["clave_sesion"],
        )

    def tearDown(self):
        if self._entorno_previo is None:
            os.environ.pop("DATENJAGER_TOKENS", None)
        else:
            os.environ["DATENJAGER_TOKENS"] = self._entorno_previo
        shutil.rmtree(self.almacen, ignore_errors=True)
        super().tearDown()

    # ------------------------------------------------------------------ #

    def activar(self, secreto):
        """Activa el 2FA desde la fachada de comandos y devuelve los códigos."""
        return self.comandos.activar_segundo_factor(secreto, pyotp.TOTP(secreto).now())

    def activar_con(self, secreto):
        """Activa el 2FA con un secreto conocido."""
        self.activar(secreto)
        return secreto


class TestPreparacion(BaseCuentaTest):

    def test_preparar_entrega_secreto_uri_y_qr(self):
        datos = self.comandos.preparar_segundo_factor()

        self.assertEqual(len(datos["secreto"]), 32)
        self.assertIn("DatenJ%C3%A4ger", datos["uri"])
        # El QR viaja como PNG en base64, listo para un `data:` del frontend.
        self.assertTrue(datos["qr"].startswith("iVBOR"))

    def test_preparar_no_activa_el_segundo_factor(self):
        self.comandos.preparar_segundo_factor()

        self.assertFalse(self.comandos.estado_de_cuenta()["segundo_factor_habilitado"])


class TestActivacion(BaseCuentaTest):

    def test_activar_entrega_codigos_de_respaldo(self):
        resultado = self.activar(pyotp.random_base32())

        self.assertEqual(len(resultado["codigos_de_respaldo"]), 5)
        for codigo in resultado["codigos_de_respaldo"]:
            self.assertEqual(len(codigo), 6)
            self.assertTrue(codigo.isdigit())

        self.assertTrue(self.comandos.estado_de_cuenta()["segundo_factor_habilitado"])

    def test_activar_con_codigo_incorrecto(self):
        with self.assertRaises(SegundoFactorInvalidoError):
            self.comandos.activar_segundo_factor("JBSWY3DPEHPK3PXP", "000000")

        self.assertFalse(self.comandos.estado_de_cuenta()["segundo_factor_habilitado"])

    def test_activar_con_codigo_mal_formado(self):
        with self.assertRaises(SegundoFactorInvalidoError):
            self.comandos.activar_segundo_factor("JBSWY3DPEHPK3PXP", "abc")

    def test_tras_activar_el_acceso_pide_el_segundo_factor(self):
        secreto = self.activar_con(pyotp.random_base32())

        self.comandos.cerrar_sesion()
        resultado = self.comandos.iniciar_sesion_credenciales(self.usuario_nombre, CONTRASENA)

        self.assertEqual(resultado["estado"], "segundo_factor")
        self.comandos.verificar_segundo_factor(pyotp.TOTP(secreto).now())
        self.assertTrue(self.comandos.sesion_actual()["autenticado"])

    def test_los_codigos_de_respaldo_recien_emitidos_sirven(self):
        resultado = self.activar(pyotp.random_base32())
        codigo = resultado["codigos_de_respaldo"][0]

        self.comandos.cerrar_sesion()
        self.comandos.iniciar_sesion_credenciales(self.usuario_nombre, CONTRASENA)

        self.assertTrue(
            self.comandos.usar_codigo_de_respaldo(codigo)["autenticado"])


class TestRegeneracion(BaseCuentaTest):

    def test_los_codigos_viejos_dejan_de_servir(self):
        secreto = pyotp.random_base32()
        viejos = self.activar(secreto)["codigos_de_respaldo"]

        nuevos = self.comandos.regenerar_codigos_de_respaldo(
            pyotp.TOTP(secreto).now())["codigos_de_respaldo"]

        self.assertNotEqual(viejos, nuevos)

        self.comandos.cerrar_sesion()
        self.comandos.iniciar_sesion_credenciales(self.usuario_nombre, CONTRASENA)
        with self.assertRaises(SegundoFactorInvalidoError):
            self.comandos.usar_codigo_de_respaldo(viejos[0])

    def test_regenerar_exige_un_codigo_vigente(self):
        self.activar_con(pyotp.random_base32())

        with self.assertRaises(SegundoFactorInvalidoError):
            self.comandos.regenerar_codigos_de_respaldo("000000")


class TestDesactivacion(BaseCuentaTest):

    def test_desactivar(self):
        secreto = self.activar_con(pyotp.random_base32())

        estado = self.comandos.desactivar_segundo_factor(pyotp.TOTP(secreto).now())

        self.assertFalse(estado["segundo_factor_habilitado"])
        self.assertFalse(estado["codigos_de_respaldo_configurados"])

        # Sin 2FA, el acceso vuelve a resolverse solo con la contraseña.
        self.comandos.cerrar_sesion()
        self.assertEqual(
            self.comandos.iniciar_sesion_credenciales(
                self.usuario_nombre, CONTRASENA)["estado"],
            "completado",
        )

    def test_desactivar_exige_codigo_valido(self):
        self.activar_con(pyotp.random_base32())

        with self.assertRaises(SegundoFactorInvalidoError):
            self.comandos.desactivar_segundo_factor("000000")

        self.assertTrue(self.comandos.estado_de_cuenta()["segundo_factor_habilitado"])


class TestCambioDeContrasena(BaseCuentaTest):

    def test_cambio_completo(self):
        secreto = self.activar_con(pyotp.random_base32())
        clave_anterior = self.comandos.state.session_key
        codigos = self.comandos.regenerar_codigos_de_respaldo(
            pyotp.TOTP(secreto).now())["codigos_de_respaldo"]

        resultado = self.comandos.cambiar_contrasena(
            CONTRASENA, NUEVA, pyotp.TOTP(secreto).now())

        self.assertEqual(resultado["estado"], "contrasena_cambiada")
        self.assertTrue(resultado["autenticado"])

        clave_nueva = self.comandos.state.session_key
        self.assertNotEqual(clave_nueva, clave_anterior)

        # La contraseña nueva funciona y el secreto se re-cifró con la clave nueva.
        self.comandos.cerrar_sesion()
        acceso = self.comandos.iniciar_sesion_credenciales(self.usuario_nombre, NUEVA)
        self.assertEqual(acceso["estado"], "segundo_factor")
        self.assertTrue(
            self.comandos.verificar_segundo_factor(pyotp.TOTP(secreto).now())["autenticado"])

        # Y los códigos de respaldo siguen siendo válidos tras el re-cifrado.
        # Se borra antes la confianza: el acceso anterior ya emitió un token que
        # omitiría el segundo factor y no llegaría a probar el respaldo.
        tokens.borrar(self.almacen, self.usuario_nombre)
        self.comandos.cerrar_sesion()
        self.comandos.iniciar_sesion_credenciales(self.usuario_nombre, NUEVA)
        self.assertTrue(self.comandos.usar_codigo_de_respaldo(codigos[0])["autenticado"])

    def test_la_contrasena_anterior_deja_de_servir(self):
        secreto = self.activar_con(pyotp.random_base32())
        self.comandos.cambiar_contrasena(CONTRASENA, NUEVA, pyotp.TOTP(secreto).now())

        self.comandos.cerrar_sesion()
        with self.assertRaises(CredencialesInvalidasError):
            self.comandos.iniciar_sesion_credenciales(self.usuario_nombre, CONTRASENA)

    def test_contrasena_actual_incorrecta(self):
        secreto = self.activar_con(pyotp.random_base32())

        with self.assertRaises(CredencialesInvalidasError):
            self.comandos.cambiar_contrasena("no-es", NUEVA, pyotp.TOTP(secreto).now())

    def test_codigo_del_autenticador_incorrecto(self):
        self.activar_con(pyotp.random_base32())

        with self.assertRaises(SegundoFactorInvalidoError):
            self.comandos.cambiar_contrasena(CONTRASENA, NUEVA, "000000")

    def test_contrasena_debil(self):
        secreto = self.activar_con(pyotp.random_base32())

        with self.assertRaises(DatosInvalidosError):
            self.comandos.cambiar_contrasena(CONTRASENA, "1234", pyotp.TOTP(secreto).now())

    def test_sin_segundo_factor_no_se_puede_cambiar(self):
        with self.assertRaises(SegundoFactorInvalidoError):
            self.comandos.cambiar_contrasena(CONTRASENA, NUEVA, "000000")

    def test_el_cambio_revoca_la_confianza_del_dispositivo(self):
        secreto = self.activar_con(pyotp.random_base32())

        # La confianza nace al completar el segundo factor en un acceso normal.
        self.comandos.cerrar_sesion()
        self.comandos.iniciar_sesion_credenciales(self.usuario_nombre, CONTRASENA)
        self.comandos.verificar_segundo_factor(pyotp.TOTP(secreto).now())
        self.assertTrue(tokens.hay_almacen(self.almacen, self.usuario_nombre))

        self.comandos.cambiar_contrasena(CONTRASENA, NUEVA, pyotp.TOTP(secreto).now())

        self.assertFalse(tokens.hay_almacen(self.almacen, self.usuario_nombre))
        self.assertFalse(self.comandos.estado_de_cuenta()["confianza_guardada"])


class TestConfianza(BaseCuentaTest):

    def test_el_token_emitido_se_guarda_cifrado_y_omite_el_segundo_factor(self):
        secreto = self.activar_con(pyotp.random_base32())

        # El token se emite al completar el segundo factor de un acceso.
        self.comandos.cerrar_sesion()
        self.comandos.iniciar_sesion_credenciales(self.usuario_nombre, CONTRASENA)
        self.comandos.verificar_segundo_factor(pyotp.TOTP(secreto).now())

        guardado = tokens.leer(self.almacen, self.usuario_nombre)
        self.assertTrue(guardado)
        self.assertTrue(self.comandos.estado_de_cuenta()["confianza_guardada"])

        # El siguiente acceso lo recupera del almacén: no hace falta enviarlo.
        self.comandos.cerrar_sesion()
        acceso = self.comandos.iniciar_sesion_credenciales(self.usuario_nombre, CONTRASENA)

        self.assertEqual(acceso["estado"], "completado")
        self.assertTrue(acceso["segundo_factor_omitido"])

    def test_revocar(self):
        self.activar_con(pyotp.random_base32())

        estado = self.comandos.revocar_confianza()

        self.assertFalse(estado["confianza_guardada"])
        self.assertFalse(tokens.hay_almacen(self.almacen, self.usuario_nombre))

        # Con la confianza revocada, el acceso vuelve a pedir el segundo factor.
        self.comandos.cerrar_sesion()
        self.assertEqual(
            self.comandos.iniciar_sesion_credenciales(
                self.usuario_nombre, CONTRASENA)["estado"],
            "segundo_factor",
        )


if __name__ == "__main__":
    unittest.main()