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

from datetime import datetime
from typing import Any, Optional, Sequence

from backend.errors import (
    ConflictoError,
    DatosInvalidosError,
    NoEncontradoError,
)

ACCION_AGREGAR = "Agregar persona (Panel Personas)"
ACCION_EDITAR = "Editar persona (Panel Personas)"
ACCION_ELIMINAR = "Eliminar persona (Panel Personas)"

#: Valor que usa la interfaz para "sin empresa".
SIN_EMPRESA = "—"


class PersonaError(DatosInvalidosError):
    """Error propio del servicio de personas."""


def _ahora() -> str:
    return datetime.now().isoformat()


def _fila_a_dict(fila: Sequence[Any]) -> dict:
    return {
        "id": fila[0],
        "cedula": fila[1],
        "nombres": fila[2],
        "empresa": fila[3],
        "documentos": fila[4],
    }


def _registrar_auditoria(cursor, conn, accion: str, usuario_id: Optional[int]) -> None:
    """Inserta un evento de auditoría sin cortar el flujo principal.

    Se consolida en el servicio de auditoría al cerrar SCRUM-14.
    """
    try:
        cursor.execute(
            "INSERT INTO Auditoria (accion, pdf_id, usuario_id, fecha) VALUES (?, ?, ?, ?)",
            (accion, None, usuario_id, _ahora()),
        )
        conn.commit()
    except Exception:
        pass


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
        "       COUNT(p.id) AS total_docs "
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
        "       COUNT(p.id) "
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


def contar_personas(cursor) -> int:
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

        cursor.execute(
            "INSERT INTO Personas (cedula, nombres, empresa) VALUES (?, ?, ?)",
            (cedula, nombres, empresa),
        )
        persona_id = cursor.lastrowid
        conn.commit()
    except ConflictoError:
        raise
    except Exception:
        conn.rollback()
        raise

    _registrar_auditoria(cursor, conn, ACCION_AGREGAR, usuario_id)
    return {"id": persona_id, "cedula": cedula, "nombres": nombres, "empresa": empresa}


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
        cursor.execute(
            "UPDATE Personas SET nombres = ?, empresa = ? WHERE id = ?",
            (nombres, empresa, persona_id),
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