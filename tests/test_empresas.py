# Copyright (c) 2024 DatenJäger. All rights reserved.
# tests/test_empresas.py - catálogo de empresas y normalización de nombres

"""Pruebas del catálogo de empresas.

Lo que se comprueba aquí es la razón de ser de la tabla: que dos grafías de la
misma empresa **no** creen dos fichas, que el personal quede asociado a la suya,
y que la migración del texto libre antiguo deje los datos vinculados.
"""

from __future__ import annotations

import unittest

from tests.soporte import BaseBackendTest, PDF_MINIMO, assert_sin_tkinter
from backend.errors import ConflictoError, NoEncontradoError
from backend.services import documentos, empresas, personas
from database import _migrar_empresas, normalizar_empresa


class NormalizacionTest(unittest.TestCase):
    """La clave de comparación: es lo que evita las redundancias."""

    def test_las_variantes_de_escritura_dan_la_misma_clave(self):
        variantes = [
            "Minera del Norte S.A.S.",
            "minera del norte sas",
            "MINERA DEL NORTE S.A.S",
            "  Minera   del  Norte  ",
            "Minera del Norte",
        ]

        claves = {normalizar_empresa(variante) for variante in variantes}

        self.assertEqual(claves, {"minera del norte"})

    def test_los_acentos_no_separan_la_misma_palabra(self):
        self.assertEqual(
            normalizar_empresa("Minería del Norte"),
            normalizar_empresa("Mineria del Norte"),
        )

    def test_distingue_empresas_distintas(self):
        self.assertNotEqual(
            normalizar_empresa("Minera del Norte"),
            normalizar_empresa("Minera del Sur"),
        )

    def test_una_empresa_sin_nombre_no_produce_clave(self):
        for vacio in (None, "", "   ", "\n"):
            self.assertEqual(normalizar_empresa(vacio), "")


class CatalogoTest(BaseBackendTest):

    def test_alta_y_listado(self):
        creada = empresas.crear_empresa(
            self.conn, self.cursor, nombre="Minera del Norte", usuario_id=self.usuario_id)

        self.assertEqual(creada["nombre"], "Minera del Norte")
        self.assertEqual(empresas.contar_empresas(self.conn, self.cursor), 1)
        self.assertIn(empresas.ACCION_AGREGAR, self.eventos())

    def test_no_admite_el_mismo_nombre_con_otra_grafia(self):
        empresas.crear_empresa(
            self.conn, self.cursor, nombre="Minera del Norte S.A.S.", usuario_id=self.usuario_id)

        with self.assertRaises(ConflictoError):
            empresas.crear_empresa(
                self.conn, self.cursor, nombre="minera del norte", usuario_id=self.usuario_id)

        self.assertEqual(empresas.contar_empresas(self.conn, self.cursor), 1)

    def test_rechaza_un_nombre_vacio(self):
        from backend.errors import DatosInvalidosError

        with self.assertRaises(DatosInvalidosError):
            empresas.crear_empresa(self.conn, self.cursor, nombre="  ")

    def test_renombrar_alcanza_a_todo_el_personal(self):
        creada = empresas.crear_empresa(
            self.conn, self.cursor, nombre="Minera A", usuario_id=self.usuario_id)
        personas.crear_persona(
            self.conn, self.cursor, cedula="1", nombres="Ana", empresa="Minera A",
            usuario_id=self.usuario_id)
        personas.crear_persona(
            self.conn, self.cursor, cedula="2", nombres="Luis", empresa="Minera A",
            usuario_id=self.usuario_id)

        empresas.renombrar_empresa(
            self.conn, self.cursor, empresa_id=creada["id"], nombre="Minera del Norte S.A.S.",
            usuario_id=self.usuario_id)

        # El nombre del catálogo y el texto de cada persona quedan en sincronía.
        for fila in personas.listar_personas(self.conn, self.cursor):
            self.assertEqual(fila["empresa"], "Minera del Norte S.A.S.")

    def test_renombrar_no_permite_chocar_con_otra(self):
        empresas.crear_empresa(
            self.conn, self.cursor, nombre="Minera A", usuario_id=self.usuario_id)
        segunda = empresas.crear_empresa(
            self.conn, self.cursor, nombre="Minera B", usuario_id=self.usuario_id)

        with self.assertRaises(ConflictoError):
            empresas.renombrar_empresa(
                self.conn, self.cursor, empresa_id=segunda["id"], nombre="Minera A",
                usuario_id=self.usuario_id)

    def test_fusionar_mueve_el_personal_y_retira_el_origen(self):
        origen = empresas.crear_empresa(
            self.conn, self.cursor, nombre="Minera A", usuario_id=self.usuario_id)
        destino = empresas.crear_empresa(
            self.conn, self.cursor, nombre="Minera B", usuario_id=self.usuario_id)
        personas.crear_persona(
            self.conn, self.cursor, cedula="1", nombres="Ana", empresa="Minera A",
            usuario_id=self.usuario_id)

        resultado = empresas.fusionar_empresas(
            self.conn, self.cursor, origen_id=origen["id"], destino_id=destino["id"],
            usuario_id=self.usuario_id)

        self.assertEqual(resultado["personas_movidas"], 1)
        self.assertEqual(empresas.contar_empresas(self.conn, self.cursor), 1)
        with self.assertRaises(NoEncontradoError):
            empresas.obtener_empresa(self.conn, self.cursor, origen["id"])

        fila = personas.listar_personas(self.conn, self.cursor)[0]
        self.assertEqual(fila["empresa_id"], destino["id"])
        self.assertEqual(fila["empresa"], "Minera B")

    def test_fusionar_la_misma_empresa_no_tiene_sentido(self):
        from backend.errors import DatosInvalidosError

        una = empresas.crear_empresa(
            self.conn, self.cursor, nombre="Minera A", usuario_id=self.usuario_id)

        with self.assertRaises(DatosInvalidosError):
            empresas.fusionar_empresas(
                self.conn, self.cursor, origen_id=una["id"], destino_id=una["id"],
                usuario_id=self.usuario_id)

    def test_eliminar_desvincula_sin_borrar_personas(self):
        creada = empresas.crear_empresa(
            self.conn, self.cursor, nombre="Minera A", usuario_id=self.usuario_id)
        personas.crear_persona(
            self.conn, self.cursor, cedula="1", nombres="Ana", empresa="Minera A",
            usuario_id=self.usuario_id)

        resultado = empresas.eliminar_empresa(
            self.conn, self.cursor, empresa_id=creada["id"], usuario_id=self.usuario_id)

        self.assertEqual(resultado["personas_desvinculadas"], 1)
        self.assertEqual(empresas.contar_empresas(self.conn, self.cursor), 0)
        fila = personas.listar_personas(self.conn, self.cursor)[0]
        self.assertIsNone(fila["empresa_id"])
        self.assertEqual(fila["nombres"], "Ana")

    def test_el_listado_cuenta_personas_y_documentos(self):
        creada = empresas.crear_empresa(
            self.conn, self.cursor, nombre="Minera A", usuario_id=self.usuario_id)
        personas.crear_persona(
            self.conn, self.cursor, cedula="1", nombres="Ana", empresa="Minera A",
            usuario_id=self.usuario_id)
        documentos.crear_documento(
            self.conn, self.cursor,
            usuario_id=self.usuario_id,
            usuario_nombre=self.usuario_nombre,
            nombre="prueba.pdf",
            datos=PDF_MINIMO,
            cedula="1",
            nombres="Ana",
            empresa="Minera A",
        )

        fila = empresas.obtener_empresa(self.conn, self.cursor, creada["id"])

        self.assertEqual(fila["personas"], 1)
        self.assertEqual(fila["documentos"], 1)


class PersonasConCatalogoTest(BaseBackendTest):
    """La puerta por la que entran los nombres que escribe el usuario."""

    def test_dos_grafias_de_la_misma_empresa_comparten_ficha(self):
        personas.crear_persona(
            self.conn, self.cursor, cedula="1", nombres="Ana",
            empresa="Minera del Norte S.A.S.", usuario_id=self.usuario_id)
        personas.crear_persona(
            self.conn, self.cursor, cedula="2", nombres="Luis",
            empresa="minera del norte", usuario_id=self.usuario_id)

        self.assertEqual(empresas.contar_empresas(self.conn, self.cursor), 1)

        filas = personas.listar_personas(self.conn, self.cursor)
        self.assertEqual(len({fila["empresa_id"] for fila in filas}), 1)

    def test_editar_la_empresa_de_una_persona_usa_el_catalogo(self):
        personas.crear_persona(
            self.conn, self.cursor, cedula="1", nombres="Ana", empresa="Minera A",
            usuario_id=self.usuario_id)
        empresas.crear_empresa(
            self.conn, self.cursor, nombre="Minera B", usuario_id=self.usuario_id)

        actualizada = personas.actualizar_persona(
            self.conn, self.cursor, persona_id=1, nombres="Ana",
            empresa="minera b", usuario_id=self.usuario_id)

        self.assertEqual(empresas.contar_empresas(self.conn, self.cursor), 2)
        self.assertEqual(actualizada["empresa"], "minera b")
        # La ficha reutilizada es la que ya existía, no una nueva.
        catalogo = {fila["nombre"] for fila in empresas.listar_empresas(self.conn, self.cursor)}
        self.assertEqual(catalogo, {"Minera A", "Minera B"})

    def test_un_documento_con_titular_nuevo_entra_al_catalogo(self):
        documentos.crear_documento(
            self.conn, self.cursor,
            usuario_id=self.usuario_id,
            usuario_nombre=self.usuario_nombre,
            nombre="prueba.pdf",
            datos=PDF_MINIMO,
            cedula="9",
            nombres="Eva",
            empresa="Minera C",
        )

        self.assertEqual(empresas.contar_empresas(self.conn, self.cursor), 1)
        fila = personas.listar_personas(self.conn, self.cursor)[0]
        self.assertIsNotNone(fila["empresa_id"])


class MigracionTest(BaseBackendTest):
    """El texto libre que ya existía queda vinculado al catálogo."""

    def test_migra_el_texto_libre_y_agrupa_variantes(self):
        # Personas como las dejaba la versión anterior: solo texto, sin vínculo.
        for cedula, nombres, empresa in (
            ("1", "Ana", "Minera del Norte S.A.S."),
            ("2", "Luis", "minera del norte"),
            ("3", "Eva", "  Minera   del  Norte  "),
            ("4", "Sol", None),
        ):
            self.cursor.execute(
                "INSERT INTO Personas (cedula, nombres, empresa) VALUES (?, ?, ?)",
                (cedula, nombres, empresa),
            )
        self.conn.commit()

        _migrar_empresas(self.cursor)
        self.conn.commit()

        # Tres grafías de la misma empresa: una sola ficha.
        self.assertEqual(empresas.contar_empresas(self.conn, self.cursor), 1)

        filas = {fila["cedula"]: fila for fila in personas.listar_personas(self.conn, self.cursor)}
        self.assertIsNotNone(filas["1"]["empresa_id"])
        self.assertEqual(filas["1"]["empresa_id"], filas["2"]["empresa_id"])
        self.assertEqual(filas["2"]["empresa_id"], filas["3"]["empresa_id"])
        # Quien no tenía empresa sigue sin ella.
        self.assertIsNone(filas["4"]["empresa_id"])

    def test_la_migracion_es_idempotente(self):
        self.cursor.execute(
            "INSERT INTO Personas (cedula, nombres, empresa) VALUES (?, ?, ?)",
            ("1", "Ana", "Minera del Norte"),
        )
        self.conn.commit()

        for _ in range(3):
            _migrar_empresas(self.cursor)
            self.conn.commit()

        self.assertEqual(empresas.contar_empresas(self.conn, self.cursor), 1)

    def test_no_toca_lo_que_ya_esta_vinculado(self):
        empresas.crear_empresa(
            self.conn, self.cursor, nombre="Minera A", usuario_id=self.usuario_id)
        personas.crear_persona(
            self.conn, self.cursor, cedula="1", nombres="Ana", empresa="Minera A",
            usuario_id=self.usuario_id)

        _migrar_empresas(self.cursor)
        self.conn.commit()

        self.assertEqual(empresas.contar_empresas(self.conn, self.cursor), 1)


class AislamientoTest(BaseBackendTest):
    def test_el_servicio_no_carga_tkinter(self):
        assert_sin_tkinter(self)


if __name__ == "__main__":
    unittest.main()