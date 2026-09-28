# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/services/autenticacion.py - autenticación sin Tkinter

"""Servicio de autenticación (SCRUM-22).

Mueve al backend la *orquestación* del inicio de sesión que vivía en
`main.py`: comprobar bloqueo, verificar la contraseña, rehashear hashes
heredados, derivar la clave de sesión, migrar el material 2FA de `ENC:` a
`ENCK:`, decidir si hace falta el segundo factor y validarlo.

Lo que **no** cambia, y por eso las cuentas y los documentos existentes
siguen funcionando:

* ``hash_contrasena`` / ``verify_contrasena`` (PBKDF2-SHA256, 260 000
  iteraciones) siguen en `database.py` y se invocan tal cual.
* ``EncryptionManager`` (derivación de la clave de sesión y AES-256-GCM de
  los secretos TOTP y de los códigos de respaldo) sigue en `encryption.py`.
* Las mismas reglas de bloqueo de cuenta (`failed_attempts`,
  `locked_until`) y el mismo formato de hash.

Errores: `CredencialesInvalidasError`, `UsuarioInexistenteError`,
`CuentaBloqueadaError` y `SegundoFactorInvalidoError` (`backend/errors.py`).
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Any, Optional

import pyotp

from backend.services import auditoria
from backend.errors import (
    CredencialesInvalidasError,
    CuentaBloqueadaError,
    SegundoFactorInvalidoError,
    UsuarioInexistenteError,
)
from database import (
    check_account_locked,
    check_trust_token,
    hash_contrasena,
    record_failed_attempt,
    reset_failed_attempts,
    set_trust_token,
    verify_contrasena,
)
from encryption import EncryptionManager

#: La contraseña es correcta y, si la cuenta usa 2FA, ya se validó.
ESTADO_COMPLETADO = "completado"

#: La contraseña es correcta pero falta el segundo factor.
ESTADO_SEGUNDO_FACTOR = "segundo_factor"

#: Horas de validez del token de confianza de dispositivo.
HORAS_CONFIANZA_POR_DEFECTO = 48

#: Longitud del código de respaldo que genera el sistema.
LONGITUD_CODIGO_RESPALDO = 6

#: Número de códigos de respaldo generados de una vez.
CODIGOS_RESPALDO = 10

ACCION_LOGIN_OK = "Login exitoso"
ACCION_LOGIN_CONTRASENA_INCORRECTA = "Login fallido: contraseña incorrecta"
ACCION_LOGIN_USUARIO_INEXISTENTE = "Login fallido: usuario inexistente"
ACCION_REHASH = "Migración hash contraseña (SHA-256→PBKDF2)"
ACCION_BLOQUEO = "Cuenta bloqueada por intentos fallidos"
ACCION_2FA_OK = "2FA verificado exitosamente"
ACCION_2FA_FALLIDO = "2FA fallido: código incorrecto o expirado"
ACCION_2FA_OMITIDO = "Login con token de confianza (2FA omitido)"
ACCION_RESPALDO_OK = "Login con código de respaldo"
ACCION_RESPALDO_FALLIDO = "Código de respaldo inválido"


def _auditar(conn, cursor, accion: str, usuario_id: Optional[int]) -> None:
    """Registra el evento de auditoría sin interrumpir el flujo de acceso."""
    auditoria.registrar_evento(conn, cursor, accion, usuario_id)


def _derivar_clave_sesion(contrasena: str, hash_de_referencia: str, nombre: str) -> bytes:
    """Deriva la clave de sesión con la misma regla que la versión anterior.

    El `salt` del hash PBKDF2 actúa como sal de la derivación; si el hash es
    del formato heredado (sin prefijo `pbkdf2:`) se usa el nombre de usuario,
    idéntico al comportamiento previo.
    """
    partes = hash_de_referencia.split(":") if hash_de_referencia.startswith("pbkdf2:") else []
    sal = partes[1] if len(partes) == 3 else nombre
    return EncryptionManager.derive_session_key(contrasena, sal)


def _migrar_material_2fa(
    conn, cursor, usuario_id: int, contrasena: str, clave_sesion: bytes
) -> bool:
    """Pasa el secreto TOTP y los códigos de respaldo de `ENC:` a `ENCK:`.

    Antes de este paso el material estaba cifrado con la contraseña; a partir
    de aquí queda cifrado con la clave de sesión, que solo vive en memoria.
    Devuelve True si hubo migración efectiva.
    """
    cursor.execute(
        "SELECT totp_secret, backup_codes FROM Usuarios WHERE id = ?", (usuario_id,)
    )
    fila = cursor.fetchone()
    if not fila:
        return False

    totp_cifrado, respaldo_cifrado = fila
    migrado = False

    if totp_cifrado and totp_cifrado.startswith("ENC:"):
        claro = EncryptionManager.decrypt_str(totp_cifrado, contrasena)
        totp_cifrado = EncryptionManager.encrypt_str_with_key(claro, clave_sesion)
        migrado = True

    if respaldo_cifrado and respaldo_cifrado.startswith("ENC:"):
        claro = EncryptionManager.decrypt_str(respaldo_cifrado, contrasena)
        respaldo_cifrado = EncryptionManager.encrypt_str_with_key(claro, clave_sesion)
        migrado = True

    if migrado:
        cursor.execute(
            "UPDATE Usuarios SET totp_secret = ?, backup_codes = ? WHERE id = ?",
            (totp_cifrado, respaldo_cifrado, usuario_id),
        )
        conn.commit()

    return migrado


def autenticar(
    conn,
    cursor,
    *,
    nombre: str,
    contrasena: str,
    token_confianza: Optional[str] = None,
    horas_confianza: int = 0,
) -> dict[str, Any]:
    """Valida las credenciales y decide si hace falta el segundo factor.

    Returns:
        dict con ``estado`` (``completado`` o ``segundo_factor``),
        ``usuario_id``, ``nombre`` y ``clave_sesion`` — esta última solo
        cuando el acceso quedó completo.

    Raises:
        CuentaBloqueadaError: la cuenta está bloqueada temporalmente.
        UsuarioInexistenteError: no hay usuario con ese nombre.
        CredencialesInvalidasError: la contraseña no es correcta.
    """
    if not nombre or not contrasena:
        raise CredencialesInvalidasError("Ingresa nombre de usuario y contraseña")

    bloqueada, segundos = check_account_locked(cursor, nombre)
    if bloqueada:
        _auditar(conn, cursor, ACCION_BLOQUEO, None)
        minutos = segundos // 60 + 1
        raise CuentaBloqueadaError(
            f"Demasiados intentos fallidos. Intenta de nuevo en {minutos} minuto(s).",
            segundos_restantes=segundos,
        )

    cursor.execute(
        "SELECT id, contrasena, totp_enabled FROM Usuarios WHERE nombre = ?", (nombre,)
    )
    fila = cursor.fetchone()
    if not fila:
        _auditar(conn, cursor, ACCION_LOGIN_USUARIO_INEXISTENTE, None)
        raise UsuarioInexistenteError(f"El usuario '{nombre}' no existe en el sistema")

    usuario_id, hash_guardado, totp_habilitado = fila
    correcta, necesita_rehash = verify_contrasena(contrasena, hash_guardado)

    if not correcta:
        record_failed_attempt(cursor, conn, nombre)
        _auditar(conn, cursor, ACCION_LOGIN_CONTRASENA_INCORRECTA, usuario_id)
        raise CredencialesInvalidasError("Contraseña incorrecta")

    # Hash heredado (SHA-256): se actualiza a PBKDF2 en el mismo acceso.
    hash_nuevo = None
    if necesita_rehash:
        hash_nuevo = hash_contrasena(contrasena)
        cursor.execute(
            "UPDATE Usuarios SET contrasena = ? WHERE id = ?", (hash_nuevo, usuario_id)
        )
        _auditar(conn, cursor, ACCION_REHASH, usuario_id)
        conn.commit()

    reset_failed_attempts(cursor, conn, nombre)

    hash_referencia = hash_nuevo or hash_guardado
    clave_sesion = _derivar_clave_sesion(contrasena, hash_referencia, nombre)

    if totp_habilitado:
        _migrar_material_2fa(conn, cursor, usuario_id, contrasena, clave_sesion)

    _auditar(conn, cursor, ACCION_LOGIN_OK, usuario_id)

    if totp_habilitado and not _token_aceptado(
        cursor, usuario_id, token_confianza, horas_confianza
    ):
        return {
            "estado": ESTADO_SEGUNDO_FACTOR,
            "usuario_id": usuario_id,
            "nombre": nombre,
            "clave_sesion": clave_sesion,
            "segundo_factor_omitido": False,
        }

    if totp_habilitado:
        _auditar(conn, cursor, ACCION_2FA_OMITIDO, usuario_id)

    return {
        "estado": ESTADO_COMPLETADO,
        "usuario_id": usuario_id,
        "nombre": nombre,
        "clave_sesion": clave_sesion,
        "segundo_factor_omitido": bool(totp_habilitado),
    }


def _token_aceptado(cursor, usuario_id: int, token: Optional[str], horas: int) -> bool:
    """¿El dispositivo presenta un token de confianza vigente?"""
    if horas <= 0 or not token:
        return False
    return bool(check_trust_token(cursor, usuario_id, token))


def verificar_segundo_factor(
    conn, cursor, *, usuario_id: int, clave_sesion: bytes, codigo: str
) -> bool:
    """Valida un código TOTP de 6 dígitos contra el secreto del usuario.

    El secreto se descifra con la clave de sesión; la ventana de validez es la
    de `pyotp` por defecto, la misma que usaba `main.py`.
    """
    codigo = (codigo or "").strip()
    if len(codigo) != 6 or not codigo.isdigit():
        raise SegundoFactorInvalidoError("Ingresa un código válido de 6 dígitos")

    cursor.execute("SELECT totp_secret FROM Usuarios WHERE id = ?", (usuario_id,))
    fila = cursor.fetchone()
    if not fila or not fila[0]:
        raise SegundoFactorInvalidoError("La cuenta no tiene segundo factor configurado")

    try:
        secreto = EncryptionManager.decrypt_str_with_key(fila[0], clave_sesion)
        valido = bool(pyotp.TOTP(secreto).verify(codigo))
    except SegundoFactorInvalidoError:
        raise
    except Exception as error:
        raise SegundoFactorInvalidoError(
            "No se pudo validar el código; vuelve a iniciar sesión"
        ) from error

    _auditar(
        conn, cursor, ACCION_2FA_OK if valido else ACCION_2FA_FALLIDO, usuario_id
    )
    return valido


def usar_codigo_de_respaldo(
    conn, cursor, *, usuario_id: int, clave_sesion: bytes, codigo: str
) -> bool:
    """Consume un código de respaldo. Cada código sirve una sola vez."""
    codigo = (codigo or "").strip()
    if not codigo:
        raise SegundoFactorInvalidoError("Ingresa un código de respaldo")

    cursor.execute("SELECT backup_codes FROM Usuarios WHERE id = ?", (usuario_id,))
    fila = cursor.fetchone()
    if not fila or not fila[0]:
        raise SegundoFactorInvalidoError("La cuenta no tiene códigos de respaldo")

    crudo = EncryptionManager.decrypt_str_with_key(fila[0], clave_sesion)
    disponibles = [codigo_guardado for codigo_guardado in crudo.split(",") if codigo_guardado]

    if codigo not in disponibles:
        _auditar(conn, cursor, ACCION_RESPALDO_FALLIDO, usuario_id)
        return False

    disponibles.remove(codigo)
    nuevo_cifrado = EncryptionManager.encrypt_str_with_key(
        ",".join(disponibles), clave_sesion
    )
    cursor.execute(
        "UPDATE Usuarios SET backup_codes = ? WHERE id = ?", (nuevo_cifrado, usuario_id)
    )
    conn.commit()

    _auditar(conn, cursor, ACCION_RESPALDO_OK, usuario_id)
    return True


def generar_token_confianza(
    conn, cursor, *, usuario_id: int, horas: int = HORAS_CONFIANZA_POR_DEFECTO
) -> Optional[str]:
    """Emite un token de confianza de dispositivo y lo guarda en la cuenta.

    Devuelve el token para que el cliente lo conserve en su almacén
    (ver `backend/tokens.py`); con ``horas <= 0`` la confianza está desactivada
    y no se emite nada.
    """
    if horas <= 0:
        return None

    token = secrets.token_hex(32)
    expira = (datetime.now() + timedelta(hours=horas)).isoformat()
    set_trust_token(cursor, conn, usuario_id, token, expira)
    return token


def token_confianza_vigente(conn, cursor, *, usuario_id: int, token: str) -> bool:
    """Indica si el token presentado sigue siendo válido para la cuenta."""
    return bool(check_trust_token(cursor, usuario_id, token))


def estado_de_cuenta(conn, cursor, *, usuario_id: int) -> dict[str, Any]:
    """Resumen del estado de seguridad de una cuenta (para el panel de cuenta)."""
    cursor.execute(
        "SELECT nombre, totp_enabled, totp_secret, backup_codes, locked_until, failed_attempts "
        "FROM Usuarios WHERE id = ?",
        (usuario_id,),
    )
    fila = cursor.fetchone()
    if not fila:
        raise UsuarioInexistenteError("La cuenta no existe")

    nombre, totp_habilitado, totp_cifrado, respaldo_cifrado, bloqueada_hasta, intentos = fila

    return {
        "usuario_id": usuario_id,
        "nombre": nombre,
        "segundo_factor_habilitado": bool(totp_habilitado),
        "tiene_secreto": bool(totp_cifrado),
        "codigos_de_respaldo_configurados": bool(respaldo_cifrado),
        "bloqueada_hasta": bloqueada_hasta,
        "intentos_fallidos": intentos or 0,
    }