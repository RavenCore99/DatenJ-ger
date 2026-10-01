# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/services/empresas.py - catálogo de empresas (calidad de vida)

"""Servicio de empresas: el catálogo al que se asocian las personas.

Antes, la empresa de un titular era **texto libre** en `Personas.empresa`, así
que «Minera del Norte S.A.S.», «minera del norte» y «Minera  del Norte» eran tres
empresas distintas para la base: imposible contar el personal por empresa y
fácil sembrar duplicados. Ahora hay un catálogo propio y `Personas.empresa_id`
apunta a él.

**Cómo se evita el duplicado.** Cada empresa guarda dos cosas: `nombre` —lo que
escribió el usuario, tal cual— y `nombre_normalizado`, la clave de comparación
que produce `database.normalizar_empresa` (sin acentos, sin puntuación, sin la
forma societaria final). La clave es `UNIQUE`: si alguien vuelve a escribir la
misma empresa con otra grafía, se resuelve a la ficha que ya existe.

La columna de texto `Personas.empresa` se conserva y se mantiene en sincronía:
es lo que el usuario escribió y sirve de respaldo, y el inventario de documentos
la sigue mostrando sin tener que recorrer el catálogo.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from backend.errors import ConflictoError, DatosInvalidosError, NoEncontradoError
from backend.services import auditoria
from database import normalizar_empresa

ACCION_AGREGAR = "Agregar empresa"
ACCION_EDITAR = "Renombrar empresa"
ACCION_FUSIONAR = "Fusionar empresas"
ACCION_ELIMINAR = "Eliminar empresa"


class EmpresaError(DatosInvalidosError):
    """Error propio del servicio de empresas."""


def _fila_a_dict(fila: Sequence[Any]) -> dict:
    return {
        "id": fila[0],
        "nombre": fila[1],
        "personas": fila[2],
        "documentos": fila[3],
    }


def _registrar_auditoria(cursor, conn, accion: str, usuario_id: Optional[int]) -> None:
    """Registra el evento en el servicio de auditoría (best-effort)."""
    auditoria.registrar_evento(conn, cursor, accion, usuario_id)


def _nombre_limpio(nombre: Optional[str]) -> str:
    return " ".join(str(nombre or "").split()).strip()


# --------------------------------------------------------------------------- #
# Consultas
# --------------------------------------------------------------------------- #

_CONSULTA_BASE = (
    "SELECT e.id, e.nombre, "
    "       (SELECT COUNT(*) FROM Personas pe WHERE pe.empresa_id = e.id), "
    "       (SELECT COUNT(*) FROM PDFs p "
    "        JOIN Personas pe2 ON p.persona_id = pe2.id "
    "        WHERE pe2.empresa_id = e.id) "
    "FROM Empresas e "
)


def listar_empresas(conn, cursor, filtro: str = "") -> list[dict]:
    """Lista el catálogo con cuántas personas y documentos tiene cada empresa.

    Args:
        filtro: texto a buscar en el nombre.

    Returns:
        Lista de dicts (``id``, ``nombre``, ``personas``, ``documentos``)
        ordenada por nombre.
    """
    consulta = _CONSULTA_BASE + "WHERE 1=1 "
    params: list[Any] = []

    filtro = (filtro or "").strip()
    if filtro:
        consulta += "AND e.nombre LIKE ? "
        params.append(f"%{filtro}%")

    consulta += "ORDER BY e.nombre ASC"
    cursor.execute(consulta, params)
    return [_fila_a_dict(fila) for fila in cursor.fetchall()]


def obtener_empresa(conn, cursor, empresa_id: int) -> dict:
    """Devuelve una empresa por id.

    Raises:
        NoEncontradoError: la empresa no existe.
    """
    cursor.execute(_CONSULTA_BASE + "WHERE e.id = ?", (empresa_id,))
    fila = cursor.fetchone()
    if not fila:
        raise NoEncontradoError("Empresa no encontrada")
    return _fila_a_dict(fila)


def contar_empresas(conn, cursor) -> int:
    """Cuenta las empresas del catálogo."""
    cursor.execute("SELECT COUNT(*) FROM Empresas")
    fila = cursor.fetchone()
    return int(fila[0]) if fila else 0


def resolver_empresa(conn, cursor, nombre: Optional[str]) -> Optional[int]:
    """Id de la empresa con ese nombre, creándola si todavía no existe.

    Es la puerta por la que entran los nombres que escribe el usuario al
    registrar una persona o un documento. Si la forma normalizada ya está en el
    catálogo devuelve **esa** ficha en vez de crear otra: es lo que evita las
    redundancias sin obligar a nadie a elegir de una lista.

    No hace `commit`: se resuelve dentro de la transacción de quien llama, para
    que la empresa y la persona se guarden juntas o no se guarde ninguna.

    Returns:
        El id de la empresa, o `None` si el nombre no aporta nada.
    """
    clave = normalizar_empresa(nombre)
    if not clave:
        return None

    cursor.execute("SELECT id FROM Empresas WHERE nombre_normalizado = ?", (clave,))
    fila = cursor.fetchone()
    if fila:
        return fila[0]

    cursor.execute(
        "INSERT INTO Empresas (nombre, nombre_normalizado) VALUES (?, ?)",
        (_nombre_limpio(nombre), clave),
    )
    return cursor.lastrowid


# --------------------------------------------------------------------------- #
# Escritura
# --------------------------------------------------------------------------- #


def crear_empresa(
    conn,
    cursor,
    *,
    nombre: str,
    usuario_id: Optional[int] = None,
) -> dict:
    """Da de alta una empresa en el catálogo.

    Raises:
        EmpresaError: el nombre está vacío.
        ConflictoError: ya existe una empresa con esa forma normalizada.
    """
    limpio = _nombre_limpio(nombre)
    if not limpio:
        raise EmpresaError("El nombre de la empresa es obligatorio")

    clave = normalizar_empresa(limpio)
    cursor.execute("SELECT id, nombre FROM Empresas WHERE nombre_normalizado = ?", (clave,))
    existente = cursor.fetchone()
    if existente:
        raise ConflictoError(
            f"Ya existe una empresa con ese nombre: {existente[1]}")

    cursor.execute(
        "INSERT INTO Empresas (nombre, nombre_normalizado) VALUES (?, ?)",
        (limpio, clave),
    )
    empresa_id = cursor.lastrowid
    conn.commit()

    _registrar_auditoria(cursor, conn, ACCION_AGREGAR, usuario_id)
    return obtener_empresa(conn, cursor, empresa_id)


def renombrar_empresa(
    conn,
    cursor,
    *,
    empresa_id: int,
    nombre: str,
    usuario_id: Optional[int] = None,
) -> dict:
    """Cambia el nombre visible de una empresa.

    Como las personas apuntan al catálogo y no al texto, el cambio alcanza a
    todo el personal de la empresa de una sola vez.

    Raises:
        EmpresaError: el nombre está vacío.
        NoEncontradoError: la empresa no existe.
        ConflictoError: el nombre nuevo choca con otra empresa del catálogo.
    """
    actual = obtener_empresa(conn, cursor, empresa_id)

    limpio = _nombre_limpio(nombre)
    if not limpio:
        raise EmpresaError("El nombre de la empresa es obligatorio")

    clave = normalizar_empresa(limpio)
    cursor.execute(
        "SELECT id FROM Empresas WHERE nombre_normalizado = ? AND id != ?",
        (clave, empresa_id),
    )
    if cursor.fetchone():
        raise ConflictoError("Ya hay otra empresa con ese nombre en el catálogo")

    try:
        cursor.execute(
            "UPDATE Empresas SET nombre = ?, nombre_normalizado = ? WHERE id = ?",
            (limpio, clave, empresa_id),
        )
        # El texto de la persona se mantiene en sincronía con el catálogo.
        cursor.execute(
            "UPDATE Personas SET empresa = ? WHERE empresa_id = ?", (limpio, empresa_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    _registrar_auditoria(cursor, conn, ACCION_EDITAR, usuario_id)
    return {"anterior": actual["nombre"], **obtener_empresa(conn, cursor, empresa_id)}


def fusionar_empresas(
    conn,
    cursor,
    *,
    origen_id: int,
    destino_id: int,
    usuario_id: Optional[int] = None,
) -> dict:
    """Une dos fichas del catálogo: el personal del origen pasa al destino.

    Sirve para arreglar lo que la normalización no puede adivinar (una empresa
    escrita con otro nombre comercial) sin tocar a mano la base.

    Raises:
        NoEncontradoError: alguna de las dos empresas no existe.
        EmpresaError: origen y destino son la misma.
    """
    if origen_id == destino_id:
        raise EmpresaError("El origen y el destino de la fusión son la misma empresa")

    origen = obtener_empresa(conn, cursor, origen_id)
    destino = obtener_empresa(conn, cursor, destino_id)

    try:
        cursor.execute(
            "UPDATE Personas SET empresa_id = ?, empresa = ? WHERE empresa_id = ?",
            (destino_id, destino["nombre"], origen_id),
        )
        cursor.execute("DELETE FROM Empresas WHERE id = ?", (origen_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    _registrar_auditoria(cursor, conn, ACCION_FUSIONAR, usuario_id)
    return {
        "origen": origen["nombre"],
        "destino": destino["nombre"],
        "personas_movidas": origen["personas"],
        "empresa": obtener_empresa(conn, cursor, destino_id),
    }


def eliminar_empresa(
    conn,
    cursor,
    *,
    empresa_id: int,
    usuario_id: Optional[int] = None,
) -> dict:
    """Elimina una empresa del catálogo; su personal queda sin empresa.

    No borra personas ni documentos: solo se desvinculan, igual que al eliminar
    un titular sus documentos quedan sin titular.

    Raises:
        NoEncontradoError: la empresa no existe.
    """
    empresa = obtener_empresa(conn, cursor, empresa_id)

    try:
        cursor.execute(
            "UPDATE Personas SET empresa_id = NULL, empresa = NULL WHERE empresa_id = ?",
            (empresa_id,),
        )
        cursor.execute("DELETE FROM Empresas WHERE id = ?", (empresa_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    _registrar_auditoria(cursor, conn, ACCION_ELIMINAR, usuario_id)
    return {
        "id": empresa["id"],
        "nombre": empresa["nombre"],
        "personas_desvinculadas": empresa["personas"],
    }