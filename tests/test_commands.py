# Copyright (c) 2024 DatenJäger. All rights reserved.
# tests/test_commands.py - fachada de comandos y flujo completo

"""Pruebas de la capa de comandos (``backend/commands.py``)."""

from __future__ import annotations

import unittest

from tests.soporte import (
    BaseBackendTest,
    USUARIO_ID,
    assert_sin_tkinter,
)
from backend.errors import ConflictoError, NoAutenticadoError, NoEncontradoError


class TestComandosSinSesion(BaseBackendTest):

    def setUp(self):
        super().setUp()
        self.comandos.cerrar_sesion()

    def test_todos_los_comandos_de_negocio_exigen_sesion(self):
        operaciones = [
            lambda: self.comandos.listar_documentos(),
            lambda: self.comandos.obtener_documento(1),
            lambda: self.comandos.contar_documentos(),
            lambda: self.comandos.agregar_documento_bytes("a.pdf", b"x"),
            lambda: self.comandos.abrir_documento(1),
            lambda: self.comandos.actualizar_documento(1, nombre="x"),
            lambda: self.comandos.eliminar_documento(1),
            lambda: self.comandos.exportar_documento(1, self.ruta_temporal("o.pdf")),
            lambda: self.comandos.listar_personas(),
            lambda: self.comandos.obtener_persona(1),
            lambda: self.comandos.crear_persona("1", "Nadie"),
            lambda: self.comandos.actualizar_persona(1, "Nadie"),
            lambda: self.comandos.eliminar_persona(1),
            lambda: self.comandos.listar_eventos(),
            lambda: self.comandos.contar_eventos(),
            lambda: self.comandos.limpiar_historial(),
            lambda: self.comandos.log_sistema(),
            lambda: self.comandos.estadisticas_dashboard(),
            lambda: self.comandos.documentos_por_empresa(),
            lambda: self.comandos.documentos_por_dia(),
            lambda: self.comandos.datos_inventario(),
            lambda: self.comandos.exportar_inventario(self.ruta_temporal("r.pdf")),
            lambda: self.comandos.iniciar_chat(),
            lambda: self.comandos.enviar_mensaje("hola"),
            lambda: self.comandos.estado_de_cuenta(),
        ]

        for operacion in operaciones:
            with self.subTest(operacion=operacion):
                with self.assertRaises(NoAutenticadoError):
                    operacion()

    def test_estado_de_sesion(self):
        sesion = self.comandos.sesion_actual()
        self.assertFalse(sesion["autenticado"])
        self.assertIsNone(sesion["usuario_id"])
        self.assertEqual(sesion["minutos_inactividad"], 10)


class TestFlujoCompleto(BaseBackendTest):
    """Login -> carga -> consulta -> edición -> descarga -> eliminación."""

    def test_flujo_documental_de_punta_a_punta(self):
        ruta = self.crear_pdf("expediente.pdf")

        agregado = self.comandos.agregar_documento(
            ruta, descripcion="Expediente minero",
            cedula="1023", nombres="Ana Diaz", empresa="Minera Ubaté")
        documento_id = agregado["id"]

        self.assertEqual(len(self.comandos.listar_documentos()), 1)
        self.assertEqual(self.comandos.contar_documentos(), 1)

        metadata = self.comandos.obtener_documento(documento_id)
        self.assertEqual(metadata["nombres"], "Ana Diaz")

        datos, nombre = self.comandos.abrir_documento(documento_id)
        self.assertEqual(nombre, "expediente.pdf")
        self.assertTrue(datos.startswith(b"%PDF"))

        self.comandos.actualizar_documento(documento_id, nombre="expediente-final.pdf")
        self.assertEqual(self.comandos.obtener_documento(documento_id)["nombre"],
                         "expediente-final.pdf")

        descarga = self.ruta_temporal("descarga.pdf")
        self.comandos.exportar_documento(documento_id, descarga)
        self.assertTrue(descarga.endswith("descarga.pdf"))

        self.assertEqual(self.comandos.estadisticas_dashboard()["total_pdfs"], 1)
        self.assertEqual(self.comandos.eliminar_documento(documento_id)["id"], documento_id)
        self.assertEqual(self.comandos.contar_documentos(), 0)

        with self.assertRaises(NoEncontradoError):
            self.comandos.obtener_documento(documento_id)

        assert_sin_tkinter(self)

    def test_flujo_personas(self):
        creada = self.comandos.crear_persona("1023", "Ana Diaz", "Minera Ubaté")
        self.assertEqual(creada["nombres"], "Ana Diaz")

        with self.assertRaises(ConflictoError):
            self.comandos.crear_persona("1023", "Otra")

        self.comandos.actualizar_persona(creada["id"], "Ana Diaz Rojas", "Minera SAS")
        self.assertEqual(self.comandos.obtener_persona(creada["id"])["empresa"], "Minera SAS")

        self.assertEqual(self.comandos.eliminar_persona(creada["id"])["id"], creada["id"])
        self.assertEqual(self.comandos.listar_personas(), [])

    def test_auditoria_registra_y_limpia(self):
        self.comandos.registrar_evento("Evento manual")
        self.assertGreaterEqual(self.comandos.contar_eventos(), 1)
        self.assertTrue(self.comandos.listar_eventos(accion="manual"))
        self.comandos.limpiar_historial()
        self.assertEqual(self.comandos.contar_eventos(), 1)   # queda la constancia

    def test_log_sistema(self):
        contenido, origen = self.comandos.log_sistema(self.tmpdir)
        self.assertIn("DatenJäger", contenido)
        self.assertTrue(origen)

    def test_sesion_se_cierra_y_limpia(self):
        self.comandos.iniciar_sesion(USUARIO_ID, "raven", b"k")
        self.assertTrue(self.comandos.sesion_actual()["autenticado"])

        self.comandos.cerrar_sesion()
        sesion = self.comandos.sesion_actual()
        self.assertFalse(sesion["autenticado"])
        self.assertIsNone(sesion["usuario_nombre"])

    def test_catalogo_de_operaciones_pendientes(self):
        pendientes = self.comandos.operaciones_pendientes()

        # El acceso y el segundo factor ya viven en esta capa (SCRUM-22)...
        self.assertNotIn("login", pendientes)
        self.assertNotIn("login_2fa", pendientes)

        # ...y la gestión de cuenta tampoco sigue pendiente (SCRUM-25).
        for operacion in ("setup_2fa", "cambio_contrasena", "confianza_dispositivo"):
            self.assertNotIn(operacion, pendientes)

        # Lo único que queda fuera es el alta de usuario.
        self.assertEqual(list(pendientes), ["registro"])
        self.assertTrue(all(pendientes.values()))



    def test_chat_inicia_con_el_usuario_autenticado(self):
        chat = self.comandos.iniciar_chat("contexto de prueba")
        self.assertEqual(chat.usuario_nombre, self.usuario_nombre)
        self.comandos.limpiar_chat()
        self.assertEqual(chat.history, [])


if __name__ == "__main__":
    unittest.main()