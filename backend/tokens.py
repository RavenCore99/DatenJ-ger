# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/tokens.py - almacén cifrado de tokens de confianza

"""Almacén de tokens de confianza cifrado en disco (SCRUM-25).

Los tokens de confianza permiten omitir el segundo factor en un equipo de
confianza. Antes vivían en claro dentro de `config.json`, mezclados con las
preferencias de la aplicación.

Ahora cada token se guarda cifrado con AES-256-GCM en `tokens_confianza/`:

* un archivo por cuenta, nombrado con un resumen del nombre del usuario, así
  que el nombre no queda expuesto en el listado del directorio;
* la clave del almacén vive en `tokens_confianza/llave.bin` con permisos 0600;
  el directorio se crea con 0700.

**Alcance real de esta protección.** Cifrar en disco evita que el token se lea
al copiar `config.json`, al sincronizarlo con la nube, en un respaldo o al
inspeccionar el directorio del proyecto. No protege frente a quien pueda leer
todo el directorio personal del usuario: si puede leer `llave.bin`, puede
descifrar los tokens. Para eso haría falta el llavero del sistema operativo.

El token en claro nunca se entrega al frontend: el servicio lo guarda y lo
recupera por su cuenta. El frontend solo ve si hay un dispositivo de confianza
y puede pedir que se revoque.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from pathlib import Path

from encryption import EncryptionManager

NOMBRE_DIRECTORIO = "tokens_confianza"
NOMBRE_CLAVE = "llave.bin"
EXTENSION = ".token"
PREFIJO_CIFRADO = "ENCK:"
LONGITUD_CLAVE = 32


def ruta_almacen(raiz: str | os.PathLike) -> Path:
    """Directorio del almacén, creado con permisos restringidos si falta."""
    directorio = Path(raiz) / NOMBRE_DIRECTORIO
    directorio.mkdir(mode=0o700, parents=True, exist_ok=True)
    return directorio


def _ruta_clave(directorio: Path) -> Path:
    return directorio / NOMBRE_CLAVE


def _clave(directorio: Path) -> bytes:
    """Clave local del almacén: se crea la primera vez con permisos 0600."""
    ruta = _ruta_clave(directorio)
    if ruta.exists():
        return ruta.read_bytes()

    clave = secrets.token_bytes(LONGITUD_CLAVE)
    # `os.open` con O_EXCL evita la carrera de dos procesos creando la clave.
    descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as archivo:
        archivo.write(clave)
    return clave


def _archivo_de(directorio: Path, usuario: str) -> Path:
    """Archivo del usuario, con el nombre reducido a un resumen."""
    resumen = hashlib.sha256(usuario.strip().lower().encode("utf-8")).hexdigest()[:16]
    return directorio / f"{resumen}{EXTENSION}"


def guardar(raiz: str | os.PathLike, usuario: str, token: str) -> Path:
    """Guarda el token de la cuenta cifrado y devuelve el archivo escrito."""
    directorio = ruta_almacen(raiz)
    archivo = _archivo_de(directorio, usuario)

    descriptor = os.open(archivo, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "wb") as salida:
        salida.write(
            EncryptionManager.encrypt_str_with_key(token, _clave(directorio)).encode("utf-8"))
    return archivo


def leer(raiz: str | os.PathLike, usuario: str) -> str | None:
    """Devuelve el token guardado de la cuenta, o None si no hay ninguno."""
    directorio = ruta_almacen(raiz)
    archivo = _archivo_de(directorio, usuario)
    if not archivo.exists():
        return None

    contenido = archivo.read_text(encoding="utf-8")
    if not contenido.startswith(PREFIJO_CIFRADO):
        # El almacén solo contiene material cifrado: un archivo en claro es un
        # residuo (o una manipulación) y no debe conceder confianza alguna.
        return None

    try:
        return EncryptionManager.decrypt_str_with_key(contenido, _clave(directorio))
    except Exception:
        # Una clave cambiada o un archivo corrupto no deben impedir el acceso:
        # simplemente se pierde la confianza y se vuelve a pedir el 2FA.
        return None


def borrar(raiz: str | os.PathLike, usuario: str) -> bool:
    """Descarta el token de la cuenta. Devuelve si había algo que borrar."""
    archivo = _archivo_de(ruta_almacen(raiz), usuario)
    if not archivo.exists():
        return False
    archivo.unlink()
    return True


def hay_almacen(raiz: str | os.PathLike, usuario: str) -> bool:
    """Indica si la cuenta tiene un token guardado."""
    return _archivo_de(ruta_almacen(raiz), usuario).exists()


def exportar_en_claro(raiz: str | os.PathLike, usuario: str) -> str | None:
    """Devuelve el token en claro para la migración desde `config.json`.

    Es la única función que entrega el token: existe para el guion de
    migración de los tokens que hoy están en claro en `config.json`.
    """
    return leer(raiz, usuario) or ""


def migrar_desde_config(raiz: str | os.PathLike, tokens: dict) -> dict:
    """Traslada los tokens en claro de `config.json` al almacén cifrado.

    `tokens` es el mapa ``{usuario: token}`` que hoy guarda la configuración.
    Devuelve un resumen de lo migrado; no modifica el archivo de configuración.
    """
    migrados, conservados = {}, {}

    for usuario, token in (tokens or {}).items():
        if not isinstance(token, str) or not token.strip():
            conservados[usuario] = token
            continue
        guardar(raiz, usuario, token)
        migrados[usuario] = True

    return {"migrados": sorted(migrados), "conservados": sorted(conservados)}