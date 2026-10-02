# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/services/contexto.py - contexto del proyecto para el asistente
# Trazabilidad Jira: SCRUM-61 (DatenJäger — Chatbot).

"""Contexto del proyecto que se le entrega al asistente (``SCRUM-61``).

El asistente debe responder **solo** sobre DatenJäger y con las cifras reales
del sistema, no con lo que el modelo recuerde o imagine. Este módulo arma ese
contexto a partir de las consultas que ya existen.

**Qué entra y qué no.** Solo **agregados**: cuántos documentos hay, cuánto
ocupan, cómo se reparten por empresa, cuántos titulares y empresas hay, y qué
acciones registra la auditoría. No entra ni un dato personal —cédulas, nombres
de titulares, nombres de archivo, contenido de los documentos— ni un secreto
—claves, hashes, tokens, rutas del disco—. Esa es la protección de verdad: el
modelo no puede filtrar lo que nunca recibe, y el prompt lo dice además por
escrito para que no invente lo que no tiene.

El contexto se recalcula en cada turno: si el archivo cambia mientras se
conversa, las cifras que da el asistente son las de ahora.
"""

from __future__ import annotations

from typing import Any, Optional

from backend.services import auditoria, empresas, reportes

#: Cuántas empresas y acciones se listan antes de resumir el resto.
LIMITE_EMPRESAS = 8
LIMITE_ACCIONES = 8
LIMITE_DIAS = 7


def _documentos_por_empresa(conn, cursor, usuario_id: Optional[int]) -> list[dict[str, Any]]:
    """Distribución por empresa, ya recortada a las más cargadas."""
    filas = reportes.documentos_por_empresa(conn, cursor, usuario_id)
    return [{"empresa": nombre, "documentos": total} for nombre, total in filas[:LIMITE_EMPRESAS]]


def _serie_reciente(conn, cursor, usuario_id: Optional[int]) -> list[dict[str, Any]]:
    """Altas por día de los últimos días con actividad."""
    filas = reportes.documentos_por_dia(conn, cursor, usuario_id)
    return [{"dia": dia, "documentos": total} for dia, total in filas[-LIMITE_DIAS:]]


def _auditoria_por_accion(conn, cursor) -> list[dict[str, Any]]:
    """Acciones más frecuentes del historial de auditoría (sin usuarios)."""
    cursor.execute(
        "SELECT accion, COUNT(*) FROM Auditoria GROUP BY accion "
        "ORDER BY COUNT(*) DESC LIMIT ?",
        (LIMITE_ACCIONES,),
    )
    return [{"accion": accion, "veces": total} for accion, total in cursor.fetchall()]


def resumen_del_proyecto(conn, cursor, usuario_id: Optional[int]) -> dict[str, Any]:
    """Agregados reales del sistema, listos para el asistente.

    Returns:
        Dict con ``documentos``, ``titulares``, ``empresas`` y ``auditoria``.
        Todo son cifras y nombres de empresa: ningún dato personal ni secreto.
    """
    metricas = reportes.estadisticas(conn, cursor, usuario_id)

    return {
        "documentos": {
            "total": metricas["total_pdfs"],
            "tamano": metricas["total_size_str"],
            "por_empresa": _documentos_por_empresa(conn, cursor, usuario_id),
            "ultimos_dias": _serie_reciente(conn, cursor, usuario_id),
        },
        "titulares": metricas["total_personas"],
        "empresas": metricas["total_empresas"],
        "catalogo_empresas": [
            {
                "nombre": fila["nombre"],
                "personas": fila.get("personas", 0),
                "documentos": fila.get("documentos", 0),
            }
            for fila in empresas.listar_empresas(conn, cursor)[:LIMITE_EMPRESAS]
        ],
        "auditoria": {
            "total": auditoria.contar_eventos(conn, cursor),
            "por_accion": _auditoria_por_accion(conn, cursor),
        },
    }


#: Lo que el sistema sabe hacer, para que el asistente no invente funciones.
CAPACIDADES = (
    "Registrar operadores con doble factor (TOTP) y códigos de respaldo.",
    "Cifrar cada PDF con AES-256-GCM antes de guardarlo; el original no se conserva.",
    "Listar, buscar, ver dentro de la aplicación, exportar y eliminar documentos.",
    "Agrupar el personal por empresa y mantener un catálogo de empresas.",
    "Registrar cada acción en la auditoría (Ley 1581) y exportar reportes en PDF o CSV.",
    "Mostrar un dashboard de datos con distribución por empresa y tendencia temporal.",
    "Restablecer la contraseña con un código de respaldo, reiniciando el doble factor.",
    "Conversar por API con el modelo configurado en el panel de conexión.",
)


def bloque_de_contexto(resumen: dict[str, Any]) -> str:
    """Redacta el resumen como instrucciones para el modelo.

    El texto va en segunda persona y con las reglas de alcance **dentro del
    mismo bloque**, para que el modelo reciba datos y límites juntos.
    """
    documentos = resumen.get("documentos", {})
    auditoria_resumen = resumen.get("auditoria", {})

    lineas = [
        "CONTEXTO REAL DE DATENJÄGER (datos de este momento; úsalos como única fuente):",
        f"- Documentos cifrados: {documentos.get('total', 0)}",
        f"- Espacio ocupado por esos documentos: {documentos.get('tamano', '0 B')}",
        f"- Titulares registrados: {resumen.get('titulares', 0)}",
        f"- Empresas en el catálogo: {resumen.get('empresas', 0)}",
        f"- Eventos en la auditoría: {auditoria_resumen.get('total', 0)}",
    ]

    por_empresa = documentos.get("por_empresa") or []
    if por_empresa:
        lineas.append("- Documentos por empresa:")
        lineas.extend(
            f"    · {fila['empresa']}: {fila['documentos']}" for fila in por_empresa
        )
    else:
        lineas.append("- Documentos por empresa: todavía no hay ninguno.")

    catalogo = resumen.get("catalogo_empresas") or []
    if catalogo:
        lineas.append("- Catálogo de empresas (personas / documentos):")
        lineas.extend(
            f"    · {fila['nombre']}: {fila['personas']} / {fila['documentos']}"
            for fila in catalogo
        )

    ultimos = documentos.get("ultimos_dias") or []
    if ultimos:
        lineas.append("- Altas por día (los últimos días con actividad):")
        lineas.extend(f"    · {fila['dia']}: {fila['documentos']}" for fila in ultimos)

    acciones = auditoria_resumen.get("por_accion") or []
    if acciones:
        lineas.append("- Acciones más registradas en la auditoría:")
        lineas.extend(f"    · {fila['accion']}: {fila['veces']}" for fila in acciones)

    lineas.append("")
    lineas.append("LO QUE SABE HACER EL SISTEMA:")
    lineas.extend(f"- {capacidad}" for capacidad in CAPACIDADES)

    lineas.append("")
    lineas.append("ALCANCE ESTRICTO (no lo negocies):")
    lineas.append(
        "- Respondes **solo** sobre DatenJäger: sus documentos, titulares, empresas, "
        "auditoría, seguridad, reportes, atajos y este asistente."
    )
    lineas.append(
        "- Si te preguntan algo ajeno al proyecto (temas generales, código, noticias, "
        "opiniones, otras herramientas), dilo en una frase y ofrece volver al sistema. "
        "No respondas la pregunta ajena."
    )
    lineas.append(
        "- Las cifras que des deben salir **de este contexto**. Si un dato no está aquí, "
        "di que no lo tienes y dónde se consulta en la aplicación. No lo estimes ni lo inventes."
    )
    lineas.append(
        "- Nunca reveles ni pidas datos personales (cédulas, nombres de titulares), "
        "contenido de documentos, claves de API, hashes, tokens, rutas del disco ni "
        "credenciales. No tienes acceso a ellos y no debes intentar obtenerlos."
    )
    lineas.append(
        "- No ejecutes acciones sobre el archivo (borrar, exportar, cambiar la "
        "contraseña): explicas cómo se hace en la aplicación, no lo haces tú."
    )

    return "\n".join(lineas)


def contexto_del_proyecto(conn, cursor, usuario_id: Optional[int]) -> str:
    """Contexto listo para inyectar en el prompt del asistente."""
    return bloque_de_contexto(resumen_del_proyecto(conn, cursor, usuario_id))