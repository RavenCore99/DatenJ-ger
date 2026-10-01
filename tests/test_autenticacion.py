# Copyright (c) 2024 DatenJäger. All rights reserved.
# tests/test_autenticacion.py - autenticación sin Tkinter

"""Pruebas del servicio de autenticación (SCRUM-22).

Incluye la prueba que más importa al mover este código: que un documento
cifrado antes del cambio se siga descifrando con la misma contraseña y la
misma clave de sesión.
"""

from __future__ import annotations

import hashlib
import unittest

import pyotp

from tests.soporte import BaseBackendTest, PDF_MINIMO
from backend.errors import (
    CredencialesInvalidasError,
    CuentaBloqueadaError,
    DatosInvalidosError,
    SegundoFactorInvalidoError,
    UsuarioInexistenteError,
)
from backend.services import autenticacion
from database import hash_contrasena
from encryption import EncryptionManager

CONTRASENA = "Secreta-2026!"


class BaseAuthTest(BaseBackendTest):
    """Base con la contraseña del usuario de prueba bajo control del test."""

    def setUp(self):
        super().setUp()
        self.cursor.execute(
            "UPDATE Usuarios SET contrasena = ? WHERE id = ?",
            (hash_contrasena(CONTRASENA), self.usuario_id),
        )
        self.conn.commit()

    # ------------------------------------------------------------------ #

    def entrar(self, contrasena=CONTRASENA, **extra):
        return autenticacion.autenticar(
            self.conn, self.cursor,
            nombre=self.usuario_nombre, contrasena=contrasena, **extra,
        )

    def activar_segundo_factor(self, secreto="JBSWY3DPEHPK3PXP", respaldo="111111,222222"):
        """Prepara la cuenta con 2FA activo, cifrado como lo deja el sistema."""
        clave = self.entrar()["clave_sesion"]
        self.cursor.execute(
            "UPDATE Usuarios SET totp_enabled = 1, totp_secret = ?, backup_codes = ? WHERE id = ?",
            (
                EncryptionManager.encrypt_str_with_key(secreto, clave),
                EncryptionManager.encrypt_str_with_key(respaldo, clave),
                self.usuario_id,
            ),
        )
        self.conn.commit()
        return secreto, clave


class TestCredenciales(BaseAuthTest):

    def test_acceso_correcto_sin_segundo_factor(self):
        resultado = self.entrar()

        self.assertEqual(resultado["estado"], autenticacion.ESTADO_COMPLETADO)
        self.assertEqual(resultado["usuario_id"], self.usuario_id)
        self.assertFalse(resultado["segundo_factor_omitido"])
        self.assertIsInstance(resultado["clave_sesion"], bytes)
        self.assertIn(autenticacion.ACCION_LOGIN_OK, self.eventos())

    def test_contrasena_incorrecta(self):
        with self.assertRaises(CredencialesInvalidasError):
            self.entrar("no-es-la-buena")

        self.cursor.execute("SELECT failed_attempts FROM Usuarios WHERE id = ?", (self.usuario_id,))
        self.assertEqual(self.cursor.fetchone()[0], 1)
        self.assertIn(autenticacion.ACCION_LOGIN_CONTRASENA_INCORRECTA, self.eventos())

    def test_usuario_inexistente(self):
        with self.assertRaises(UsuarioInexistenteError):
            autenticacion.autenticar(
                self.conn, self.cursor, nombre="fantasma", contrasena=CONTRASENA)

        self.assertIn(autenticacion.ACCION_LOGIN_USUARIO_INEXISTENTE, self.eventos())

    def test_credenciales_vacias(self):
        with self.assertRaises(CredencialesInvalidasError):
            autenticacion.autenticar(self.conn, self.cursor, nombre="", contrasena="")

    def test_cuenta_se_bloquea_tras_intentos_fallidos(self):
        for _intento in range(5):
            with self.assertRaises(CredencialesInvalidasError):
                self.entrar("mal")

        with self.assertRaises(CuentaBloqueadaError) as contexto:
            self.entrar()
        self.assertGreater(contexto.exception.segundos_restantes, 0)
        self.assertIn(autenticacion.ACCION_BLOQUEO, self.eventos())

        # Ni con la contraseña correcta se entra mientras dure el bloqueo.
        with self.assertRaises(CuentaBloqueadaError):
            self.entrar()

    def test_acceso_correcto_limpia_los_intentos(self):
        with self.assertRaises(CredencialesInvalidasError):
            self.entrar("mal")

        self.entrar()
        self.cursor.execute("SELECT failed_attempts FROM Usuarios WHERE id = ?", (self.usuario_id,))
        self.assertEqual(self.cursor.fetchone()[0], 0)


class TestMigracionDeHash(BaseAuthTest):

    def test_hash_heredado_se_migra_en_el_acceso(self):
        legado = hashlib.sha256(CONTRASENA.encode()).hexdigest()
        self.cursor.execute(
            "UPDATE Usuarios SET contrasena = ? WHERE id = ?", (legado, self.usuario_id))
        self.conn.commit()

        self.entrar()

        self.cursor.execute("SELECT contrasena FROM Usuarios WHERE id = ?", (self.usuario_id,))
        actual = self.cursor.fetchone()[0]
        self.assertTrue(actual.startswith("pbkdf2:"))
        self.assertIn(autenticacion.ACCION_REHASH, self.eventos())

        # Y sigue entrando con la misma contraseña tras migrar.
        self.assertEqual(self.entrar()["estado"], autenticacion.ESTADO_COMPLETADO)


class TestSegundoFactor(BaseAuthTest):

    def test_con_2fa_activo_pide_el_codigo(self):
        self.activar_segundo_factor()

        resultado = self.entrar()
        self.assertEqual(resultado["estado"], autenticacion.ESTADO_SEGUNDO_FACTOR)
        self.assertFalse(resultado["segundo_factor_omitido"])

    def test_codigo_correcto_e_incorrecto(self):
        secreto, clave = self.activar_segundo_factor()
        codigo = pyotp.TOTP(secreto).now()

        self.assertTrue(autenticacion.verificar_segundo_factor(
            self.conn, self.cursor,
            usuario_id=self.usuario_id, clave_sesion=clave, codigo=codigo))

        self.assertFalse(autenticacion.verificar_segundo_factor(
            self.conn, self.cursor,
            usuario_id=self.usuario_id, clave_sesion=clave, codigo="000000"))

        eventos = self.eventos()
        self.assertIn(autenticacion.ACCION_2FA_OK, eventos)
        self.assertIn(autenticacion.ACCION_2FA_FALLIDO, eventos)

    def test_codigo_con_formato_invalido(self):
        _, clave = self.activar_segundo_factor()
        for codigo in ("", "123", "abcdef"):
            with self.subTest(codigo=codigo):
                with self.assertRaises(SegundoFactorInvalidoError):
                    autenticacion.verificar_segundo_factor(
                        self.conn, self.cursor,
                        usuario_id=self.usuario_id, clave_sesion=clave, codigo=codigo)

    def test_clave_de_sesion_equivocada_no_valida_el_codigo(self):
        self.activar_segundo_factor()
        with self.assertRaises(SegundoFactorInvalidoError):
            autenticacion.verificar_segundo_factor(
                self.conn, self.cursor,
                usuario_id=self.usuario_id,
                clave_sesion=b"clave-que-no-corresponde",
                codigo="123456",
            )

    def test_material_2fa_legado_se_migra_a_encryption_por_sesion(self):
        clave = self.entrar()["clave_sesion"]
        secreto = "JBSWY3DPEHPK3PXP"
        self.cursor.execute(
            "UPDATE Usuarios SET totp_enabled = 1, totp_secret = ?, backup_codes = ? WHERE id = ?",
            (
                EncryptionManager.encrypt_str(secreto, CONTRASENA),      # formato ENC:
                EncryptionManager.encrypt_str("333333", CONTRASENA),     # formato ENC:
                self.usuario_id,
            ),
        )
        self.conn.commit()

        self.entrar()

        self.cursor.execute(
            "SELECT totp_secret, backup_codes FROM Usuarios WHERE id = ?", (self.usuario_id,))
        totp_guardado, respaldo_guardado = self.cursor.fetchone()
        self.assertFalse(totp_guardado.startswith("ENC:"))
        self.assertFalse(respaldo_guardado.startswith("ENC:"))

        # Y el código del secreto migrado sigue funcionando con la clave nueva.
        self.assertTrue(autenticacion.verificar_segundo_factor(
            self.conn, self.cursor,
            usuario_id=self.usuario_id, clave_sesion=clave,
            codigo=pyotp.TOTP(secreto).now()))


class TestCodigosDeRespaldo(BaseAuthTest):

    def test_codigo_valido_se_consume(self):
        _, clave = self.activar_segundo_factor(respaldo="111111,222222")

        self.assertTrue(autenticacion.usar_codigo_de_respaldo(
            self.conn, self.cursor,
            usuario_id=self.usuario_id, clave_sesion=clave, codigo="111111"))

        # El mismo código ya no sirve, pero el otro sí.
        self.assertFalse(autenticacion.usar_codigo_de_respaldo(
            self.conn, self.cursor,
            usuario_id=self.usuario_id, clave_sesion=clave, codigo="111111"))
        self.assertTrue(autenticacion.usar_codigo_de_respaldo(
            self.conn, self.cursor,
            usuario_id=self.usuario_id, clave_sesion=clave, codigo="222222"))

        eventos = self.eventos()
        self.assertIn(autenticacion.ACCION_RESPALDO_OK, eventos)
        self.assertIn(autenticacion.ACCION_RESPALDO_FALLIDO, eventos)

    def test_codigo_inexistente(self):
        _, clave = self.activar_segundo_factor()
        self.assertFalse(autenticacion.usar_codigo_de_respaldo(
            self.conn, self.cursor,
            usuario_id=self.usuario_id, clave_sesion=clave, codigo="999999"))

    def test_cuenta_sin_codigos(self):
        clave = self.entrar()["clave_sesion"]
        with self.assertRaises(SegundoFactorInvalidoError):
            autenticacion.usar_codigo_de_respaldo(
                self.conn, self.cursor,
                usuario_id=self.usuario_id, clave_sesion=clave, codigo="111111")


class TestTokenDeConfianza(BaseAuthTest):

    def test_token_permite_omitir_el_segundo_factor(self):
        self.activar_segundo_factor()

        token = autenticacion.generar_token_confianza(
            self.conn, self.cursor, usuario_id=self.usuario_id, horas=48)
        self.assertIsNotNone(token)
        self.assertTrue(autenticacion.token_confianza_vigente(
            self.conn, self.cursor, usuario_id=self.usuario_id, token=token))

        resultado = self.entrar(token_confianza=token, horas_confianza=48)
        self.assertEqual(resultado["estado"], autenticacion.ESTADO_COMPLETADO)
        self.assertTrue(resultado["segundo_factor_omitido"])
        self.assertIn(autenticacion.ACCION_2FA_OMITIDO, self.eventos())

    def test_token_ajeno_no_omite_el_segundo_factor(self):
        self.activar_segundo_factor()
        resultado = self.entrar(token_confianza="token-inventado", horas_confianza=48)
        self.assertEqual(resultado["estado"], autenticacion.ESTADO_SEGUNDO_FACTOR)

    def test_confianza_desactivada_no_emite_token(self):
        self.assertIsNone(autenticacion.generar_token_confianza(
            self.conn, self.cursor, usuario_id=self.usuario_id, horas=0))

    def test_token_vigente(self):
        token = autenticacion.generar_token_confianza(
            self.conn, self.cursor, usuario_id=self.usuario_id, horas=1)
        self.assertTrue(autenticacion.token_confianza_vigente(
            self.conn, self.cursor, usuario_id=self.usuario_id, token=token))
        self.assertFalse(autenticacion.token_confianza_vigente(
            self.conn, self.cursor, usuario_id=self.usuario_id, token="otro"))


class TestEstadoDeCuenta(BaseAuthTest):

    def test_resumen_de_seguridad(self):
        estado = autenticacion.estado_de_cuenta(self.conn, self.cursor, usuario_id=self.usuario_id)

        self.assertEqual(estado["nombre"], self.usuario_nombre)
        self.assertFalse(estado["segundo_factor_habilitado"])
        self.assertIsNone(estado["bloqueada_hasta"])
        self.assertEqual(estado["intentos_fallidos"], 0)

        self.activar_segundo_factor()
        estado = autenticacion.estado_de_cuenta(self.conn, self.cursor, usuario_id=self.usuario_id)
        self.assertTrue(estado["segundo_factor_habilitado"])
        self.assertTrue(estado["codigos_de_respaldo_configurados"])

    def test_cuenta_inexistente(self):
        with self.assertRaises(UsuarioInexistenteError):
            autenticacion.estado_de_cuenta(self.conn, self.cursor, usuario_id=404)


class TestRestablecimientoDeContrasena(BaseAuthTest):
    """Restablecer la contraseña sin conocerla, con un código de respaldo (SCRUM-84).

    El caso que motivó el cambio: el secreto TOTP y los códigos de respaldo
    estaban cifrados con la clave derivada de la contraseña, así que el flujo
    antiguo no podía verificarlos y el restablecimiento era imposible para quien
    la había olvidado.
    """

    def _activar_con_codigos_hash(self, codigos=("111111", "222222")):
        """Deja la cuenta con 2FA activo y los códigos en el formato de hash."""
        clave = self.entrar()["clave_sesion"]
        self.cursor.execute(
            "UPDATE Usuarios SET totp_enabled = 1, totp_secret = ?, backup_codes = ? WHERE id = ?",
            (
                EncryptionManager.encrypt_str_with_key("JBSWY3DPEHPK3PXP", clave),
                autenticacion._codigos_como_hash(list(codigos)),
                self.usuario_id,
            ),
        )
        self.conn.commit()
        return clave

    def _guardado(self):
        self.cursor.execute("SELECT backup_codes FROM Usuarios WHERE id = ?", (self.usuario_id,))
        return self.cursor.fetchone()[0]

    # ------------------------------------------------------------------ #

    def test_los_codigos_nuevos_se_guardan_como_hash(self):
        secreto = "JBSWY3DPEHPK3PXP"
        codigos = autenticacion.activar_segundo_factor(
            self.conn, self.cursor, usuario_id=self.usuario_id,
            clave_sesion=self.entrar()["clave_sesion"],
            secreto=secreto, codigo=pyotp.TOTP(secreto).now(),
        )

        guardado = self._guardado()
        self.assertTrue(guardado.startswith(autenticacion.PREFIJO_CODIGOS_HASH))
        for codigo in codigos:
            self.assertNotIn(codigo, guardado, "el código no debe quedar en claro")

    def test_los_codigos_antiguos_migran_en_el_siguiente_acceso(self):
        self.activar_segundo_factor(respaldo="111111,222222")
        self.assertFalse(self._guardado().startswith(autenticacion.PREFIJO_CODIGOS_HASH))

        self.entrar()

        self.assertTrue(self._guardado().startswith(autenticacion.PREFIJO_CODIGOS_HASH))
        self.assertIn(autenticacion.ACCION_RESPALDO_MIGRADO, self.eventos())
        # Migrar no invalida nada: los mismos códigos siguen sirviendo.
        self.assertTrue(autenticacion.usar_codigo_de_respaldo(
            self.conn, self.cursor, usuario_id=self.usuario_id,
            clave_sesion=self.entrar()["clave_sesion"], codigo="111111"))

    def test_restablecimiento_completo(self):
        self._activar_con_codigos_hash()

        resultado = autenticacion.verificar_codigo_de_respaldo(
            self.conn, self.cursor, nombre=self.usuario_nombre, codigo="111111")
        self.assertEqual(resultado["usuario_id"], self.usuario_id)

        autenticacion.restablecer_contrasena(
            self.conn, self.cursor, usuario_id=self.usuario_id,
            nombre=self.usuario_nombre, contrasena_nueva="Nueva-2026!")

        # El segundo factor se reinició: hay que volver a inscribirlo.
        estado = autenticacion.estado_de_cuenta(
            self.conn, self.cursor, usuario_id=self.usuario_id)
        self.assertFalse(estado["segundo_factor_habilitado"])
        self.assertFalse(estado["codigos_de_respaldo_configurados"])

        # Se entra con la nueva y sin segundo factor; la anterior ya no vale.
        self.assertEqual(self.entrar("Nueva-2026!")["estado"], autenticacion.ESTADO_COMPLETADO)
        with self.assertRaises(CredencialesInvalidasError):
            self.entrar(CONTRASENA)

        self.assertIn(autenticacion.ACCION_RESTABLECIMIENTO_OK, self.eventos())

    def test_el_codigo_usado_no_vuelve_a_servir(self):
        self._activar_con_codigos_hash()

        autenticacion.verificar_codigo_de_respaldo(
            self.conn, self.cursor, nombre=self.usuario_nombre, codigo="111111")

        with self.assertRaises(CredencialesInvalidasError):
            autenticacion.verificar_codigo_de_respaldo(
                self.conn, self.cursor, nombre=self.usuario_nombre, codigo="111111")

        # El otro código sigue disponible.
        self.assertEqual(
            autenticacion.verificar_codigo_de_respaldo(
                self.conn, self.cursor, nombre=self.usuario_nombre, codigo="222222")["nombre"],
            self.usuario_nombre,
        )

    def test_el_error_no_revela_si_la_cuenta_existe(self):
        self._activar_con_codigos_hash()

        for nombre, codigo in ((self.usuario_nombre, "000000"), ("no-existe", "111111")):
            with self.subTest(nombre=nombre):
                with self.assertRaises(CredencialesInvalidasError):
                    autenticacion.verificar_codigo_de_respaldo(
                        self.conn, self.cursor, nombre=nombre, codigo=codigo)

        self.assertIn(autenticacion.ACCION_RESTABLECIMIENTO_FALLIDO, self.eventos())

    def test_los_intentos_fallidos_bloquean_la_cuenta(self):
        self._activar_con_codigos_hash()

        for _intento in range(5):
            with self.assertRaises(CredencialesInvalidasError):
                autenticacion.verificar_codigo_de_respaldo(
                    self.conn, self.cursor, nombre=self.usuario_nombre, codigo="000000")

        # Ni siquiera el código correcto pasa mientras la cuenta esté bloqueada.
        with self.assertRaises(CuentaBloqueadaError):
            autenticacion.verificar_codigo_de_respaldo(
                self.conn, self.cursor, nombre=self.usuario_nombre, codigo="111111")

    def test_el_formato_antiguo_avisa_en_vez_de_fallar_en_silencio(self):
        self.activar_segundo_factor(respaldo="111111,222222")

        with self.assertRaises(DatosInvalidosError):
            autenticacion.verificar_codigo_de_respaldo(
                self.conn, self.cursor, nombre=self.usuario_nombre, codigo="111111")

    def test_contrasena_nueva_debil_o_corta_se_rechaza(self):
        self._activar_con_codigos_hash()
        autenticacion.verificar_codigo_de_respaldo(
            self.conn, self.cursor, nombre=self.usuario_nombre, codigo="111111")

        for nueva in ("corta", "solominusculas"):
            with self.subTest(contrasena=nueva):
                with self.assertRaises(DatosInvalidosError):
                    autenticacion.restablecer_contrasena(
                        self.conn, self.cursor, usuario_id=self.usuario_id,
                        nombre=self.usuario_nombre, contrasena_nueva=nueva)


class TestNoRegresionDeCifrado(BaseAuthTest):
    """Lo que no puede romperse: los documentos ya cifrados siguen abriéndose."""

    def test_la_clave_de_sesion_es_estable_entre_accesos(self):
        primero = self.entrar()
        segundo = self.entrar()

        self.assertEqual(primero["clave_sesion"], segundo["clave_sesion"])

    def test_documento_cifrado_antes_del_cambio_se_sigue_descifrando(self):
        contenido = b"%PDF-1.4 documento previo al refactor\n%%EOF\n"

        # Sesión 1: se guarda el documento cifrado con la clave derivada.
        primera = self.entrar()
        self.comandos.iniciar_sesion(self.usuario_id, self.usuario_nombre, primera["clave_sesion"])
        creado = self.comandos.agregar_documento_bytes("previo.pdf", contenido)
        self.comandos.cerrar_sesion()

        # Sesión 2: se vuelve a autenticar y se descifra con la clave nueva.
        segunda = self.entrar()
        self.assertEqual(segunda["clave_sesion"], primera["clave_sesion"])
        self.comandos.iniciar_sesion(self.usuario_id, self.usuario_nombre, segunda["clave_sesion"])

        datos, nombre = self.comandos.abrir_documento(creado["id"])
        self.assertEqual(datos, contenido)
        self.assertEqual(nombre, "previo.pdf")
        self.assertEqual(len(self.comandos.listar_documentos()), 1)


if __name__ == "__main__":
    unittest.main()