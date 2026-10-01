# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/services/personas.py - CRUD de personas (titulares)

"""Servicio de personas: CRUD de titulares de documentos.

Extraído del cuerpo de ``personas.py`` (que conserva solo la interfaz).
Todas las funciones son invocables sin Tkinter.

Nota de alcance: el catálogo de personas es compartido entre usuarios del
sistema (el panel original no filtraba por usuario), así que el servicio
tampoco lo hace. ``usuario_id`` se recibe únicamente para registrar el
evento de auditoría de las operaciones de escritura.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from backend.errors import (
    ConflictoError,
    DatosInvalidosError,
    NoEncontradoError,
)
from backend.services import auditoria
from backend.services import empresas

ACCION_AGREGAR = "Agregar persona (Panel Personas)"
ACCION_EDITAR = "Editar persona (Panel Personas)"
ACCION_ELIMINAR = "Eliminar persona (Panel Personas)"

#: Valor que usa la interfaz para "sin empresa".
SIN_EMPRESA = "—"


class PersonaError(DatosInvalidosError):
    """Error propio del servicio de personas."""


def _fila_a_dict(fila: Sequence[Any]) -> dict:
    return {
        "id": fila[0],
        "cedula": fila[1],
        "nombres": fila[2],
        "empresa": fila[3],
        "documentos": fila[4],
        "empresa_id": fila[5],
    }


def _registrar_auditoria(cursor, conn, accion: str, usuario_id: Optional[int]) -> None:
    """Registra el evento en el servicio de auditoría (best-effort)."""
    auditoria.registrar_evento(conn, cursor, accion, usuario_id)


# --------------------------------------------------------------------------- #
# Consultas
# --------------------------------------------------------------------------- #

def listar_personas(conn, cursor, filtro: str = "") -> list[dict]:
    """Lista personas con su número de documentos vinculados.

    Args:
        filtro: texto a buscar en cédula, nombres o empresa.

    Returns:
        Lista de dicts (``id``, ``cedula``, ``nombres``, ``empresa``,
        ``documentos``) ordenada por nombre.
    """
    consulta = (
        "SELECT pe.id, pe.cedula, pe.nombres, "
        "       COALESCE(pe.empresa, ?), "
        "       COUNT(p.id) AS total_docs, "
        "       pe.empresa_id "
        "FROM Personas pe "
        "LEFT JOIN PDFs p ON p.persona_id = pe.id "
        "WHERE 1=1 "
    )
    params: list[Any] = [SIN_EMPRESA]

    filtro = (filtro or "").strip()
    if filtro:
        consulta += (
            "AND (pe.cedula LIKE ? OR pe.nombres LIKE ? "
            "     OR pe.empresa LIKE ?) "
        )
        like = f"%{filtro}%"
        params.extend([like, like, like])

    consulta += "GROUP BY pe.id ORDER BY pe.nombres ASC"

    cursor.execute(consulta, params)
    return [_fila_a_dict(fila) for fila in cursor.fetchall()]


def obtener_persona(conn, cursor, persona_id: int) -> dict:
    """Devuelve una persona por id.

    Raises:
        NoEncontradoError: la persona no existe.
    """
    cursor.execute(
        "SELECT pe.id, pe.cedula, pe.nombres, COALESCE(pe.empresa, ?), "
        "       COUNT(p.id), pe.empresa_id "
        "FROM Personas pe "
        "LEFT JOIN PDFs p ON p.persona_id = pe.id "
        "WHERE pe.id = ? "
        "GROUP BY pe.id",
        (SIN_EMPRESA, persona_id),
    )
    fila = cursor.fetchone()
    if not fila:
        raise NoEncontradoError("Persona no encontrada")
    return _fila_a_dict(fila)


def contar_personas(conn, cursor) -> int:
    """Cuenta las personas registradas."""
    cursor.execute("SELECT COUNT(*) FROM Personas")
    fila = cursor.fetchone()
    return int(fila[0]) if fila else 0


# --------------------------------------------------------------------------- #
# Escritura
# --------------------------------------------------------------------------- #

def crear_persona(
    conn,
    cursor,
    *,
    cedula: str,
    nombres: str,
    empresa: Optional[str] = None,
    usuario_id: Optional[int] = None,
) -> dict:
    """Registra una persona nueva.

    Raises:
        PersonaError: cédula o nombres vacíos.
        ConflictoError: ya existe una persona con esa cédula.
    """
    cedula = (cedula or "").strip()
    nombres = (nombres or "").strip()
    empresa = (empresa or "").strip() or None

    if not cedula or not nombres:
        raise PersonaError("Cédula y nombres son obligatorios")

    try:
        cursor.execute("SELECT id FROM Personas WHERE cedula = ?", (cedula,))
        if cursor.fetchone():
            raise ConflictoError(f"Ya existe una persona con cédula {cedula}")

        # La empresa entra por el catálogo: si ya existe con otra grafía, se
        # resuelve a esa ficha en vez de crear una nueva.
        empresa_id = empresas.resolver_empresa(conn, cursor, empresa)

        cursor.execute(
            "INSERT INTO Personas (cedula, nombres, empresa, empresa_id) VALUES (?, ?, ?, ?)",
            (cedula, nombres, empresa, empresa_id),
        )
        persona_id = cursor.lastrowid
        conn.commit()
    except ConflictoError:
        raise
    except Exception:
        conn.rollback()
        raise

    _registrar_auditoria(cursor, conn, ACCION_AGREGAR, usuario_id)
    return {
        "id": persona_id,
        "cedula": cedula,
        "nombres": nombres,
        "empresa": empresa,
        "empresa_id": empresa_id,
    }


def actualizar_persona(
    conn,
    cursor,
    *,
    persona_id: int,
    nombres: str,
    empresa: Optional[str] = None,
    usuario_id: Optional[int] = None,
) -> dict:
    """Actualiza nombre y empresa de una persona.

    La cédula no se modifica: identifica al titular y está referenciada por
    los documentos vinculados.

    Raises:
        PersonaError: nombres vacíos.
        NoEncontradoError: la persona no existe.
    """
    nombres = (nombres or "").strip()
    empresa = (empresa or "").strip() or None

    if not nombres:
        raise PersonaError("Los nombres son obligatorios")

    obtener_persona(conn, cursor, persona_id)

    try:
        empresa_id = empresas.resolver_empresa(conn, cursor, empresa)
        cursor.execute(
            "UPDATE Personas SET nombres = ?, empresa = ?, empresa_id = ? WHERE id = ?",
            (nombres, empresa, empresa_id, persona_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    _registrar_auditoria(cursor, conn, ACCION_EDITAR, usuario_id)
    return obtener_persona(conn, cursor, persona_id)


def eliminar_persona(
    conn,
    cursor,
    *,
    persona_id: int,
    usuario_id: Optional[int] = None,
) -> dict:
    """Elimina una persona; sus documentos quedan sin titular.

    Returns:
        Dict con ``id``, ``nombres`` y ``documentos`` (cuántos quedaron
        huérfanos).

    Raises:
        NoEncontradoError: la persona no existe.
    """
    persona = obtener_persona(conn, cursor, persona_id)

    try:
        # Los documentos vinculados quedan sin titular. El esquema declara
        # ON DELETE SET NULL, pero la conexión no activa las claves foráneas
        # (PRAGMA foreign_keys), así que el desvinculo se hace explícito para
        # que el documento no quede apuntando a un id reutilizable.
        cursor.execute("UPDATE PDFs SET persona_id = NULL WHERE persona_id = ?", (persona_id,))
        cursor.execute("DELETE FROM Personas WHERE id = ?", (persona_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    _registrar_auditoria(cursor, conn, ACCION_ELIMINAR, usuario_id)
    return {
        "id": persona["id"],
        "nombres": persona["nombres"],
        "documentos": persona["documentos"],
    }