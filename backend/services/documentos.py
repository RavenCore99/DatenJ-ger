# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/services/documentos.py - CRUD de documentos (PDFs)

"""Servicio de documentos: CRUD de PDFs cifrados.

Extraído de ``pdf_manager.py`` (que conserva solo la construcción de la
interfaz). Todas las funciones de este módulo son invocables sin Tkinter:
reciben ``conn``/``cursor`` y el usuario explícitamente, y retornan datos
o levantan una excepción tipada.

Contrato de cifrado: el PDF se guarda cifrado con AES-256-GCM usando como
clave el nombre del usuario (``usuario_nombre``), tal como hacía el panel
original. El servicio no cambia el esquema ni el algoritmo.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional, Sequence

from encryption import EncryptionManager
from backend.errors import (
    DatosInvalidosError,
    NoEncontradoError,
    NoAutenticadoError,
)
from backend.services import auditoria

# Acciones registradas en la tabla Auditoria por este servicio.
ACCION_AGREGAR = "Agregar PDF (Encriptado AES-256-GCM)"
ACCION_ELIMINAR = "Eliminar PDF"
ACCION_EDITAR = "Editar metadatos PDF"
ACCION_ABRIR = "Abrir / Descifrar PDF"
ACCION_EXPORTAR = "Exportar PDF"

#: Columnas que consume el panel documental, en el orden histórico del Treeview.
_COLUMNAS_LISTADO = """
    p.id, p.nombre, p.descripcion, p.tamano, p.fecha_subida,
    pe.cedula, pe.nombres, pe.empresa
"""


class DocumentoError(DatosInvalidosError):
    """Error propio del servicio de documentos."""


def _ahora() -> str:
    return datetime.now().isoformat()


def _fila_a_dict(fila: Sequence[Any]) -> dict:
    """Convierte una fila del listado en dict con nombres estables."""
    return {
        "id": fila[0],
        "nombre": fila[1],
        "descripcion": fila[2],
        "tamano": fila[3],
        "fecha_subida": fila[4],
        "cedula": fila[5],
        "nombres": fila[6],
        "empresa": fila[7],
    }


def _validar_usuario(usuario_id: Optional[int]) -> int:
    if usuario_id is None:
        raise NoAutenticadoError("No hay usuario autenticado")
    return usuario_id


def _registrar_auditoria(
    cursor,
    conn,
    accion: str,
    usuario_id: Optional[int],
    documento_id: Optional[int] = None,
) -> None:
    """Registra el evento en el servicio de auditoría (best-effort)."""
    auditoria.registrar_evento(conn, cursor, accion, usuario_id, documento_id)


# --------------------------------------------------------------------------- #
# Consultas
# --------------------------------------------------------------------------- #

def listar_documentos(conn, cursor, usuario_id: Optional[int], termino: str = "") -> list[dict]:
    """Lista los documentos del usuario, opcionalmente filtrados.

    Args:
        conn: conexión SQLite activa.
        cursor: cursor de esa conexión.
        usuario_id: propietario de los documentos.
        termino: texto a buscar en nombre, descripción, cédula, nombres o
            empresa. Vacío = sin filtro.

    Returns:
        Lista de dicts (ver ``_fila_a_dict``), ordenada por fecha descendente.
    """
    usuario_id = _validar_usuario(usuario_id)
    termino = (termino or "").strip()

    if not termino:
        cursor.execute(
            f"""
            SELECT {_COLUMNAS_LISTADO}
            FROM PDFs p
            LEFT JOIN Personas pe ON p.persona_id = pe.id
            WHERE p.usuario_id = ?
            ORDER BY p.fecha_subida DESC
            """,
            (usuario_id,),
        )
    else:
        cursor.execute(
            f"""
            SELECT {_COLUMNAS_LISTADO}
            FROM PDFs p
            LEFT JOIN Personas pe ON p.persona_id = pe.id
            WHERE p.usuario_id = ? AND (
                p.nombre LIKE ? OR p.descripcion LIKE ?
                OR pe.cedula LIKE ? OR pe.nombres LIKE ?
                OR pe.empresa LIKE ?
            )
            ORDER BY p.fecha_subida DESC
            """,
            (usuario_id, *[f"%{termino}%"] * 5),
        )

    return [_fila_a_dict(fila) for fila in cursor.fetchall()]


def obtener_documento(conn, cursor, usuario_id: Optional[int], documento_id: int) -> dict:
    """Devuelve los metadatos de un documento del usuario.

    Raises:
        NoEncontradoError: el documento no existe o es de otro usuario.
    """
    usuario_id = _validar_usuario(usuario_id)
    cursor.execute(
        f"""
        SELECT {_COLUMNAS_LISTADO}
        FROM PDFs p
        LEFT JOIN Personas pe ON p.persona_id = pe.id
        WHERE p.id = ? AND p.usuario_id = ?
        """,
        (documento_id, usuario_id),
    )
    fila = cursor.fetchone()
    if not fila:
        raise NoEncontradoError("PDF no encontrado")
    return _fila_a_dict(fila)


def contar_documentos(conn, cursor, usuario_id: Optional[int]) -> int:
    """Cuenta los documentos del usuario (para KPIs y dashboard)."""
    usuario_id = _validar_usuario(usuario_id)
    cursor.execute("SELECT COUNT(*) FROM PDFs WHERE usuario_id = ?", (usuario_id,))
    fila = cursor.fetchone()
    return int(fila[0]) if fila else 0


# --------------------------------------------------------------------------- #
# Escritura
# --------------------------------------------------------------------------- #

def _resolver_persona(cursor, cedula: str, nombres: str, empresa: Optional[str]) -> int:
    """Crea o actualiza el titular asociado al documento y devuelve su id."""
    cursor.execute("SELECT id FROM Personas WHERE cedula = ?", (cedula,))
    fila = cursor.fetchone()
    if fila:
        persona_id = fila[0]
        cursor.execute(
            "UPDATE Personas SET nombres = ?, empresa = ? WHERE id = ?",
            (nombres, empresa, persona_id),
        )
        return persona_id

    cursor.execute(
        "INSERT INTO Personas (cedula, nombres, empresa) VALUES (?, ?, ?)",
        (cedula, nombres, empresa),
    )
    return cursor.lastrowid


def crear_documento(
    conn,
    cursor,
    *,
    usuario_id: Optional[int],
    usuario_nombre: str,
    nombre: str,
    datos: bytes,
    descripcion: str = "",
    cedula: Optional[str] = None,
    nombres: Optional[str] = None,
    empresa: Optional[str] = None,
    datos_encriptados: bool = True,
) -> dict:
    """Registra un documento en el corpus.

    Args:
        datos: contenido del PDF en claro (el servicio lo cifra).
        cedula / nombres / empresa: titular asociado. Si ``cedula`` y
            ``nombres`` vienen informados se crea o actualiza la persona.
        datos_encriptados: cifrar con AES-256-GCM antes de guardar.

    Returns:
        Dict con ``id``, ``nombre``, ``persona_id`` y ``tamano``.

    Raises:
        DocumentoError: faltan datos obligatorios.
        NoAutenticadoError: no hay usuario.
    """
    usuario_id = _validar_usuario(usuario_id)

    nombre = (nombre or "").strip()
    if not nombre:
        raise DocumentoError("El nombre del documento es obligatorio")
    if not datos:
        raise DocumentoError("El documento está vacío")
    if bool(cedula) != bool(nombres):
        raise DocumentoError("Cédula y nombres deben informarse juntos")

    tamano = len(datos)
    blob = EncryptionManager.encrypt_data(datos, usuario_nombre) if datos_encriptados else datos

    try:
        persona_id = None
        if cedula and nombres:
            persona_id = _resolver_persona(cursor, str(cedula), str(nombres), empresa or None)

        cursor.execute(
            "INSERT INTO PDFs (nombre, descripcion, datos, datos_encriptados, "
            "tamano, fecha_subida, usuario_id, persona_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                nombre,
                descripcion or "",
                blob,
                1 if datos_encriptados else 0,
                tamano,
                _ahora(),
                usuario_id,
                persona_id,
            ),
        )
        documento_id = cursor.lastrowid
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    _registrar_auditoria(cursor, conn, ACCION_AGREGAR, usuario_id, documento_id)

    return {
        "id": documento_id,
        "nombre": nombre,
        "persona_id": persona_id,
        "tamano": tamano,
    }


def crear_documento_desde_archivo(
    conn,
    cursor,
    *,
    usuario_id: Optional[int],
    usuario_nombre: str,
    ruta: str,
    descripcion: str = "",
    cedula: Optional[str] = None,
    nombres: Optional[str] = None,
    empresa: Optional[str] = None,
) -> dict:
    """Variante de ``crear_documento`` que lee el PDF desde disco.

    Raises:
        DocumentoError: la ruta no existe o no es legible.
    """
    if not ruta:
        raise DocumentoError("No se seleccionó ningún archivo")
    if not os.path.isfile(ruta):
        raise DocumentoError(f"No existe el archivo: {ruta}")

    with open(ruta, "rb") as archivo:
        datos = archivo.read()

    return crear_documento(
        conn,
        cursor,
        usuario_id=usuario_id,
        usuario_nombre=usuario_nombre,
        nombre=os.path.basename(ruta),
        datos=datos,
        descripcion=descripcion,
        cedula=cedula,
        nombres=nombres,
        empresa=empresa,
    )


def actualizar_documento(
    conn,
    cursor,
    *,
    usuario_id: Optional[int],
    documento_id: int,
    nombre: Optional[str] = None,
    descripcion: Optional[str] = None,
    cedula: Optional[str] = None,
    nombres: Optional[str] = None,
    empresa: Optional[str] = None,
) -> dict:
    """Actualiza metadatos del documento y del titular asociado.

    Solo se escriben los campos informados (``None`` = sin cambio). Si
    ``cedula`` trae valor se propaga ``nombres``/``empresa`` a la persona
    vinculada, replicando el comportamiento del panel original.

    Raises:
        DocumentoError: el nombre queda vacío.
        NoEncontradoError: el documento no existe o es de otro usuario.
    """
    usuario_id = _validar_usuario(usuario_id)
    actual = obtener_documento(conn, cursor, usuario_id, documento_id)

    nuevo_nombre = actual["nombre"] if nombre is None else str(nombre).strip()
    if not nuevo_nombre:
        raise DocumentoError("El nombre no puede estar vacío")

    nueva_descripcion = actual["descripcion"] if descripcion is None else descripcion

    try:
        cursor.execute(
            "UPDATE PDFs SET nombre = ?, descripcion = ? WHERE id = ? AND usuario_id = ?",
            (nuevo_nombre, nueva_descripcion, documento_id, usuario_id),
        )
        if cedula:
            cursor.execute(
                """UPDATE Personas SET nombres = ?, empresa = ?
                   WHERE id = (SELECT persona_id FROM PDFs WHERE id = ?)""",
                (nombres, empresa or None, documento_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    _registrar_auditoria(cursor, conn, ACCION_EDITAR, usuario_id, documento_id)
    return obtener_documento(conn, cursor, usuario_id, documento_id)


def eliminar_documento(conn, cursor, usuario_id: Optional[int], documento_id: int) -> dict:
    """Elimina definitivamente un documento del usuario.

    Returns:
        Dict con ``id`` y ``nombre`` del documento eliminado.

    Raises:
        NoEncontradoError: el documento no existe o es de otro usuario.
    """
    usuario_id = _validar_usuario(usuario_id)
    documento = obtener_documento(conn, cursor, usuario_id, documento_id)

    try:
        cursor.execute(
            "DELETE FROM PDFs WHERE id = ? AND usuario_id = ?",
            (documento_id, usuario_id),
        )
        if cursor.rowcount == 0:
            conn.rollback()
            raise NoEncontradoError("PDF no encontrado")
        conn.commit()
    except NoEncontradoError:
        raise
    except Exception:
        conn.rollback()
        raise

    _registrar_auditoria(cursor, conn, ACCION_ELIMINAR, usuario_id, documento_id)
    return {"id": documento["id"], "nombre": documento["nombre"]}


# --------------------------------------------------------------------------- #
# Lectura / exportación de contenido
# --------------------------------------------------------------------------- #

def leer_documento(
    conn,
    cursor,
    *,
    usuario_id: Optional[int],
    documento_id: int,
    usuario_nombre: str,
    registrar_apertura: bool = True,
) -> tuple[bytes, str]:
    """Devuelve ``(bytes_en_claro, nombre)`` del documento.

    Raises:
        NoEncontradoError: el documento no existe o es de otro usuario.
        DocumentoError: el descifrado falla (clave distinta o blob corrupto).
    """
    usuario_id = _validar_usuario(usuario_id)
    cursor.execute(
        "SELECT datos, nombre, datos_encriptados FROM PDFs WHERE id = ? AND usuario_id = ?",
        (documento_id, usuario_id),
    )
    fila = cursor.fetchone()
    if not fila:
        raise NoEncontradoError("PDF no encontrado")

    datos_guardados, nombre, encriptado = fila

    if registrar_apertura:
        _registrar_auditoria(cursor, conn, ACCION_ABRIR, usuario_id, documento_id)

    try:
        if encriptado:
            return EncryptionManager.decrypt_data(bytes(datos_guardados), usuario_nombre), nombre
        return bytes(datos_guardados), nombre
    except Exception as exc:
        raise DocumentoError(f"No se pudo descifrar el documento: {exc}") from exc


def exportar_documento(
    conn,
    cursor,
    *,
    usuario_id: Optional[int],
    documento_id: int,
    usuario_nombre: str,
    destino: str,
) -> str:
    """Descifra el documento y lo escribe en ``destino``.

    Returns:
        La ruta destino escrita.

    Raises:
        DocumentoError: no hay destino o falla la escritura.
    """
    if not destino:
        raise DocumentoError("No se indicó un destino para exportar")

    datos, _nombre = leer_documento(
        conn,
        cursor,
        usuario_id=usuario_id,
        documento_id=documento_id,
        usuario_nombre=usuario_nombre,
        registrar_apertura=False,
    )

    try:
        with open(destino, "wb") as archivo:
            archivo.write(datos)
    except Exception as exc:
        raise DocumentoError(f"Error al exportar: {exc}") from exc

    _registrar_auditoria(cursor, conn, ACCION_EXPORTAR, usuario_id, documento_id)
    return destino