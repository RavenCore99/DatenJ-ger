# Copyright (c) 2024 DatenJäger. All rights reserved.
# tests/test_servidor.py - el puente HTTP expone la capa de comandos

"""Pruebas del servidor local (SCRUM-21).

Levanta uvicorn sobre un puerto libre y consume la API con `urllib` de la
biblioteca estándar: se prueba el camino HTTP real, no una llamada en
proceso, y no hace falta ninguna dependencia de cliente.
"""

from __future__ import annotations

import base64
import json
import socket
import threading
import unittest
import urllib.error
import urllib.request

import pyotp
import uvicorn

from tests.soporte import BaseBackendTest, PDF_MINIMO
from backend import server
from backend.services import autenticacion
from database import hash_contrasena
from encryption import EncryptionManager

CONTRASENA = "Secreta-2026!"

TOKEN = "token-de-prueba-para-el-puente"


def puerto_libre() -> int:
    with socket.socket() as sonda:
        sonda.bind(("127.0.0.1", 0))
        return sonda.getsockname()[1]


class TestServidor(BaseBackendTest):

    def setUp(self):
        super().setUp()
        self.cursor.execute(
            "UPDATE Usuarios SET contrasena = ? WHERE id = ?",
            (hash_contrasena(CONTRASENA), self.usuario_id),
        )
        self.conn.commit()

        self.puerto = puerto_libre()
        app, self.comandos_servidor = server.crear_servicio(self.db_path, token=TOKEN)

        configuracion = uvicorn.Config(
            app, host="127.0.0.1", port=self.puerto, log_level="error",
        )
        self.servidor = uvicorn.Server(configuracion)
        self.hilo = threading.Thread(target=self.servidor.run, daemon=True)
        self.hilo.start()

        for _intento in range(200):
            if self.servidor.started:
                break
            threading.Event().wait(0.05)
        else:
            self.fail("El servidor no arrancó a tiempo")

    def tearDown(self):
        self.servidor.should_exit = True
        self.hilo.join(timeout=10)
        # La conexión del proceso servidor es independiente de la de la prueba.
        try:
            self.comandos_servidor.state.conn.close()
        except Exception:
            pass
        super().tearDown()

    # ------------------------------------------------------------------ #
    # Cliente mínimo
    # ------------------------------------------------------------------ #

    def pedir(self, metodo: str, ruta: str, cuerpo=None, token: str | None = TOKEN):
        """Ejecuta una petición y devuelve (estado, cuerpo_decodificado)."""
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        peticion = urllib.request.Request(
            f"http://127.0.0.1:{self.puerto}{ruta}", data=datos, method=metodo,
        )
        if datos:
            peticion.add_header("Content-Type", "application/json")
        if token is not None:
            peticion.add_header("X-DatenJager-Token", token)

        try:
            with urllib.request.urlopen(peticion, timeout=10) as respuesta:
                return respuesta.status, json.loads(respuesta.read() or b"null")
        except urllib.error.HTTPError as error:
            try:
                crudo = error.read()
                return error.code, (json.loads(crudo) if crudo else {})
            finally:
                error.close()

    def heredar_sesion(self):
        estado, _cuerpo = self.pedir("POST", "/api/sesion/heredar", {
            "usuario_id": self.usuario_id,
            "nombre": self.usuario_nombre,
            "session_key": base64.b64encode(b"clave-de-sesion").decode(),
        })
        self.assertEqual(estado, 200)

    # ------------------------------------------------------------------ #
    # Acceso
    # ------------------------------------------------------------------ #

    def test_salud_no_exige_token(self):
        estado, cuerpo = self.pedir("GET", "/api/salud", token=None)
        self.assertEqual(estado, 200)
        self.assertEqual(cuerpo["estado"], "ok")
        self.assertFalse(cuerpo["autenticado"])

    def test_sin_token_no_se_puede_operar(self):
        estado, cuerpo = self.pedir("GET", "/api/documentos", token=None)
        self.assertEqual(estado, 401)
        self.assertEqual(cuerpo["detail"]["tipo"], "NoAutenticadoError")

    def test_token_incorrecto_no_se_puede_operar(self):
        estado, _cuerpo = self.pedir("GET", "/api/documentos", token="otro-token")
        self.assertEqual(estado, 401)

    # ------------------------------------------------------------------ #
    # Sesión
    # ------------------------------------------------------------------ #

    def test_sin_sesion_los_comandos_de_negocio_responden_401(self):
        estado, cuerpo = self.pedir("GET", "/api/documentos")
        self.assertEqual(estado, 401)
        self.assertEqual(cuerpo["detail"]["tipo"], "NoAutenticadoError")

    def test_heredar_sesion_y_cerrarla(self):
        self.heredar_sesion()

        estado, cuerpo = self.pedir("GET", "/api/sesion")
        self.assertEqual(estado, 200)
        self.assertTrue(cuerpo["autenticado"])
        self.assertEqual(cuerpo["usuario_nombre"], self.usuario_nombre)

        estado, _cuerpo = self.pedir("DELETE", "/api/sesion")
        self.assertEqual(estado, 200)
        self.assertFalse(self.pedir("GET", "/api/sesion")[1]["autenticado"])

    def test_acceso_por_http(self):
        estado, cuerpo = self.pedir("POST", "/api/sesion",
                                    {"nombre": self.usuario_nombre, "contrasena": CONTRASENA})

        self.assertEqual(estado, 200)
        self.assertEqual(cuerpo["estado"], "completado")
        self.assertTrue(cuerpo["autenticado"])
        self.assertNotIn("clave_sesion", cuerpo)

        # La sesión queda abierta para el resto de rutas.
        self.assertEqual(self.pedir("GET", "/api/documentos")[0], 200)

    def test_la_clave_de_sesion_no_viaja_en_la_respuesta(self):
        _estado, cuerpo = self.pedir("POST", "/api/sesion",
                                     {"nombre": self.usuario_nombre, "contrasena": CONTRASENA})

        for campo in ("clave_sesion", "session_key", "clave"):
            self.assertNotIn(campo, cuerpo)

    def test_acceso_con_contrasena_incorrecta(self):
        estado, cuerpo = self.pedir("POST", "/api/sesion",
                                    {"nombre": self.usuario_nombre, "contrasena": "mal"})
        self.assertEqual(estado, 401)
        self.assertEqual(cuerpo["detail"]["tipo"], "CredencialesInvalidasError")

    def test_usuario_inexistente_responde_igual_que_contrasena_mala(self):
        estado, _cuerpo = self.pedir("POST", "/api/sesion",
                                     {"nombre": "fantasma", "contrasena": CONTRASENA})
        self.assertEqual(estado, 401)

    def test_cuenta_bloqueada_responde_423(self):
        for _intento in range(5):
            self.pedir("POST", "/api/sesion",
                       {"nombre": self.usuario_nombre, "contrasena": "mal"})

        estado, cuerpo = self.pedir("POST", "/api/sesion",
                                    {"nombre": self.usuario_nombre, "contrasena": CONTRASENA})
        self.assertEqual(estado, 423)
        self.assertEqual(cuerpo["detail"]["tipo"], "CuentaBloqueadaError")

    def test_segundo_factor_por_http(self):
        secreto = "JBSWY3DPEHPK3PXP"
        clave = autenticacion.autenticar(
            self.conn, self.cursor, nombre=self.usuario_nombre, contrasena=CONTRASENA)["clave_sesion"]
        self.cursor.execute(
            "UPDATE Usuarios SET totp_enabled = 1, totp_secret = ? WHERE id = ?",
            (EncryptionManager.encrypt_str_with_key(secreto, clave), self.usuario_id),
        )
        self.conn.commit()

        estado, cuerpo = self.pedir("POST", "/api/sesion",
                                    {"nombre": self.usuario_nombre, "contrasena": CONTRASENA})
        self.assertEqual(estado, 200)
        self.assertEqual(cuerpo["estado"], "segundo_factor")
        self.assertFalse(cuerpo["autenticado"])

        # Con el código equivocado no se abre la sesión.
        estado, _cuerpo = self.pedir("POST", "/api/sesion/2fa", {"codigo": "000000"})
        self.assertEqual(estado, 401)

        estado, cuerpo = self.pedir("POST", "/api/sesion/2fa",
                                    {"codigo": pyotp.TOTP(secreto).now()})
        self.assertEqual(estado, 200)
        self.assertEqual(cuerpo["estado"], "completado")
        self.assertTrue(cuerpo["autenticado"])
        self.assertIsNotNone(cuerpo["token_confianza"])

    def test_codigo_de_respaldo_por_http(self):
        secreto = "JBSWY3DPEHPK3PXP"
        clave = autenticacion.autenticar(
            self.conn, self.cursor, nombre=self.usuario_nombre, contrasena=CONTRASENA)["clave_sesion"]
        self.cursor.execute(
            "UPDATE Usuarios SET totp_enabled = 1, totp_secret = ?, backup_codes = ? WHERE id = ?",
            (
                EncryptionManager.encrypt_str_with_key(secreto, clave),
                EncryptionManager.encrypt_str_with_key("111111", clave),
                self.usuario_id,
            ),
        )
        self.conn.commit()

        self.pedir("POST", "/api/sesion",
                   {"nombre": self.usuario_nombre, "contrasena": CONTRASENA})

        estado, cuerpo = self.pedir("POST", "/api/sesion/respaldo", {"codigo": "111111"})
        self.assertEqual(estado, 200)
        self.assertEqual(cuerpo["estado"], "completado")
        self.assertTrue(cuerpo["autenticado"])

    def test_estado_de_cuenta_por_http(self):
        self.heredar_sesion()
        estado, cuerpo = self.pedir("GET", "/api/cuenta")
        self.assertEqual(estado, 200)
        self.assertEqual(cuerpo["nombre"], self.usuario_nombre)
        self.assertFalse(cuerpo["segundo_factor_habilitado"])

    def test_clave_de_sesion_invalida(self):
        estado, cuerpo = self.pedir("POST", "/api/sesion/heredar", {
            "usuario_id": 1, "nombre": "raven", "session_key": "***no-base64***"})
        self.assertEqual(estado, 422)
        self.assertEqual(cuerpo["detail"]["tipo"], "DatosInvalidosError")

    # ------------------------------------------------------------------ #
    # Documentos
    # ------------------------------------------------------------------ #

    def test_ciclo_documental_por_http(self):
        self.heredar_sesion()

        estado, creado = self.pedir("POST", "/api/documentos", {
            "nombre": "afiliacion.pdf",
            "contenido_b64": base64.b64encode(PDF_MINIMO).decode(),
            "descripcion": "EPS",
            "cedula": "1023", "nombres": "Ana Diaz", "empresa": "Minera Ubaté",
        })
        self.assertEqual(estado, 201)
        documento_id = creado["id"]
        self.assertEqual(creado["tamano"], len(PDF_MINIMO))

        estado, listado = self.pedir("GET", "/api/documentos")
        self.assertEqual(estado, 200)
        self.assertEqual(len(listado), 1)
        self.assertEqual(self.pedir("GET", "/api/documentos/conteo")[1]["total"], 1)

        estado, descarga = self.pedir("GET", f"/api/documentos/{documento_id}/descarga")
        self.assertEqual(estado, 200)
        self.assertEqual(base64.b64decode(descarga["contenido_b64"]), PDF_MINIMO)
        self.assertEqual(descarga["nombre"], "afiliacion.pdf")

        estado, actualizado = self.pedir("PATCH", f"/api/documentos/{documento_id}",
                                        {"nombre": "renombrado.pdf"})
        self.assertEqual(estado, 200)
        self.assertEqual(actualizado["nombre"], "renombrado.pdf")

        estado, _cuerpo = self.pedir("DELETE", f"/api/documentos/{documento_id}")
        self.assertEqual(estado, 200)
        self.assertEqual(self.pedir("GET", "/api/documentos/conteo")[1]["total"], 0)

    def test_errores_de_negocio_llegan_con_su_codigo(self):
        self.heredar_sesion()

        # 404 documento inexistente
        estado, cuerpo = self.pedir("GET", "/api/documentos/404")
        self.assertEqual(estado, 404)
        self.assertEqual(cuerpo["detail"]["tipo"], "NoEncontradoError")

        # 422 alta sin contenido ni ruta
        estado, cuerpo = self.pedir("POST", "/api/documentos", {"nombre": "vacio.pdf"})
        self.assertEqual(estado, 422)
        self.assertEqual(cuerpo["detail"]["tipo"], "DatosInvalidosError")

        # 422 base64 inválido
        estado, _cuerpo = self.pedir("POST", "/api/documentos",
                                     {"nombre": "x.pdf", "contenido_b64": "***"})
        self.assertEqual(estado, 422)

    # ------------------------------------------------------------------ #
    # Personas, auditoría y reportes
    # ------------------------------------------------------------------ #

    def test_ciclo_de_personas_por_http(self):
        self.heredar_sesion()

        estado, creada = self.pedir("POST", "/api/personas",
                                    {"cedula": "1023", "nombres": "Ana Diaz",
                                     "empresa": "Minera Ubaté"})
        self.assertEqual(estado, 201)

        # 409 cédula duplicada
        estado, cuerpo = self.pedir("POST", "/api/personas",
                                    {"cedula": "1023", "nombres": "Otra"})
        self.assertEqual(estado, 409)
        self.assertEqual(cuerpo["detail"]["tipo"], "ConflictoError")

        estado, actualizada = self.pedir("PATCH", f"/api/personas/{creada['id']}",
                                         {"nombres": "Ana Diaz Rojas"})
        self.assertEqual(estado, 200)
        self.assertEqual(actualizada["nombres"], "Ana Diaz Rojas")

        self.assertEqual(len(self.pedir("GET", "/api/personas?buscar=Ana")[1]), 1)
        self.assertEqual(self.pedir("DELETE", f"/api/personas/{creada['id']}")[0], 200)
        self.assertEqual(self.pedir("GET", "/api/personas")[1], [])

    def test_auditoria_por_http(self):
        self.heredar_sesion()
        self.pedir("POST", "/api/personas", {"cedula": "1", "nombres": "Ana"})

        estado, eventos = self.pedir("GET", "/api/auditoria")
        self.assertEqual(estado, 200)
        self.assertTrue(any("Persona" in evento["accion"] for evento in eventos))

        self.assertGreaterEqual(self.pedir("GET", "/api/auditoria/conteo")[1]["total"], 1)
        self.assertEqual(self.pedir("GET", "/api/auditoria?accion=Persona")[0], 200)

        estado, log = self.pedir("GET", "/api/auditoria/log")
        self.assertEqual(estado, 200)
        self.assertIn("contenido", log)

        estado, limpieza = self.pedir("DELETE", "/api/auditoria")
        self.assertEqual(estado, 200)
        self.assertGreaterEqual(limpieza["eliminados"], 1)

    def test_reportes_por_http(self):
        self.heredar_sesion()
        self.pedir("POST", "/api/documentos", {
            "nombre": "uno.pdf",
            "contenido_b64": base64.b64encode(PDF_MINIMO).decode(),
        })

        estado, metricas = self.pedir("GET", "/api/reportes/estadisticas")
        self.assertEqual(estado, 200)
        self.assertEqual(metricas["total_pdfs"], 1)

        estado, inventario = self.pedir("GET", "/api/reportes/inventario")
        self.assertEqual(estado, 200)
        self.assertEqual(len(inventario["filas"]), 1)

        destino = self.ruta_temporal("reporte.csv")
        estado, cuerpo = self.pedir("POST", "/api/reportes/exportar",
                                    {"destino": destino, "formato": "csv"})
        self.assertEqual(estado, 200)
        self.assertEqual(cuerpo["destino"], destino)


class TestServidorSinToken(BaseBackendTest):
    """Sin token configurado el servicio queda abierto (uso interno/pruebas)."""

    def test_la_app_se_construye_sin_token(self):
        app, comandos = server.crear_servicio(self.db_path, token=None)
        try:
            self.assertIsNotNone(app)
            self.assertFalse(comandos.sesion_actual()["autenticado"])
        finally:
            comandos.state.conn.close()


if __name__ == "__main__":
    unittest.main()