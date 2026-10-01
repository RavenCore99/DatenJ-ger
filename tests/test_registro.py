# Copyright (c) 2024 DatenJäger. All rights reserved.
# tests/test_registro.py - alta de usuario y conexión de modelos sin Tkinter

"""Pruebas del alta de cuentas (SCRUM-57) y de la conexión de modelos (SCRUM-64).

El alta era la última operación que vivía en `main.py`; aquí se comprueba que
el servicio repite sus reglas y que el comando deja la sesión abierta para
configurar el segundo factor encima.
"""

from __future__ import annotations

import os
import tempfile
import unittest

from tests.soporte import BaseBackendTest
from backend.errors import ConflictoError, DatosInvalidosError
from backend.services import autenticacion, modelos
from database import conectar_db, verify_contrasena

CONTRASENA_VALIDA = "Secreta-2026!"


class TestRegistro(BaseBackendTest):
    """Alta de cuentas sobre una base temporal."""

    def registrar(self, nombre="operador", contrasena=CONTRASENA_VALIDA):
        return self.comandos.registrar_usuario(nombre, contrasena)

    # ------------------------------------------------------------------ #
    # Servicio
    # ------------------------------------------------------------------ #

    def test_alta_guarda_el_hash_y_deriva_la_clave(self):
        resultado = autenticacion.registrar_usuario(
            self.conn, self.cursor, nombre="operador", contrasena=CONTRASENA_VALIDA)

        self.assertEqual(resultado["nombre"], "operador")
        self.assertTrue(resultado["clave_sesion"])

        self.cursor.execute(
            "SELECT contrasena FROM Usuarios WHERE nombre = ?", ("operador",))
        hash_guardado = self.cursor.fetchone()[0]

        # El mismo formato PBKDF2 que las cuentas existentes y sin la
        # contraseña en claro.
        self.assertTrue(hash_guardado.startswith("pbkdf2:"))
        self.assertNotIn(CONTRASENA_VALIDA, hash_guardado)
        self.assertTrue(verify_contrasena(CONTRASENA_VALIDA, hash_guardado)[0])

    def test_alta_queda_en_auditoria(self):
        self.registrar()
        self.assertIn(autenticacion.ACCION_REGISTRO, self.eventos())

    def test_nombre_duplicado_no_toca_la_cuenta_existente(self):
        self.registrar(nombre="operador")

        with self.assertRaises(ConflictoError):
            self.registrar(nombre="operador")

        self.cursor.execute(
            "SELECT COUNT(*) FROM Usuarios WHERE nombre = ?", ("operador",))
        self.assertEqual(self.cursor.fetchone()[0], 1)

    def test_nombre_corto(self):
        with self.assertRaises(DatosInvalidosError):
            self.registrar(nombre="ab")

    def test_contrasena_corta_o_debil(self):
        with self.assertRaises(DatosInvalidosError):
            self.registrar(nombre="operador", contrasena="Corta1!")

        with self.assertRaises(DatosInvalidosError):
            self.registrar(nombre="operador", contrasena="sololetrasminusculas")

    def test_sin_datos(self):
        with self.assertRaises(DatosInvalidosError):
            self.registrar(nombre="  ", contrasena="")

    # ------------------------------------------------------------------ #
    # Comando: el alta abre la sesión para configurar el 2FA
    # ------------------------------------------------------------------ #

    def test_el_comando_abre_la_sesion_del_usuario_nuevo(self):
        resultado = self.registrar(nombre="naciente")

        self.assertEqual(resultado["estado"], "registrado")
        self.assertTrue(resultado["autenticado"])
        self.assertEqual(resultado["usuario_nombre"], "naciente")
        self.assertNotIn("clave_sesion", resultado)

        # Con la sesión abierta, el alta del segundo factor es posible.
        preparado = self.comandos.preparar_segundo_factor()
        self.assertTrue(preparado["secreto"])
        self.assertTrue(preparado["qr"])

    def test_el_comando_no_exige_sesion_previa(self):
        self.comandos.cerrar_sesion()
        self.registrar(nombre="otro")
        self.assertTrue(self.comandos.sesion_actual()["autenticado"])


class TestEstadoDeBaseDatos(BaseBackendTest):

    def test_una_base_sana_se_lee_como_ok(self):
        self.assertEqual(self.comandos.estado_base_datos(), "ok")

    def test_una_base_cerrada_se_lee_como_error(self):
        self.conn.close()
        self.assertEqual(self.comandos.estado_base_datos(), "error")


class TestConexionDeModelos(unittest.TestCase):
    """El almacén de la conexión de modelos nunca devuelve la clave."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="datenjager_modelos_")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_estado_inicial_sin_clave(self):
        estado = modelos.estado(self.tmpdir)

        self.assertEqual(estado["proveedor"], modelos.PROVEEDOR_POR_DEFECTO)
        self.assertFalse(estado["clave_configurada"])
        self.assertIsNone(estado["origen_clave"])
        self.assertNotIn("api_key", estado)

    def test_guardar_y_leer_la_clave_cifrada(self):
        modelos.guardar(
            self.tmpdir, proveedor="gemini", modelo="gemini-2.0-flash",
            endpoint="https://ejemplo.invalido/v1", api_key="clave-secreta-123")

        estado = modelos.estado(self.tmpdir)
        self.assertTrue(estado["clave_configurada"])
        # El panel deja la credencial también en el `.env` del proyecto, que es
        # de donde la lee el asistente: el origen efectivo pasa a ser el entorno.
        self.assertEqual(estado["origen_clave"], "entorno")
        self.assertEqual(estado["endpoint"], "https://ejemplo.invalido/v1")

        with open(os.path.join(self.tmpdir, modelos.NOMBRE_ENV), encoding="utf-8") as archivo:
            self.assertIn("clave-secreta-123", archivo.read())

        # La clave no aparece en el estado, pero el servicio la recupera.
        self.assertNotIn("clave-secreta-123", str(estado))
        self.assertEqual(modelos.clave(self.tmpdir), "clave-secreta-123")

        # Y en disco no está en claro.
        with open(os.path.join(self.tmpdir, modelos.NOMBRE_DIRECTORIO,
                               modelos.NOMBRE_ARCHIVO), encoding="utf-8") as archivo:
            crudo = archivo.read()
        self.assertNotIn("clave-secreta-123", crudo)

    def test_quitar_la_clave_no_toca_el_resto(self):
        modelos.guardar(self.tmpdir, api_key="clave-secreta-123",
                        modelo="gemini-1.5-flash")

        estado = modelos.estado(self.tmpdir)
        self.assertTrue(estado["clave_configurada"])

        estado = modelos.guardar(self.tmpdir, quitar_clave=True)
        self.assertFalse(estado["clave_configurada"])
        self.assertEqual(estado["modelo"], "gemini-1.5-flash")

    def test_proveedor_desconocido(self):
        with self.assertRaises(DatosInvalidosError):
            modelos.guardar(self.tmpdir, proveedor="inventado")

    def test_el_env_manda_sobre_el_entorno_del_proceso(self):
        """Contrato nuevo: la credencial del panel surte efecto sin reiniciar.

        `config.py` carga el `.env` en `os.environ` al arrancar, así que si el
        entorno del proceso mandara, una clave guardada desde el panel no se
        aplicaría hasta reiniciar —y «Quitar la credencial» no quitaría nada.
        """
        modelos.guardar(self.tmpdir, api_key="clave-del-panel")
        os.environ[modelos.VARIABLE_ENTORNO] = "clave-cargada-al-arrancar"
        try:
            self.assertEqual(modelos.clave(self.tmpdir), "clave-del-panel")
            self.assertEqual(modelos.estado(self.tmpdir)["origen_clave"], "entorno")
        finally:
            del os.environ[modelos.VARIABLE_ENTORNO]

    def test_sin_env_manda_el_entorno_del_proceso(self):
        """Sin `.env` (pruebas, o una variable exportada a mano) se usa el entorno."""
        os.environ[modelos.VARIABLE_ENTORNO] = "clave-exportada"
        try:
            self.assertEqual(modelos.clave(self.tmpdir), "clave-exportada")
        finally:
            del os.environ[modelos.VARIABLE_ENTORNO]


class TestRegistroPorHTTP(BaseBackendTest):
    """El alta a través del puente HTTP, sin depender de `test_servidor.py`."""

    def test_el_comando_registra_y_la_base_lo_ve(self):
        # Se usa la misma base temporal: la comprobación es directa, sin HTTP,
        # porque el camino HTTP ya está cubierto en `test_servidor.py`.
        self.comandos.registrar_usuario("operador-http", CONTRASENA_VALIDA)

        conn, cursor = conectar_db(self.db_path)
        try:
            cursor.execute(
                "SELECT nombre FROM Usuarios WHERE nombre = ?", ("operador-http",))
            self.assertIsNotNone(cursor.fetchone())
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()