# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/services/auditoria.py - registro y consulta de auditoría

"""Servicio de auditoría: registro de eventos, consulta del historial y
composición del log del sistema.

Extraído de ``audit.py``, que conserva únicamente el visor (ventana,
tabla y filtros). Todas las funciones de este módulo son invocables sin
Tkinter.

Cumplimiento: el registro de cada acción es obligatorio para la
trazabilidad (Ley 1581). ``registrar_evento`` nunca levanta excepción: un
fallo de auditoría no debe romper la operación de negocio que lo origina,
pero sí reporta ``False`` para que el llamador pueda decidir.
"""

from __future__ import annotations

import glob
import os
import platform
import sqlite3
import sys
from datetime import datetime
from typing import Any, Optional

#: Texto base del evento que deja constancia al vaciar el historial.
ACCION_LIMPIEZA = "Historial de auditoría limpiado"

#: Límite de filas del visor (igual que el panel original).
LIMITE_VISOR = 2000

#: Límite de eventos volcados al log en memoria.
LIMITE_LOG = 500


def _ahora() -> str:
    return datetime.now().isoformat()


# --------------------------------------------------------------------------- #
# Registro
# --------------------------------------------------------------------------- #

def registrar_evento(
    conn,
    cursor,
    accion: str,
    usuario_id: Optional[int] = None,
    documento_id: Optional[int] = None,
) -> bool:
    """Registra una acción en la tabla Auditoria.

    Returns:
        ``True`` si el evento quedó guardado, ``False`` si falló (el error
        no se propaga: la auditoría es best-effort).
    """
    if not accion:
        return False
    try:
        cursor.execute(
            "INSERT INTO Auditoria (accion, pdf_id, usuario_id, fecha) VALUES (?, ?, ?, ?)",
            (accion, documento_id, usuario_id, _ahora()),
        )
        conn.commit()
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Consulta
# --------------------------------------------------------------------------- #

def listar_eventos(
    cursor,
    desde: str = "",
    hasta: str = "",
    accion: str = "",
    limite: int = LIMITE_VISOR,
) -> list[dict]:
    """Consulta el historial de auditoría con filtros opcionales.

    Args:
        cursor: cursor de la conexión activa (consulta de solo lectura).
        desde: fecha ISO mínima (se compara contra el texto almacenado).
        hasta: fecha ISO máxima; se extiende al final del día.
        accion: texto a buscar dentro de la acción.
        limite: máximo de filas devueltas.

    Returns:
        Lista de dicts con ``fecha`` (ISO crudo), ``accion``,
        ``documento_id`` y ``usuario`` (nombre o ``None``), más reciente
        primero.
    """
    consulta = (
        "SELECT a.fecha, a.accion, a.pdf_id, u.nombre "
        "FROM Auditoria a "
        "LEFT JOIN Usuarios u ON a.usuario_id = u.id "
        "WHERE 1=1 "
    )
    params: list[Any] = []

    desde = (desde or "").strip()
    hasta = (hasta or "").strip()
    accion = (accion or "").strip()

    if desde:
        consulta += "AND a.fecha >= ? "
        params.append(desde)
    if hasta:
        consulta += "AND a.fecha <= ? "
        params.append(hasta + "T23:59:59")
    if accion:
        consulta += "AND a.accion LIKE ? "
        params.append(f"%{accion}%")

    consulta += "ORDER BY a.fecha DESC LIMIT ?"
    params.append(int(limite))

    cursor.execute(consulta, params)
    return [
        {
            "fecha": fila[0],
            "accion": fila[1],
            "documento_id": fila[2],
            "usuario": fila[3],
        }
        for fila in cursor.fetchall()
    ]


def contar_eventos(cursor) -> int:
    """Cuenta los eventos de auditoría registrados."""
    cursor.execute("SELECT COUNT(*) FROM Auditoria")
    fila = cursor.fetchone()
    return int(fila[0]) if fila else 0


# --------------------------------------------------------------------------- #
# Mantenimiento
# --------------------------------------------------------------------------- #

def limpiar_historial(conn, cursor, usuario_id: Optional[int] = None) -> int:
    """Borra todo el historial dejando constancia del vaciado.

    Returns:
        Número de registros eliminados (0 si ya estaba vacío).

    Raises:
        sqlite3.Error / Exception: si el borrado falla (el llamador decide
        cómo avisar).
    """
    total = contar_eventos(cursor)
    if total == 0:
        return 0

    try:
        cursor.execute("DELETE FROM Auditoria")
        cursor.execute(
            "INSERT INTO Auditoria (accion, pdf_id, usuario_id, fecha) "
            "VALUES (?, NULL, ?, ?)",
            (f"{ACCION_LIMPIEZA} ({total} registros eliminados)", usuario_id, _ahora()),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    try:
        cursor.execute("VACUUM")
    except Exception:
        # el compactado es opcional: no invalida el borrado ya confirmado
        pass

    return total


# --------------------------------------------------------------------------- #
# Log del sistema
# --------------------------------------------------------------------------- #

def construir_log_sistema(cursor, directorio: str, limite: int = LIMITE_LOG) -> tuple[str, str]:
    """Compone el contenido del visor de log.

    Busca el primer archivo ``*.log`` del directorio; si no existe, genera
    un volcado en memoria con la información del sistema y los últimos
    eventos de auditoría — el mismo comportamiento del visor original.

    Args:
        directorio: ruta donde buscar los archivos de log.

    Returns:
        ``(contenido, origen)`` donde ``origen`` es la ruta del archivo
        encontrado o ``"(generado en memoria)"``.
    """
    rutas = [
        os.path.join(directorio, "datenjager.log"),
        os.path.join(directorio, "app.log"),
    ]
    rutas += glob.glob(os.path.join(directorio, "*.log"))

    for ruta in rutas:
        if os.path.isfile(ruta):
            try:
                with open(ruta, "r", encoding="utf-8", errors="replace") as archivo:
                    return archivo.read(), ruta
            except Exception:
                continue

    contenido = (
        "═══ DatenJäger — Información del Sistema ═══\n\n"
        f"Python:     {sys.version}\n"
        f"Plataforma: {platform.platform()}\n"
        f"SQLite:     {sqlite3.sqlite_version}\n\n"
        "═══ Log de Auditoría exportado ═══\n\n"
    )
    try:
        for evento in reversed(listar_eventos(cursor, limite=limite)):
            fecha = evento["fecha"][:19].replace("T", " ") if evento["fecha"] else "—"
            documento = evento["documento_id"] if evento["documento_id"] is not None else "—"
            usuario = evento["usuario"] or "—"
            contenido += f"[{fecha}] {evento['accion']} | PDF={documento} | User={usuario}\n"
    except Exception as exc:
        contenido += f"Error leyendo BD: {exc}\n"

    return contenido, "(generado en memoria)"