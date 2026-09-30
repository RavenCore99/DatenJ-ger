# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/services/modelos.py - conexión de modelos de IA (SCRUM-64)

"""Configuración del proveedor de modelos que usa el asistente.

El panel de conexión del frontend necesita tres datos —proveedor, modelo y
punto de conexión— y, opcionalmente, una clave de API. Los tres primeros no
son secretos; la clave sí.

**Dónde vive la clave.** Nunca en el renderer y nunca en claro en disco: se
guarda cifrada con AES-256-GCM en `modelos/config.json`, dentro de un
directorio con permisos `0700`, y la clave del almacén vive en
`modelos/llave.bin` con permisos `0600` — el mismo patrón que ya usa
`backend/tokens.py` para los tokens de confianza. El servicio solo informa de
*si* hay clave configurada, jamás la devuelve.

**Alcance real de esta protección.** Cifrar en disco evita que la clave quede
en un respaldo, en el historial de git o al copiar el proyecto. No protege
frente a quien pueda leer todo el directorio personal del usuario: si puede
leer `llave.bin`, puede descifrar la clave. Para eso haría falta el llavero
del sistema operativo.

**Alcance funcional.** Esta pieza es la pantalla y su almacén; el proveedor
efectivo sigue siendo el que ya usaba el chatbot (Gemini por API), y el
modelo elegido se antepone a su lista de candidatos. Añadir proveedores
locales es la evaluación `SCRUM-37` a `SCRUM-39`, aparcada a propósito.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from backend.errors import DatosInvalidosError
from encryption import EncryptionManager

#: Directorio del almacén y de su clave, con permisos restringidos.
NOMBRE_DIRECTORIO = "modelos"
NOMBRE_ARCHIVO = "config.json"
NOMBRE_CLAVE = "llave.bin"
LONGITUD_CLAVE = 32

#: Proveedores que la interfaz puede ofrecer. Solo el primero tiene
#: implementación hoy; el segundo queda como punto de extensión.
PROVEEDORES = (
    {
        "clave": "gemini",
        "nombre": "Google Gemini",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta",
        "modelos": ("gemini-2.0-flash", "gemini-1.5-flash", "gemini-flash-latest"),
        "implementado": True,
    },
    {
        "clave": "compatible",
        "nombre": "Endpoint compatible con OpenAI",
        "endpoint": "",
        "modelos": (),
        "implementado": False,
    },
)

PROVEEDOR_POR_DEFECTO = PROVEEDORES[0]["clave"]
MODELO_POR_DEFECTO = PROVEEDORES[0]["modelos"][0]

#: Variable de entorno que ya usa `chatbot.py` para la clave de Gemini.
VARIABLE_ENTORNO = "GEMINI_API_KEY"

#: Campos que no son secretos y se guardan en claro.
CAMPOS_PUBLICOS = ("proveedor", "modelo", "endpoint")


# --------------------------------------------------------------------------- #
# Almacén
# --------------------------------------------------------------------------- #


def _directorio(raiz: str | os.PathLike) -> Path:
    """Directorio del almacén, creado con permisos restringidos si falta."""
    directorio = Path(raiz) / NOMBRE_DIRECTORIO
    directorio.mkdir(mode=0o700, parents=True, exist_ok=True)
    return directorio


def _ruta_config(raiz: str | os.PathLike) -> Path:
    return _directorio(raiz) / NOMBRE_ARCHIVO


def _clave_del_almacen(raiz: str | os.PathLike) -> bytes:
    """Clave local del almacén: se crea la primera vez con permisos 0600."""
    ruta = _directorio(raiz) / NOMBRE_CLAVE
    if ruta.exists():
        return ruta.read_bytes()

    import secrets

    clave = secrets.token_bytes(LONGITUD_CLAVE)
    # `os.open` con O_EXCL evita la carrera de dos procesos creando la clave.
    descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as archivo:
        archivo.write(clave)
    return clave


def _leer(raiz: str | os.PathLike) -> dict[str, Any]:
    """Contenido del almacén, o un dict vacío si todavía no existe."""
    ruta = _ruta_config(raiz)
    if not ruta.exists():
        return {}
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return datos if isinstance(datos, dict) else {}


def _escribir(raiz: str | os.PathLike, datos: dict[str, Any]) -> None:
    """Guarda el almacén con permisos 0600."""
    ruta = _ruta_config(raiz)
    descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# Lectura
# --------------------------------------------------------------------------- #


def clave(raiz: str | os.PathLike) -> Optional[str]:
    """Clave de API vigente: la del almacén o, si no hay, la del entorno.

    El entorno tiene prioridad histórica (`.env` con `GEMINI_API_KEY`); lo que
    se guarde desde el panel pasa a ser la fuente cuando el entorno no define
    nada.
    """
    del_entorno = os.getenv(VARIABLE_ENTORNO, "").strip()
    if del_entorno:
        return del_entorno

    datos = _leer(raiz)
    cifrada = datos.get("api_key")
    if not cifrada:
        return None

    try:
        return EncryptionManager.decrypt_str_with_key(cifrada, _clave_del_almacen(raiz))
    except Exception:
        # Una clave del almacén cambiada o un archivo corrupto no deben tumbar
        # el asistente: se comporta como si no hubiera credencial.
        return None


def estado(raiz: str | os.PathLike) -> dict[str, Any]:
    """Resumen de la conexión de modelos para el panel.

    Nunca devuelve la clave: solo si está configurada y de dónde sale.
    """
    datos = _leer(raiz)
    del_entorno = bool(os.getenv(VARIABLE_ENTORNO, "").strip())

    if del_entorno:
        origen = "entorno"
    elif datos.get("api_key"):
        origen = "almacen"
    else:
        origen = None

    proveedor = datos.get("proveedor") or PROVEEDOR_POR_DEFECTO
    modelo = datos.get("modelo") or MODELO_POR_DEFECTO

    return {
        "proveedor": proveedor,
        "modelo": modelo,
        "endpoint": datos.get("endpoint") or _endpoint_por_defecto(proveedor),
        "clave_configurada": bool(origen),
        "origen_clave": origen,
        "proveedores": [dict(proveedor) for proveedor in PROVEEDORES],
    }


def _endpoint_por_defecto(proveedor: str) -> str:
    for descrito in PROVEEDORES:
        if descrito["clave"] == proveedor:
            return descrito["endpoint"]
    return ""


# --------------------------------------------------------------------------- #
# Escritura
# --------------------------------------------------------------------------- #


def guardar(
    raiz: str | os.PathLike,
    *,
    proveedor: Optional[str] = None,
    modelo: Optional[str] = None,
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    quitar_clave: bool = False,
) -> dict[str, Any]:
    """Guarda la conexión elegida y devuelve el estado resultante.

    Args:
        api_key: si llega con valor, se cifra y reemplaza la anterior. Una
            cadena vacía o ``None`` deja la clave como estaba.
        quitar_clave: descarta la clave guardada en el almacén.

    Raises:
        DatosInvalidosError: el proveedor no está en el catálogo.
    """
    datos = _leer(raiz)

    if proveedor:
        proveedor = proveedor.strip()
        if not any(descrito["clave"] == proveedor for descrito in PROVEEDORES):
            raise DatosInvalidosError(f"Proveedor desconocido: {proveedor}")
        datos["proveedor"] = proveedor

    if modelo is not None:
        datos["modelo"] = modelo.strip()

    if endpoint is not None:
        datos["endpoint"] = endpoint.strip()

    if api_key is not None and api_key.strip():
        datos["api_key"] = EncryptionManager.encrypt_str_with_key(
            api_key.strip(), _clave_del_almacen(raiz))
    elif quitar_clave:
        datos.pop("api_key", None)

    _escribir(raiz, datos)
    return estado(raiz)