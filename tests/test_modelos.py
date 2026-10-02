# Copyright (c) 2024 DatenJäger. All rights reserved.
# tests/test_modelos.py - conexión de modelos: almacén, .env y prueba real

"""Pruebas del servicio de conexión de modelos.

Cubren lo que se añadió para que el panel deje la credencial donde el asistente
la lee (el `.env`) y para que «Probar conexión» sea una prueba de verdad y no un
adorno: sin credencial no hay nada que probar, y con un endpoint inalcanzable el
resultado es un fallo explicado, no una excepción.
"""

import os
import stat
import tempfile
import unittest
from pathlib import Path

from backend.services import modelos, proveedores


class BaseModelosTest(unittest.TestCase):
    """Raíz temporal con su propio `.env`, para no tocar el del proyecto."""

    def setUp(self):
        self._carpeta = tempfile.TemporaryDirectory()
        self.raiz = Path(self._carpeta.name)

        # El `.env` del proyecto no debe influir: se aísla el entorno.
        self._entorno_previo = os.environ.pop(modelos.VARIABLE_ENTORNO, None)

        (self.raiz / modelos.NOMBRE_ENV).write_text(
            "# DatenJäger — Variables de entorno\n"
            "# NO subir este archivo a control de versiones\n"
            "\n"
            "OTRA_VARIABLE=se-conserva\n",
            encoding="utf-8",
        )

    def tearDown(self):
        if self._entorno_previo is not None:
            os.environ[modelos.VARIABLE_ENTORNO] = self._entorno_previo
        self._carpeta.cleanup()

    def leer_env(self) -> str:
        return (self.raiz / modelos.NOMBRE_ENV).read_text(encoding="utf-8")


class GuardarEnEnvTest(BaseModelosTest):
    def test_guardar_escribe_la_clave_en_el_env(self):
        modelos.guardar(self.raiz, api_key="clave-de-prueba")

        self.assertIn(f"{modelos.VARIABLE_ENTORNO}=clave-de-prueba", self.leer_env())

    def test_guardar_conserva_el_resto_del_archivo(self):
        modelos.guardar(self.raiz, api_key="clave-de-prueba")
        contenido = self.leer_env()

        self.assertIn("OTRA_VARIABLE=se-conserva", contenido)
        self.assertIn("# NO subir este archivo a control de versiones", contenido)

    def test_el_env_queda_con_permisos_restringidos(self):
        modelos.guardar(self.raiz, api_key="clave-de-prueba")
        modo = stat.S_IMODE((self.raiz / modelos.NOMBRE_ENV).stat().st_mode)

        self.assertEqual(modo, 0o600)

    def test_reemplaza_la_clave_anterior_sin_duplicar_la_linea(self):
        modelos.guardar(self.raiz, api_key="primera")
        modelos.guardar(self.raiz, api_key="segunda")
        contenido = self.leer_env()

        self.assertEqual(contenido.count(f"{modelos.VARIABLE_ENTORNO}="), 1)
        self.assertIn(f"{modelos.VARIABLE_ENTORNO}=segunda", contenido)

    def test_crea_el_env_si_no_existe(self):
        (self.raiz / modelos.NOMBRE_ENV).unlink()
        modelos.guardar(self.raiz, api_key="clave-de-prueba")

        self.assertIn(f"{modelos.VARIABLE_ENTORNO}=clave-de-prueba", self.leer_env())


class ClaveVigenteTest(BaseModelosTest):
    def test_el_env_manda_sobre_el_entorno_del_proceso(self):
        # `os.getenv` devuelve lo cargado al arrancar; si mandara, una clave
        # escrita desde el panel no surtiría efecto hasta reiniciar.
        os.environ[modelos.VARIABLE_ENTORNO] = "clave-vieja-del-proceso"
        modelos.guardar(self.raiz, api_key="clave-nueva")

        self.assertEqual(modelos.clave(self.raiz), "clave-nueva")

    def test_sin_env_se_usa_el_entorno_del_proceso(self):
        (self.raiz / modelos.NOMBRE_ENV).unlink()
        os.environ[modelos.VARIABLE_ENTORNO] = "clave-exportada"

        self.assertEqual(modelos.clave(self.raiz), "clave-exportada")

    def test_quitar_la_credencial_la_retira_de_los_dos_sitios(self):
        modelos.guardar(self.raiz, api_key="clave-de-prueba")
        os.environ[modelos.VARIABLE_ENTORNO] = "clave-vieja-del-proceso"

        resultado = modelos.guardar(self.raiz, quitar_clave=True)

        self.assertNotIn(f"{modelos.VARIABLE_ENTORNO}=", self.leer_env())
        self.assertFalse(resultado["clave_configurada"])
        self.assertIsNone(modelos.clave(self.raiz))

    def test_el_estado_no_devuelve_la_clave(self):
        modelos.guardar(self.raiz, api_key="clave-de-prueba")
        resultado = modelos.estado(self.raiz)

        self.assertNotIn("clave-de-prueba", repr(resultado))
        self.assertTrue(resultado["clave_configurada"])
        self.assertEqual(resultado["origen_clave"], "entorno")


class ProbarConexionTest(BaseModelosTest):
    def test_sin_credencial_no_hay_nada_que_probar(self):
        resultado = modelos.probar(self.raiz)

        self.assertFalse(resultado["ok"])
        self.assertIn("No hay credencial", resultado["mensaje"])

    def test_un_endpoint_inalcanzable_falla_explicado(self):
        # Se apunta a un puerto local cerrado: la prueba debe contarlo, no
        # reventar con una excepción de red.
        modelos.guardar(
            self.raiz,
            api_key="clave-de-prueba",
            endpoint="http://127.0.0.1:9",
        )

        resultado = modelos.probar(self.raiz, tiempo_limite=2.0)

        self.assertFalse(resultado["ok"])
        self.assertIn("No se pudo contactar", resultado["mensaje"])
        self.assertTrue(resultado["detalle"])

    def test_un_proveedor_sin_endpoint_lo_dice(self):
        """Un endpoint propio sin URL base no se puede probar: se dice, no se finge.

        Antes esta prueba afirmaba «solo Google Gemini tiene prueba
        implementada». Eso era una limitación del servicio y ya no existe: ahora
        se prueba cualquier proveedor del catálogo, y lo que falta es la URL.
        """
        modelos.guardar(self.raiz, api_key="clave-de-prueba", proveedor="compatible")

        resultado = modelos.probar(self.raiz)

        self.assertFalse(resultado["ok"])
        self.assertIn("punto de conexión", resultado["mensaje"])
        self.assertIn("Otro endpoint compatible con OpenAI", resultado["mensaje"])


class CatalogoTest(BaseModelosTest):
    def test_rechaza_un_proveedor_desconocido(self):
        from backend.errors import DatosInvalidosError

        with self.assertRaises(DatosInvalidosError):
            modelos.guardar(self.raiz, proveedor="inventado")


class SaludDeLaConexionTest(BaseModelosTest):
    """El verde no lo pone tener una clave, sino haberla probado de verdad."""

    def test_sin_credencial_no_hay_nada_configurado(self):
        self.assertEqual(modelos.estado(self.raiz)["salud"], modelos.SALUD_SIN_CONFIGURAR)

    def test_con_credencial_sin_probar_queda_sin_verificar(self):
        modelos.guardar(self.raiz, api_key="clave-de-prueba")

        self.assertEqual(modelos.estado(self.raiz)["salud"], modelos.SALUD_SIN_VERIFICAR)

    def test_una_prueba_correcta_pone_el_verde(self):
        modelos.guardar(self.raiz, api_key="clave-de-prueba")
        modelos.registrar_prueba(
            self.raiz, {"ok": True, "mensaje": "acepta"}, modelos.PRUEBA_CONEXION)

        self.assertEqual(modelos.estado(self.raiz)["salud"], modelos.SALUD_OK)

    def test_una_prueba_fallida_no_se_queda_en_verde(self):
        modelos.guardar(self.raiz, api_key="clave-de-prueba")
        modelos.registrar_prueba(
            self.raiz, {"ok": True, "mensaje": "acepta"}, modelos.PRUEBA_CONEXION)
        modelos.registrar_prueba(
            self.raiz, {"ok": False, "mensaje": "rechazada"}, modelos.PRUEBA_RESPUESTA)

        estado = modelos.estado(self.raiz)

        self.assertEqual(estado["salud"], modelos.SALUD_ERROR)
        self.assertEqual(estado["ultima_prueba"]["mensaje"], "rechazada")

    def test_cambiar_la_clave_invalida_la_prueba_anterior(self):
        modelos.guardar(self.raiz, api_key="clave-de-prueba")
        modelos.registrar_prueba(
            self.raiz, {"ok": True, "mensaje": "acepta"}, modelos.PRUEBA_CONEXION)

        modelos.guardar(self.raiz, api_key="otra-clave")

        # El verde describía la credencial anterior: con otra clave vuelve a
        # «sin verificar», en vez de quedarse verde por inercia.
        self.assertEqual(modelos.estado(self.raiz)["salud"], modelos.SALUD_SIN_VERIFICAR)

    def test_quitar_la_credencial_deja_el_estado_sin_configurar(self):
        modelos.guardar(self.raiz, api_key="clave-de-prueba")
        modelos.registrar_prueba(
            self.raiz, {"ok": True, "mensaje": "acepta"}, modelos.PRUEBA_CONEXION)

        modelos.guardar(self.raiz, quitar_clave=True)

        self.assertEqual(modelos.estado(self.raiz)["salud"], modelos.SALUD_SIN_CONFIGURAR)


class PermisosDelEnvTest(BaseModelosTest):
    """El `.env` lleva la credencial en claro: sus permisos son parte del asunto."""

    def test_corrige_un_env_legible_por_otros(self):
        ruta = self.raiz / modelos.NOMBRE_ENV
        os.chmod(ruta, 0o644)

        estado = modelos.estado(self.raiz)

        self.assertTrue(estado["permisos_env_corregidos"])
        self.assertEqual(stat.S_IMODE(ruta.stat().st_mode), 0o600)

    def test_no_toca_un_env_ya_restringido(self):
        ruta = self.raiz / modelos.NOMBRE_ENV
        os.chmod(ruta, 0o600)

        self.assertFalse(modelos.estado(self.raiz)["permisos_env_corregidos"])
        self.assertEqual(stat.S_IMODE(ruta.stat().st_mode), 0o600)


class CandidatosYEndpointTest(BaseModelosTest):
    def test_el_elegido_va_primero_y_los_conocidos_detras(self):
        modelos.guardar(self.raiz, api_key="clave-de-prueba", modelo="gemini-3.5-flash")
        modelos.registrar_prueba(
            self.raiz,
            {
                "ok": True,
                "mensaje": "acepta",
                "modelos_disponibles": ["gemini-3.5-flash", "gemini-9"],
            },
            modelos.PRUEBA_CONEXION,
        )

        candidatos = modelos.modelos_candidatos(self.raiz)

        self.assertEqual(candidatos[0], "gemini-3.5-flash")
        self.assertIn("gemini-9", candidatos)
        # Los alias del catálogo cierran la lista: nunca se queda sin respaldo.
        self.assertIn("gemini-flash-latest", candidatos)
        self.assertEqual(len(candidatos), len(set(candidatos)))

    def test_el_respaldo_descarta_los_modelos_que_no_conversan(self):
        modelos.guardar(self.raiz, api_key="clave-de-prueba", modelo="mi-modelo")
        modelos.registrar_prueba(
            self.raiz,
            {
                "ok": True,
                "mensaje": "acepta",
                "modelos_disponibles": ["mi-modelo", "imagen-4", "gemini-3.5-flash"],
            },
            modelos.PRUEBA_CONEXION,
        )

        candidatos = modelos.modelos_candidatos(self.raiz)

        # El elegido se respeta aunque no parezca de conversación: lo escogió el
        # usuario. Lo que se descarta es el respaldo que no generaría texto.
        self.assertEqual(candidatos[0], "mi-modelo")
        self.assertIn("gemini-3.5-flash", candidatos)
        self.assertNotIn("imagen-4", candidatos)

    def test_una_url_escrita_manda_sobre_lo_deducido(self):
        """El panel no la manda cuando el proveedor la tiene fijada; si llega, manda.

        Es la única vía para un endpoint propio, que por definición no está en el
        catálogo. El proveedor, en cambio, sí se deduce de la clave.
        """
        modelos.guardar(
            self.raiz, api_key="nvapi-abcdef123456", endpoint="https://mio.invalido/v1")

        estado = modelos.estado(self.raiz)

        self.assertEqual(estado["proveedor"], "nvidia")
        self.assertEqual(estado["endpoint"], "https://mio.invalido/v1")

    def test_sin_url_escrita_manda_la_del_catalogo(self):
        modelos.guardar(self.raiz, api_key="nvapi-abcdef123456")

        estado = modelos.estado(self.raiz)

        self.assertEqual(estado["proveedor"], "nvidia")
        self.assertEqual(estado["endpoint"], proveedores.ENDPOINT_NVIDIA)

    def test_una_clave_no_reconocida_respeta_el_endpoint_escrito(self):
        modelos.guardar(
            self.raiz, api_key="clave-propia", endpoint="https://mio.invalido/v1")

        self.assertEqual(modelos.estado(self.raiz)["endpoint"], "https://mio.invalido/v1")


class ModeloRetiradoTest(BaseModelosTest):
    """Un modelo retirado se sustituye al probar, en vez de dejar el 503."""

    def test_la_prueba_cambia_un_modelo_que_ya_no_existe(self):
        modelos.guardar(self.raiz, api_key="clave-de-prueba", modelo="gemini-2.0-flash")
        modelos.registrar_prueba(
            self.raiz,
            {
                "ok": True,
                "mensaje": "acepta",
                "modelos_disponibles": ["gemini-3.5-flash", "gemini-flash-latest", "imagen-4"],
            },
            modelos.PRUEBA_CONEXION,
        )

        # El guardado no está en la cuenta: se cambia por uno que sí.
        self.assertEqual(modelos.estado(self.raiz)["modelo"], "gemini-flash-latest")

    def test_no_cambia_un_modelo_que_sigue_existiendo(self):
        modelos.guardar(self.raiz, api_key="clave-de-prueba", modelo="gemini-3.5-flash")
        modelos.registrar_prueba(
            self.raiz,
            {
                "ok": True,
                "mensaje": "acepta",
                "modelos_disponibles": ["gemini-3.5-flash", "imagen-4"],
            },
            modelos.PRUEBA_CONEXION,
        )

        self.assertEqual(modelos.estado(self.raiz)["modelo"], "gemini-3.5-flash")

    def test_descarta_los_modelos_que_no_conversan(self):
        modelos.guardar(self.raiz, api_key="clave-de-prueba", modelo="retirado")
        modelos.registrar_prueba(
            self.raiz,
            {
                "ok": True,
                "mensaje": "acepta",
                "modelos_disponibles": [
                    "imagen-4",
                    "gemini-3.5-flash-tts",
                    "gemini-3.5-flash",
                ],
            },
            modelos.PRUEBA_CONEXION,
        )

        self.assertEqual(modelos.estado(self.raiz)["modelo"], "gemini-3.5-flash")


class CredencialQueElListadoNoDemuestraTest(BaseModelosTest):
    """Un listado público no prueba una credencial: hace falta un turno real."""

    @staticmethod
    def _respuesta(cuerpo: bytes):
        class Respuesta:
            def read(self):
                return cuerpo

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        return Respuesta()

    def test_un_listado_publico_no_da_la_credencial_por_buena(self):
        import urllib.error
        from unittest import mock

        modelos.guardar(self.raiz, api_key="nvapi-clave-que-no-sirve")

        def urlopen(peticion, timeout=None):
            url = getattr(peticion, "full_url", str(peticion))
            if url.endswith("/models"):
                # El listado de NVIDIA es público: responde 200 con cualquier clave.
                return self._respuesta(b'{"data": [{"id": "meta/llama-3.3-70b-instruct"}]}')
            raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)

        with mock.patch("urllib.request.urlopen", urlopen):
            resultado = modelos.probar(self.raiz)

        self.assertFalse(resultado["ok"])
        self.assertIn("rechazó la credencial", resultado["mensaje"])
        # Y el estado no se queda verde por haber listado modelos.
        self.assertEqual(modelos.estado(self.raiz)["salud"], modelos.SALUD_ERROR)


class IdentificarTest(BaseModelosTest):
    """Reconocer la clave no llama a nadie: solo aplica las reglas del catálogo."""

    def test_identifica_sin_guardar_nada(self):
        reconocido = modelos.identificar("nvapi-abcdef123456")

        self.assertTrue(reconocido["detectado"])
        self.assertEqual(reconocido["proveedor"], "nvidia")
        # Identificar no configura: el estado sigue sin credencial.
        self.assertFalse(modelos.estado(self.raiz)["clave_configurada"])


class DeteccionDeProveedorTest(unittest.TestCase):
    """De la forma de la clave salen el proveedor y la URL base."""

    def test_reconoce_gemini(self):
        for clave in ("AIzaSyClaveDeEjemplo", "AQ.Ab8ClaveNueva"):
            self.assertEqual(proveedores.detectar(clave), "gemini", clave)

    def test_reconoce_nvidia(self):
        self.assertEqual(proveedores.detectar("nvapi-abcdef123456"), "nvidia")

    def test_reconoce_openrouter_antes_que_openai(self):
        self.assertEqual(proveedores.detectar("sk-or-v1-abc"), "openrouter")
        self.assertEqual(proveedores.detectar("sk-abc"), "openai")

    def test_una_clave_desconocida_no_se_adivina(self):
        self.assertIsNone(proveedores.detectar("clave-cualquiera"))

    def test_la_url_base_viene_del_catalogo(self):
        resuelto = proveedores.resolver("nvapi-abcdef123456")

        self.assertTrue(resuelto["detectado"])
        self.assertEqual(resuelto["endpoint"], proveedores.ENDPOINT_NVIDIA)
        self.assertEqual(resuelto["variable_entorno"], "NVIDIA_API_KEY")

    def test_solo_el_endpoint_propio_es_editable(self):
        self.assertFalse(proveedores.endpoint_editable("gemini"))
        self.assertFalse(proveedores.endpoint_editable("nvidia"))
        self.assertTrue(proveedores.endpoint_editable("compatible"))

    def test_los_modelos_del_catalogo_son_alias(self):
        # Una versión fija se retira y deja de responder: fue el 503 real.
        for nombre in proveedores.modelos_de("gemini"):
            self.assertTrue(nombre.endswith("-latest"), nombre)


if __name__ == "__main__":
    unittest.main()