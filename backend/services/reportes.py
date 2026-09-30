# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/services/reportes.py - métricas y exportación de reportes

"""Servicio de reportes y métricas.

Reúne las consultas que estaban repartidas entre ``main.py`` (datos del
reporte del dashboard) y ``ui_components.DashboardWidget`` (tarjetas KPI,
documentos por empresa y tendencia temporal), más la exportación a PDF/CSV.
Sin dependencias de Tkinter.

Nota sobre ``total_empresas``: el reporte de ``main.py`` lo cuenta como el
número de filas del agrupamiento por ``COALESCE(empresa,'Sin empresa')``,
mientras el dashboard lo cuenta como ``COUNT(DISTINCT COALESCE(empresa,''))``
—son definiciones distintas y se conservan tal cual para no alterar las
cifras que ya mostraba cada pantalla.
"""

from __future__ import annotations

from typing import Optional

from database import format_size
from reporter import ReporteInventario
from backend.errors import DatosInvalidosError
from backend.services import auditoria

#: Formatos de exportación admitidos.
FORMATOS = ("pdf", "csv")

ACCION_REPORTE = "Generar reporte dashboard {formato}"


class ReporteError(DatosInvalidosError):
    """Error propio del servicio de reportes."""


# --------------------------------------------------------------------------- #
# Métricas del dashboard
# --------------------------------------------------------------------------- #

def estadisticas(conn, cursor, usuario_id: Optional[int]) -> dict:
    """Tarjetas KPI del dashboard.

    Returns:
        Dict con ``total_pdfs``, ``total_size_str``, ``total_personas`` y
        ``total_empresas``.
    """
    cursor.execute(
        "SELECT COUNT(*), COALESCE(SUM(tamano),0) FROM PDFs WHERE usuario_id = ?",
        (usuario_id,),
    )
    total_pdfs, total_size = cursor.fetchone()
    total_pdfs = total_pdfs or 0
    total_size = total_size or 0

    cursor.execute(
        "SELECT COUNT(DISTINCT persona_id) FROM PDFs WHERE usuario_id = ?",
        (usuario_id,),
    )
    total_personas = cursor.fetchone()[0] or 0

    cursor.execute(
        "SELECT COUNT(DISTINCT COALESCE(pe.empresa,'')) "
        "FROM PDFs p LEFT JOIN Personas pe ON p.persona_id = pe.id "
        "WHERE p.usuario_id = ?",
        (usuario_id,),
    )
    total_empresas = cursor.fetchone()[0] or 0

    return {
        "total_pdfs": total_pdfs,
        "total_size_str": format_size(total_size),
        "total_personas": total_personas,
        "total_empresas": total_empresas,
    }


def documentos_por_empresa(conn, cursor, usuario_id: Optional[int]) -> list[tuple]:
    """Distribución de documentos por empresa (gráfico donut)."""
    cursor.execute(
        "SELECT COALESCE(pe.empresa, 'Sin empresa'), COUNT(*) "
        "FROM PDFs p LEFT JOIN Personas pe ON p.persona_id = pe.id "
        "WHERE p.usuario_id = ? "
        "GROUP BY COALESCE(pe.empresa, 'Sin empresa') "
        "ORDER BY COUNT(*) DESC",
        (usuario_id,),
    )
    return cursor.fetchall()


def documentos_por_dia(conn, cursor, usuario_id: Optional[int]) -> list[tuple]:
    """Documentos subidos por día (línea de tendencia)."""
    cursor.execute(
        "SELECT DATE(fecha_subida) AS dia, COUNT(*) "
        "FROM PDFs WHERE usuario_id = ? "
        "GROUP BY DATE(fecha_subida) ORDER BY dia ASC",
        (usuario_id,),
    )
    return cursor.fetchall()


# --------------------------------------------------------------------------- #
# Reporte de inventario
# --------------------------------------------------------------------------- #

def datos_inventario(conn, cursor, usuario_id: Optional[int]) -> tuple[list, dict]:
    """Filas y estadísticas del reporte de inventario.

    Returns:
        ``(rows, stats)`` donde ``rows`` es el inventario de documentos con
        su titular y ``stats`` el resumen que consume el generador PDF.
    """
    cursor.execute(
        """
        SELECT p.id, p.nombre, p.descripcion, p.tamano,
               p.fecha_subida, pe.cedula, pe.nombres, pe.empresa
        FROM PDFs p
        LEFT JOIN Personas pe ON p.persona_id = pe.id
        WHERE p.usuario_id = ?
        ORDER BY p.fecha_subida DESC
        """,
        (usuario_id,),
    )
    rows = cursor.fetchall()

    cursor.execute(
        "SELECT COUNT(*), COALESCE(SUM(tamano), 0) FROM PDFs WHERE usuario_id = ?",
        (usuario_id,),
    )
    total_pdfs, total_size = cursor.fetchone()
    total_pdfs = total_pdfs or 0
    total_size = total_size or 0

    cursor.execute(
        "SELECT COUNT(DISTINCT persona_id) FROM PDFs WHERE usuario_id = ?",
        (usuario_id,),
    )
    total_personas = cursor.fetchone()[0] or 0

    cursor.execute(
        """
        SELECT COALESCE(pe.empresa, 'Sin empresa') AS empresa, COUNT(*) AS total
        FROM PDFs p
        LEFT JOIN Personas pe ON p.persona_id = pe.id
        WHERE p.usuario_id = ?
        GROUP BY COALESCE(pe.empresa, 'Sin empresa')
        ORDER BY total DESC, empresa ASC
        """,
        (usuario_id,),
    )
    empresas_data = cursor.fetchall()

    stats = {
        "total_pdfs": total_pdfs,
        "total_size_str": format_size(total_size),
        "total_personas": total_personas,
        "total_empresas": len(empresas_data),
        "empresas_data": empresas_data,
    }
    return rows, stats


def exportar_inventario(
    conn,
    cursor,
    *,
    usuario_id: Optional[int],
    usuario_nombre: str,
    destino: str,
    formato: str = "pdf",
) -> str:
    """Genera el reporte de inventario en ``destino`` y lo audita.

    Args:
        formato: ``"pdf"`` o ``"csv"``; cualquier otro valor cae a ``"pdf"``.
        destino: ruta del archivo a escribir.

    Returns:
        La ruta escrita.

    Raises:
        ReporteError: no hay destino.
    """
    if not destino:
        raise ReporteError("No se indicó un destino para el reporte")

    formato = (formato or "pdf").lower().strip()
    if formato not in FORMATOS:
        formato = "pdf"

    rows, stats = datos_inventario(conn, cursor, usuario_id)

    if formato == "csv":
        ReporteInventario.generar_csv(rows, destino, usuario_nombre or "")
    else:
        ReporteInventario.generar_pdf(rows, stats, destino, usuario_nombre or "")

    auditoria.registrar_evento(
        conn, cursor, ACCION_REPORTE.format(formato=formato.upper()), usuario_id
    )
    return destino