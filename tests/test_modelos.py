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

from backend.services import modelos


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

    def test_un_proveedor_sin_prueba_lo_dice(self):
        modelos.guardar(self.raiz, api_key="clave-de-prueba", proveedor="compatible")

        resultado = modelos.probar(self.raiz)

        self.assertFalse(resultado["ok"])
        self.assertIn("Google Gemini", resultado["mensaje"])


class CatalogoTest(BaseModelosTest):
    def test_rechaza_un_proveedor_desconocido(self):
        from backend.errors import DatosInvalidosError

        with self.assertRaises(DatosInvalidosError):
            modelos.guardar(self.raiz, proveedor="inventado")


if __name__ == "__main__":
    unittest.main()