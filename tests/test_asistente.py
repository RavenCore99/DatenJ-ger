# Copyright (c) 2024 DatenJäger. All rights reserved.
# tests/test_asistente.py - streaming, errores de red y anclaje al proyecto

"""Pruebas del asistente de la Fase 4.

Cubren las tres cosas que no se ven en una prueba de humo: que la respuesta
llegue **por fragmentos** (RF-16), que los fallos de red se manejen sin
duplicar ni perder la conversación (`SCRUM-35`/`SCRUM-36`), y que el asistente
solo reciba **agregados** del proyecto, nunca datos personales ni secretos
(`SCRUM-61`).

No se toca la red: el servicio se prueba con sus métodos de proveedor
sustituidos, que es justo la frontera donde vive la lógica propia.
"""

from __future__ import annotations

import json
import os
import unittest
from email.message import Message
from pathlib import Path
from unittest import mock

from tests.soporte import BaseBackendTest, PDF_MINIMO
from backend.services import contexto
import chatbot


CLAVE_DE_PRUEBA = "clave-de-prueba"


def servicio(**kwargs) -> chatbot.ChatbotService:
    """Servicio con credencial ficticia: no llega a usarse contra la red."""
    kwargs.setdefault("reintentos", 1)
    return chatbot.ChatbotService("raven", api_key=CLAVE_DE_PRUEBA, **kwargs)


class TestStreamingDelAsistente(unittest.TestCase):
    """Entrega progresiva y continuidad de la conversación (RF-16, SCRUM-36)."""

    def test_entrega_los_fragmentos_en_orden(self):
        asistente = servicio()
        asistente.model_candidates = ["modelo-de-prueba"]
        asistente._fragmentos = lambda model_name, contents: iter(["Ho", "la", " mundo"])

        fragmentos = list(asistente.enviar_mensaje_stream("hola"))

        self.assertEqual(fragmentos, ["Ho", "la", " mundo"])
        # Un turno de usuario y uno del modelo: exactamente dos, ni uno más.
        self.assertEqual([turno["role"] for turno in asistente.history], ["user", "model"])
        self.assertEqual(asistente.history[1]["parts"][0]["text"], "Hola mundo")

    def test_el_fallo_a_media_respuesta_conserva_lo_que_se_vio(self):
        asistente = servicio()
        asistente.model_candidates = ["modelo-de-prueba"]

        def fragmentos_cortados(model_name, contents):
            yield "La mitad"
            raise chatbot.ErrorRedChatbot("se cortó la conexión")

        asistente._fragmentos = fragmentos_cortados

        recibidos = []
        with self.assertRaises(chatbot.ErrorRedChatbot):
            for fragmento in asistente.enviar_mensaje_stream("pregunta"):
                recibidos.append(fragmento)

        self.assertEqual(recibidos, ["La mitad"])
        # Lo que el usuario llegó a leer entra al historial: el turno siguiente
        # debe saber qué se respondió.
        self.assertEqual([turno["role"] for turno in asistente.history], ["user", "model"])
        self.assertEqual(asistente.history[1]["parts"][0]["text"], "La mitad")

    def test_un_fallo_antes_del_primer_fragmento_se_reintenta(self):
        asistente = servicio(reintentos=3)
        asistente.model_candidates = ["modelo-de-prueba"]
        intentos = {"n": 0}

        def fragmentos_inestables(model_name, contents):
            intentos["n"] += 1
            if intentos["n"] == 1:
                raise chatbot.ErrorRedChatbot("corte temporal", reintentable=True)
            yield "respuesta"

        asistente._fragmentos = fragmentos_inestables

        with mock.patch.object(chatbot.time, "sleep", lambda *_: None):
            fragmentos = list(asistente.enviar_mensaje_stream("pregunta"))

        self.assertEqual(fragmentos, ["respuesta"])
        self.assertEqual(intentos["n"], 2)
        # El reintento no duplica el turno del usuario.
        self.assertEqual([turno["role"] for turno in asistente.history], ["user", "model"])

    def test_no_se_reintenta_despues_de_haber_emitido_texto(self):
        asistente = servicio(reintentos=3)
        asistente.model_candidates = ["modelo-de-prueba"]
        intentos = {"n": 0}

        def fragmentos_cortados(model_name, contents):
            intentos["n"] += 1
            yield "algo"
            raise chatbot.ErrorRedChatbot("corte", reintentable=True)

        asistente._fragmentos = fragmentos_cortados

        with mock.patch.object(chatbot.time, "sleep", lambda *_: None):
            with self.assertRaises(chatbot.ErrorRedChatbot):
                list(asistente.enviar_mensaje_stream("pregunta"))

        # Reintentar duplicaría lo que el usuario ya leyó.
        self.assertEqual(intentos["n"], 1)

    def test_la_variante_bloqueante_devuelve_la_respuesta_completa(self):
        asistente = servicio()
        asistente.model_candidates = ["modelo-de-prueba"]
        asistente._fragmentos = lambda model_name, contents: iter(["completa"])

        self.assertEqual(asistente.enviar_mensaje("pregunta"), "completa")


class TestErroresDeRed(unittest.TestCase):
    """Traducción de los fallos del proveedor (SCRUM-35)."""

    def test_un_tiempo_agotado_es_reintentable_y_se_explica(self):
        asistente = servicio(tiempo_limite=7.0)

        fallo = asistente._traducir_fallo(TimeoutError("se agotó"))

        self.assertIsInstance(fallo, chatbot.ErrorRedChatbot)
        self.assertTrue(fallo.reintentable)
        self.assertIn("7 s", str(fallo))

    def test_un_403_no_se_reintenta_y_apunta_al_panel(self):
        import urllib.error

        asistente = servicio()
        http = urllib.error.HTTPError("https://ejemplo", 403, "Forbidden", Message(), None)

        fallo = asistente._traducir_fallo(http)

        self.assertFalse(fallo.reintentable)
        self.assertIn("panel de conexión", str(fallo))

    def test_un_429_si_se_reintenta(self):
        import urllib.error

        asistente = servicio()
        http = urllib.error.HTTPError("https://ejemplo", 429, "Too Many Requests", Message(), None)

        fallo = asistente._traducir_fallo(http)

        self.assertTrue(fallo.reintentable)
        self.assertIn("429", str(fallo))

    def test_la_prueba_de_respuesta_devuelve_lo_que_contesta_el_modelo(self):
        asistente = servicio()
        asistente.model_candidates = ["modelo-de-prueba"]
        asistente._generar_completo = lambda model_name, contents: "listo"

        resultado = asistente.probar_respuesta()

        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["respuesta"], "listo")
        self.assertEqual(resultado["modelo"], "modelo-de-prueba")

    def test_la_prueba_de_respuesta_informa_del_fallo(self):
        asistente = servicio()
        asistente.model_candidates = ["modelo-de-prueba"]

        def falla(model_name, contents):
            raise chatbot.ErrorRedChatbot("La credencial no sirve.", motivo="403")

        asistente._generar_completo = falla

        resultado = asistente.probar_respuesta()

        self.assertFalse(resultado["ok"])
        self.assertIn("credencial", resultado["mensaje"])
        self.assertEqual(resultado["detalle"], "403")

    def test_sin_credencial_no_se_construye_el_servicio(self):
        # La variable se vacía en el entorno de la prueba: `config.py` carga el
        # `.env` del proyecto al importarse y, sin esto, la prueba dependería de
        # que este equipo tenga o no una credencial configurada.
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            with self.assertRaises(chatbot.ConfiguracionChatbotError):
                chatbot.ChatbotService("raven", api_key="")


class TestContextoDelProyecto(BaseBackendTest):
    """El asistente recibe agregados reales y nada sensible (SCRUM-61)."""

    def setUp(self):
        super().setUp()
        self.comandos.agregar_documento_bytes(
            nombre="contrato_confidencial.pdf",
            datos=PDF_MINIMO,
            cedula="1023456789",
            nombres="Ana Diaz",
            empresa="Minera Ubaté",
        )

    def test_incluye_las_cifras_reales(self):
        resumen = contexto.resumen_del_proyecto(self.conn, self.cursor, self.usuario_id)

        self.assertEqual(resumen["documentos"]["total"], 1)
        self.assertEqual(resumen["titulares"], 1)
        self.assertEqual(resumen["empresas"], 1)
        self.assertGreaterEqual(resumen["auditoria"]["total"], 1)
        self.assertEqual(resumen["documentos"]["por_empresa"][0]["empresa"], "Minera Ubaté")

    def test_no_filtra_datos_personales_ni_nombres_de_archivo(self):
        bloque = contexto.contexto_del_proyecto(self.conn, self.cursor, self.usuario_id)

        for sensible in ("1023456789", "Ana Diaz", "contrato_confidencial"):
            with self.subTest(dato=sensible):
                self.assertNotIn(sensible, bloque)

    def test_la_empresa_si_es_contexto_legitimo(self):
        bloque = contexto.contexto_del_proyecto(self.conn, self.cursor, self.usuario_id)
        self.assertIn("Minera Ubaté", bloque)

    def test_declara_el_alcance_estricto(self):
        bloque = contexto.contexto_del_proyecto(self.conn, self.cursor, self.usuario_id)

        self.assertIn("ALCANCE ESTRICTO", bloque)
        self.assertIn("solo", bloque)
        self.assertIn("Nunca reveles", bloque)

    def test_el_contexto_viaja_en_el_prompt_de_cada_turno(self):
        asistente = servicio()
        asistente.set_context("CONTEXTO-DE-PRUEBA")

        self.assertIn("CONTEXTO-DE-PRUEBA", asistente._system_prompt())
        self.assertIn("DatenJäger", asistente._system_prompt())

    def test_la_capa_de_comandos_inyecta_el_contexto_al_abrir_el_chat(self):
        # La credencial se deja en el `.env` del directorio temporal de la
        # prueba: es de donde la resuelve el backend, sin tocar el real.
        (Path(self.tmpdir) / ".env").write_text(
            f"GEMINI_API_KEY={CLAVE_DE_PRUEBA}\n", encoding="utf-8")

        conversacion = self.comandos.iniciar_chat()

        self.assertIn("CONTEXTO REAL DE DATENJÄGER", conversacion.contexto)
        self.assertIn("Documentos cifrados: 1", conversacion.contexto)
        self.assertIn("Minera Ubaté", conversacion.contexto)


class RazonamientoNoSeMuestraTest(unittest.TestCase):
    """El pensamiento del modelo no es la respuesta que ve el usuario.

    Lo reportó Raven al probar la conexión: el asistente devolvía su
    planificación —«el usuario pregunta si funciono, debo responder que sí»—
    mezclada con la respuesta. Los modelos con razonamiento la devuelven como
    partes marcadas, y hay que descartarlas.
    """

    @staticmethod
    def _respuesta(cuerpo: bytes = b"", lineas=None):
        class Respuesta:
            def read(self):
                return cuerpo

            def __iter__(self):
                return iter(lineas or [])

            def __enter__(self):
                return self

            def __exit__(self, *_argumentos):
                return False

        return Respuesta()

    @staticmethod
    def _servicio():
        return chatbot.ChatbotService(
            "prueba", api_key=CLAVE_DE_PRUEBA, modelo="modelo-de-prueba")

    def test_la_respuesta_completa_descarta_el_pensamiento(self):
        cuerpo = json.dumps({
            "candidates": [{"content": {"parts": [
                {"text": "Analizo: el usuario prueba la conexion.", "thought": True},
                {"text": "Sí, funciono."},
            ]}}],
        }).encode("utf-8")

        with mock.patch(
            "urllib.request.urlopen", lambda *_a, **_k: self._respuesta(cuerpo)
        ):
            texto = self._servicio()._generar_completo("modelo-de-prueba", [])

        self.assertEqual(texto, "Sí, funciono.")
        self.assertNotIn("Analizo", texto)

    def test_los_fragmentos_descartan_el_pensamiento(self):
        def marco(trozo):
            return ("data: " + json.dumps(trozo) + "\n").encode("utf-8")

        lineas = [
            marco({"candidates": [{"content": {"parts": [
                {"text": "Pienso en la respuesta...", "thought": True}]}}]}),
            marco({"candidates": [{"content": {"parts": [{"text": "Hola."}]}}]}),
        ]

        with mock.patch(
            "urllib.request.urlopen", lambda *_a, **_k: self._respuesta(b"", lineas)
        ):
            fragmentos = list(self._servicio()._fragmentos("modelo-de-prueba", []))

        self.assertEqual(fragmentos, ["Hola."])

    def test_una_respuesta_que_solo_tiene_pensamiento_es_un_fallo(self):
        # Si todo lo que llegó era pensamiento, no hay nada que mostrar: es un
        # fallo explicado, no una respuesta vacía.
        cuerpo = json.dumps({
            "candidates": [{"content": {"parts": [
                {"text": "Solo pienso.", "thought": True}]}}],
        }).encode("utf-8")

        with mock.patch(
            "urllib.request.urlopen", lambda *_a, **_k: self._respuesta(cuerpo)
        ):
            with self.assertRaises(chatbot.ErrorRedChatbot):
                self._servicio()._generar_completo("modelo-de-prueba", [])

    def test_el_prompt_prohibe_mostrar_el_razonamiento(self):
        # El prompt es la otra mitad del arreglo: los modelos que escriben su
        # planificación como texto (los gemma) no la marcan como pensamiento, y
        # ahí solo se les puede pedir que no la escriban.
        from chatbot import SYSTEM_PROMPT

        self.assertIn("No muestres tu razonamiento", SYSTEM_PROMPT)
        self.assertIn("directamente", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()