# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/services/semantica.py - búsqueda semántica y clasificación (Fase 6)

"""Servicio de búsqueda semántica y clasificación automática (evaluación).

Backend-only, sin Tkinter. Cubre los dos usos de la Fase 6 (buscar por
significado y clasificar por tipo) que comparten la misma tubería: extraer
texto del PDF, trocearlo y calcular embeddings.

Decisiones:

* **Modelo**: ``sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2``
  vía `fastembed` (ONNX Runtime, CPU, sin PyTorch). Se importa **de forma
  perezosa** para no cargar el modelo en el arranque ni exigirlo como
  dependencia del resto de la aplicación.

* **Índice**: un archivo SQLite **propio** (no la base principal) con los
  fragmentos, su texto cifrado y su embedding. No se toca el esquema de
  `database.py`.

* **Privacidad (opción B)**: el texto del fragmento se guarda **cifrado en
  reposo** con AES-256-GCM usando una clave de 256 bits derivada del
  ``usuario_nombre`` con el mismo PBKDF2-600k que los documentos, pero
  **derivada una sola vez por usuario** (salt fijo del índice) y reutilizada
  con nonce aleatorio por fragmento. Es la misma fuerza criptográfica que usa
  el sistema, sin repetir el costoso KDF por cada fragmento. El embedding
  (vector float32) se guarda en claro porque la búsqueda lo necesita en bloque
  y no es reversible a texto completo.

* **Almacén vectorial**: los vectores se comparan con coseno en numpy. Para
  cientos de documentos (miles de fragmentos) esto es milisegundos, así que no
  hace falta ChromaDB.

Funciones públicas: :func:`trocear`, :func:`indexar_corpus`,
:func:`buscar`, y el clasificador por reglas :func:`clasificar_texto`.
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any, Optional, Sequence

import numpy as np

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from encryption import EncryptionManager

# --------------------------------------------------------------------------- #
# Constantes
# --------------------------------------------------------------------------- #

MODELO_DEFAULT = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIMENSION = 384

#: Tamaño objetivo de fragmento (caracteres) y solape entre contiguos.
CHUNK_CARACTERES = 600
CHUNK_SOLAPE = 100

#: Categorías de clasificación (Uso B, línea base por reglas).
CATEGORIAS = ("contrato_laboral", "afiliacion", "reporte_seguridad_social")

#: Palabras clave por categoría, para la línea base sin modelo.
#: El orden importa: se evalúa en este orden y gana la primera con más aciertos.
_REGLAS: dict[str, tuple[str, ...]] = {
    "contrato_laboral": (
        "contrato de trabajo", "contrato laboral", "término fijo",
        "término indefinido", "cláusula", "empleador", "trabajador",
        "jornada laboral", "salario", "preaviso", "contratante",
    ),
    "afiliacion": (
        "formulario de afiliación", "afiliación", "afiliado",
        "novedad de ingreso", "registro de ingreso", "cotizante",
        "aporte del afiliado",
    ),
    "reporte_seguridad_social": (
        "seguridad social", "planilla", "cotización", "aporte",
        "pensión", "riesgos laborales", "arl", "parafiscales",
        "certificado de aportes", "reporte de aportes", "autoliquidación",
        "caja de compensación",
    ),
}

#: Modelo cargado de forma perezosa (singleton del proceso).
_modelo: Any = None


# --------------------------------------------------------------------------- #
# Modelo (importación perezosa)
# --------------------------------------------------------------------------- #

def _obtener_modelo() -> Any:
    """Devuelve el modelo de embeddings, cargándolo la primera vez."""
    global _modelo
    if _modelo is None:
        from fastembed import TextEmbedding  # importación perezosa
        _modelo = TextEmbedding(model_name=MODELO_DEFAULT)
    return _modelo


def liberar_modelo() -> None:
    """Descarga el modelo de embeddings de memoria, liberando la RAM (~680 MB).

    El modelo se recarga solo en la siguiente operación (indexar o buscar),
    con el coste de ~2.4 s de calentamiento. Pensado para que el llamador
    (el servidor) pueda soltar la RAM cuando no hay búsqueda activa.
    """
    global _modelo
    _modelo = None


def _embed(textos: Sequence[str]) -> np.ndarray:
    """Calcula los embeddings de ``textos`` (matriz ``(n, DIMENSION)`` float32)."""
    modelo = _obtener_modelo()
    vectores = np.array(list(modelo.embed(list(textos))), dtype=np.float32)
    return vectores


# --------------------------------------------------------------------------- #
# Cifrado de fragmentos: clave por usuario derivada una sola vez
# --------------------------------------------------------------------------- #

_SALT_CLAVE = "kdf_salt_fragmentos"


def _salt_fragmentos(indice_conn) -> bytes:
    """Devuelve (creando si no existe) el salt estable del índice."""
    fila = indice_conn.execute(
        "SELECT valor FROM meta WHERE clave = ?", (_SALT_CLAVE,)).fetchone()
    if fila:
        return bytes.fromhex(fila[0])
    salt = os.urandom(16)
    indice_conn.execute(
        "INSERT INTO meta (clave, valor) VALUES (?, ?) "
        "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
        (_SALT_CLAVE, salt.hex()),
    )
    indice_conn.commit()
    return salt


def _clave_fragmentos(indice_conn, usuario_nombre: str) -> bytes:
    """Clave de 256 bits para los fragmentos del usuario.

    Derivada con el mismo PBKDF2-600k que los documentos, pero una sola vez por
    usuario (salt fijo del índice) en lugar de por cada fragmento: misma fuerza
    criptográfica, sin el coste redundante.
    """
    return EncryptionManager.derive_key(usuario_nombre, _salt_fragmentos(indice_conn))


def _cifrar_fragmento(texto: str, clave: bytes) -> bytes:
    """Cifra un fragmento con AES-256-GCM usando la clave por usuario."""
    nonce = os.urandom(12)
    return nonce + AESGCM(clave).encrypt(nonce, texto.encode("utf-8"), None)


def _descifrar_fragmento(blob: bytes, clave: bytes) -> str:
    """Descifra un fragmento cifrado con :func:`_cifrar_fragmento`."""
    nonce, ciphertext = blob[:12], blob[12:]
    return AESGCM(clave).decrypt(nonce, ciphertext, None).decode("utf-8")


# --------------------------------------------------------------------------- #
# Extracción y troceado
# --------------------------------------------------------------------------- #

def texto_pdf(pdf_bytes: bytes) -> str:
    """Extrae el texto completo de un PDF en memoria (bytes en claro)."""
    import fitz  # PyMuPDF, importado perezosamente
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        partes = [pagina.get_text() for pagina in doc]
    finally:
        doc.close()
    return "\n".join(partes)


def trocear(texto: str, tamaño: int = CHUNK_CARACTERES, solape: int = CHUNK_SOLAPE) -> list[str]:
    """Trocea ``texto`` en fragmentos de ~``tamaño`` caracteres con solape.

    Normaliza espacios en blanco y corta en límite de palabra cuando es posible.
    Devuelve la lista de fragmentos (vacía si no hay texto aprovechable).
    """
    texto = " ".join(str(texto or "").split())
    if not texto:
        return []
    if len(texto) <= tamaño:
        return [texto]

    fragmentos: list[str] = []
    inicio = 0
    n = len(texto)
    while inicio < n:
        fin = min(inicio + tamaño, n)
        if fin < n:
            espacio = texto.rfind(" ", inicio, fin)
            if espacio > inicio + tamaño // 2:
                fin = espacio
        fragmento = texto[inicio:fin].strip()
        if fragmento:
            fragmentos.append(fragmento)
        if fin >= n:
            break
        inicio = max(fin - solape, inicio + 1)

    return fragmentos


# --------------------------------------------------------------------------- #
# Índice (SQLite propio)
# --------------------------------------------------------------------------- #

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS fragmentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    documento_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    indice INTEGER NOT NULL,
    texto_cifrado BLOB NOT NULL,
    embedding BLOB NOT NULL,
    n_caracteres INTEGER NOT NULL,
    modelo TEXT NOT NULL,
    creado TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fragmentos_doc ON fragmentos(documento_id);
CREATE INDEX IF NOT EXISTS idx_fragmentos_usuario ON fragmentos(usuario_id);
CREATE TABLE IF NOT EXISTS meta (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
"""


def conectar_indice(ruta: str):
    """Abre (y crea si hace falta) el archivo de índice semántico."""
    import sqlite3
    conn = sqlite3.connect(ruta, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_ESQUEMA)
    conn.commit()
    return conn


def ruta_indice(db_path: str) -> str:
    """Deriva la ruta del índice: al lado de la base de datos activa.

    Ejemplo: ``/datos/base_datos_pdfs.db`` -> ``/datos/base_datos_pdfs.semantico.db``.
    """
    return f"{os.path.splitext(db_path)[0]}.semantico.db"


# --------------------------------------------------------------------------- #
# Indexado del corpus
# --------------------------------------------------------------------------- #

def _marcado() -> str:
    return datetime.now().isoformat()


def indexar_corpus(
    conn,
    cursor,
    *,
    usuario_id: int,
    usuario_nombre: str,
    indice_conn,
    documento_ids: Optional[list[int]] = None,
    registrar_progreso=lambda msg: None,
) -> dict:
    """Reconstruye el índice semántico de los documentos del usuario.

    Por cada documento: descifra (reutilizando ``backend.services.documentos``),
    extrae el texto, lo trocea y guarda, en el índice, el fragmento cifrado y
    su embedding. Los documentos que no aporten texto se omiten sin romper.

    Returns:
        dict con ``documentos``, ``fragmentos``, ``caracteres`` y ``segundos``.
    """
    from backend.services import documentos

    documento_ids = list(documento_ids or [])
    if not documento_ids:
        cursor.execute("SELECT id FROM PDFs WHERE usuario_id = ? ORDER BY id", (usuario_id,))
        documento_ids = [fila[0] for fila in cursor.fetchall()]

    modelo = _obtener_modelo()
    inicio = time.time()

    # Se limpia el índice previo de este usuario para que sea idempotente.
    indice_conn.execute("DELETE FROM fragmentos WHERE usuario_id = ?", (usuario_id,))

    # Clave por usuario derivada una sola vez (no por fragmento).
    clave = _clave_fragmentos(indice_conn, usuario_nombre)

    total_docs = 0
    total_frags = 0
    total_chars = 0

    for documento_id in documento_ids:
        try:
            pdf_bytes, _nombre = documentos.leer_documento(
                conn,
                cursor,
                usuario_id=usuario_id,
                documento_id=documento_id,
                usuario_nombre=usuario_nombre,
                registrar_apertura=False,
            )
        except Exception as exc:  # noqa: BLE001 — un documento ilegible no tumba el índice
            registrar_progreso(f"  [omitido] documento {documento_id}: {exc}")
            continue

        texto = texto_pdf(pdf_bytes)
        if not texto.strip():
            registrar_progreso(f"  [sin texto] documento {documento_id}")
            continue

        fragmentos = trocear(texto)
        if not fragmentos:
            continue

        embeddings = _embed(fragmentos)
        filas = []
        for idx, (frag, emb) in enumerate(zip(fragmentos, embeddings)):
            cifrado = _cifrar_fragmento(frag, clave)
            filas.append((
                documento_id,
                usuario_id,
                idx,
                cifrado,
                np.asarray(emb, dtype=np.float32).tobytes(),
                len(frag),
                MODELO_DEFAULT,
                _marcado(),
            ))

        indice_conn.executemany(
            "INSERT INTO fragmentos "
            "(documento_id, usuario_id, indice, texto_cifrado, embedding, "
            "n_caracteres, modelo, creado) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            filas,
        )
        total_docs += 1
        total_frags += len(filas)
        total_chars += sum(len(f) for f in fragmentos)
        registrar_progreso(f"  documento {documento_id}: {len(filas)} fragmento(s)")

    indice_conn.execute(
        "INSERT INTO meta (clave, valor) VALUES ('modelo', ?) "
        "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
        (MODELO_DEFAULT,),
    )
    indice_conn.execute(
        "INSERT INTO meta (clave, valor) VALUES ('actualizado', ?) "
        "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
        (_marcado(),),
    )
    indice_conn.commit()

    return {
        "documentos": total_docs,
        "fragmentos": total_frags,
        "caracteres": total_chars,
        "segundos": round(time.time() - inicio, 2),
        "modelo": MODELO_DEFAULT,
    }


# --------------------------------------------------------------------------- #
# Búsqueda
# --------------------------------------------------------------------------- #

def buscar(
    indice_conn,
    *,
    consulta: str,
    usuario_id: int,
    usuario_nombre: str,
    k: int = 5,
) -> list[dict]:
    """Devuelve hasta ``k`` documentos distintos, cada uno por su fragmento más parecido.

    Returns:
        lista de dicts con ``documento_id``, ``indice``, ``score`` (coseno
        normalizado), ``texto`` (descifrado) y ``caracteres``, ordenada por
        similitud descendente y sin repetir documento.
    """
    consulta = (consulta or "").strip()
    if not consulta:
        return []

    cursor = indice_conn.execute(
        "SELECT id, documento_id, indice, texto_cifrado, embedding, n_caracteres "
        "FROM fragmentos WHERE usuario_id = ?",
        (usuario_id,),
    )
    filas = cursor.fetchall()
    if not filas:
        return []

    ids = [f[0] for f in filas]
    matriz = np.vstack([np.frombuffer(f[4], dtype=np.float32) for f in filas])

    emb_consulta = _embed([consulta])[0]

    # coseno normalizado
    matriz_norm = matriz / np.linalg.norm(matriz, axis=1, keepdims=True)
    consulta_norm = emb_consulta / (np.linalg.norm(emb_consulta) + 1e-9)
    similitudes = matriz_norm @ consulta_norm

    orden = np.argsort(similitudes)[::-1]

    clave = _clave_fragmentos(indice_conn, usuario_nombre)
    resultados = []
    documentos_vistos: set[int] = set()

    # Se recorre por similitud descendente y se conserva solo el mejor fragmento
    # de cada documento, para que los resultados sean documentos distintos en
    # lugar de varias tajadas del mismo PDF ocupando los primeros puestos.
    for pos in orden:
        _id, documento_id, indice, cifrado, _emb, n_caracteres = filas[pos]
        if documento_id in documentos_vistos:
            continue
        documentos_vistos.add(documento_id)
        try:
            texto = _descifrar_fragmento(bytes(cifrado), clave)
        except Exception as exc:  # noqa: BLE001
            texto = f"[no descifrable: {exc}]"
        resultados.append({
            "fragmento_id": _id,
            "documento_id": documento_id,
            "indice": indice,
            "score": round(float(similitudes[pos]), 4),
            "texto": texto,
            "caracteres": n_caracteres,
        })
        if len(resultados) >= k:
            break

    return resultados


# --------------------------------------------------------------------------- #
# Estado del índice
# --------------------------------------------------------------------------- #

def estado_indice(indice_conn, usuario_id: int) -> dict:
    """Estado del índice del usuario: indexado, conteos y fecha de actualización.

    No carga el modelo ni descifra nada: es una lectura ligera para que el
    frontend decida entre «índice vacío, pulsa para indexar» y «índice listo».
    """
    fragmentos, documentos = indice_conn.execute(
        "SELECT COUNT(*), COUNT(DISTINCT documento_id) FROM fragmentos WHERE usuario_id = ?",
        (usuario_id,),
    ).fetchone()

    actualizado = indice_conn.execute(
        "SELECT valor FROM meta WHERE clave = 'actualizado'").fetchone()
    modelo = indice_conn.execute(
        "SELECT valor FROM meta WHERE clave = 'modelo'").fetchone()

    return {
        "indexado": int(fragmentos) > 0,
        "fragmentos": int(fragmentos),
        "documentos": int(documentos),
        "actualizado": actualizado[0] if actualizado else None,
        "modelo": modelo[0] if modelo else None,
    }


# --------------------------------------------------------------------------- #
# Clasificación (Uso B) — línea base por reglas
# --------------------------------------------------------------------------- #

def clasificar_texto(texto: str) -> str:
    """Asigna una categoría por reglas de palabras clave.

    Devuelve una de :data:`CATEGORIAS` o ``"sin_clasificar"``.
    """
    texto = " ".join(str(texto or "").lower().split())
    if not texto:
        return "sin_clasificar"

    mejor = "sin_clasificar"
    mejor_puntaje = 0
    for categoria, claves in _REGLAS.items():
        puntaje = sum(1 for clave in claves if clave in texto)
        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor = categoria

    return mejor if mejor_puntaje > 0 else "sin_clasificar"