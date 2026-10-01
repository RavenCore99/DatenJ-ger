# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/services/autenticacion.py - autenticación sin Tkinter
# Trazabilidad Jira: SCRUM-57 (DatenJäger — Backend).

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

import io

import pyotp
import qrcode

from backend.services import auditoria
from backend.errors import (
    ConflictoError,
    DatosInvalidosError,
    CredencialesInvalidasError,
    CuentaBloqueadaError,
    SegundoFactorInvalidoError,
    UsuarioInexistenteError,
)
from database import (  # noqa: E402
    clear_trust_token,
    password_strength,
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
ACCION_REGISTRO = "Usuario registrado"
ACCION_RESPALDO_MIGRADO = "Códigos de respaldo migrados a hash de un solo sentido"
ACCION_RESTABLECIMIENTO_SOLICITADO = "Restablecimiento: código de respaldo verificado"
ACCION_RESTABLECIMIENTO_FALLIDO = "Restablecimiento fallido: usuario o código no válidos"
ACCION_RESTABLECIMIENTO_OK = "Contraseña restablecida; segundo factor reiniciado"

#: Prefijo del formato **nuevo** de los códigos de respaldo: hashes de un solo
#: sentido (`pbkdf2:sal:hash`, uno por código, separados por comas).
#:
#: El formato anterior cifraba la lista con la clave de sesión —derivada de la
#: contraseña—, de modo que **no se podía comprobar sin la contraseña** y el
#: restablecimiento era imposible justo para quien la había olvidado. Con el
#: hash, comprobar un código no exige descifrar nada, y la lista deja de ser
#: reversible: leer la base ya no entrega los códigos en claro.
PREFIJO_CODIGOS_HASH = "HASH1:"

#: Longitud mínima del nombre de usuario y de la contraseña al dar de alta.
LONGITUD_MINIMA_NOMBRE = 3
PUNTAJE_MINIMO_CONTRASENA = 2


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


def _codigos_como_hash(codigos) -> str:
    """Serializa la lista de códigos como hashes de un solo sentido."""
    return PREFIJO_CODIGOS_HASH + ",".join(hash_contrasena(codigo) for codigo in codigos)


def _serializar_hashes(hashes) -> str:
    """Recompone el valor de ``backup_codes`` a partir de hashes ya calculados."""
    hashes = [guardado for guardado in hashes if guardado]
    if not hashes:
        # Lista agotada: se guarda vacío para que la cuenta sepa que no le quedan
        # códigos, en vez de dejar un prefijo sin contenido que parecería válido.
        return ""
    return PREFIJO_CODIGOS_HASH + ",".join(hashes)


def _consumir_codigo(guardado: str, codigo: str, clave_sesion) -> Optional[str]:
    """Devuelve el nuevo valor de ``backup_codes`` tras usar ``codigo``.

    ``None`` si el código no es válido. Admite los dos formatos:

    * ``HASH1:`` — se compara contra cada hash; no hace falta descifrar nada,
      así que funciona **sin sesión** (lo que habilita el restablecimiento);
    * el antiguo, cifrado con la clave de sesión, que exige ``clave_sesion``.
    """
    if guardado.startswith(PREFIJO_CODIGOS_HASH):
        hashes = [h for h in guardado[len(PREFIJO_CODIGOS_HASH):].split(",") if h]
        for indice, guardado_hash in enumerate(hashes):
            if verify_contrasena(codigo, guardado_hash)[0]:
                del hashes[indice]
                return _serializar_hashes(hashes)
        return None

    if not clave_sesion:
        return None

    crudo = EncryptionManager.decrypt_str_with_key(guardado, clave_sesion)
    disponibles = [guardado_codigo for guardado_codigo in crudo.split(",") if guardado_codigo]
    if codigo not in disponibles:
        return None

    disponibles.remove(codigo)
    if not disponibles:
        return ""
    return EncryptionManager.encrypt_str_with_key(",".join(disponibles), clave_sesion)


def _migrar_codigos_de_respaldo(conn, cursor, usuario_id: int, clave_sesion: bytes) -> bool:
    """Pasa los códigos de respaldo del cifrado reversible al hash (una vez).

    Se ejecuta en un acceso válido, que es cuando la clave de sesión permite
    descifrar la lista. Idempotente: si ya está en hash, no hace nada.
    """
    cursor.execute("SELECT backup_codes FROM Usuarios WHERE id = ?", (usuario_id,))
    fila = cursor.fetchone()
    if not fila or not fila[0] or fila[0].startswith(PREFIJO_CODIGOS_HASH):
        return False

    try:
        crudo = EncryptionManager.decrypt_str_with_key(fila[0], clave_sesion)
    except Exception:
        # Material ilegible (clave distinta): no se toca y se deja constancia.
        return False

    codigos = [guardado for guardado in crudo.split(",") if guardado]
    if not codigos:
        return False

    cursor.execute(
        "UPDATE Usuarios SET backup_codes = ? WHERE id = ?",
        (_codigos_como_hash(codigos), usuario_id),
    )
    conn.commit()
    _auditar(conn, cursor, ACCION_RESPALDO_MIGRADO, usuario_id)
    return True


def registrar_usuario(
    conn,
    cursor,
    *,
    nombre: str,
    contrasena: str,
) -> dict[str, Any]:
    """Da de alta una cuenta nueva y deriva su clave de sesión (SCRUM-57).

    Es la última operación que todavía vivía en ``main.py``. Repite sus mismas
    reglas —nombre de 3 caracteres como mínimo, contraseña de 8 con fortaleza
    al menos «Regular»— y el mismo formato de hash PBKDF2, de modo que una
    cuenta creada aquí es idéntica a las que ya existen.

    La clave de sesión se deriva del ``salt`` del hash recién creado y **no**
    se persiste: solo viaja al estado en memoria para que el alta continúe con
    la configuración del segundo factor.

    Returns:
        dict con ``usuario_id``, ``nombre`` y ``clave_sesion``.

    Raises:
        DatosInvalidosError: nombre o contraseña fuera de las reglas.
        ConflictoError: ya existe una cuenta con ese nombre.
    """
    nombre = (nombre or "").strip()
    contrasena = (contrasena or "").strip()

    if not nombre or not contrasena:
        raise DatosInvalidosError("Ingresa nombre de usuario y contraseña")

    if len(nombre) < LONGITUD_MINIMA_NOMBRE:
        raise DatosInvalidosError(
            f"El nombre de usuario debe tener al menos {LONGITUD_MINIMA_NOMBRE} caracteres")

    puntaje, etiqueta, _color = password_strength(contrasena)
    if len(contrasena) < LONGITUD_MINIMA_CONTRASENA or puntaje < PUNTAJE_MINIMO_CONTRASENA:
        raise DatosInvalidosError(
            f"Contraseña insegura (fortaleza: {etiqueta}). Usa al menos "
            f"{LONGITUD_MINIMA_CONTRASENA} caracteres con mayúsculas, números y símbolos.")

    cursor.execute("SELECT id FROM Usuarios WHERE nombre = ?", (nombre,))
    if cursor.fetchone():
        raise ConflictoError(f"El usuario '{nombre}' ya existe")

    hash_pass = hash_contrasena(contrasena)
    cursor.execute(
        "INSERT INTO Usuarios (nombre, contrasena, fecha_creacion) VALUES (?, ?, ?)",
        (nombre, hash_pass, datetime.now().isoformat()),
    )
    conn.commit()
    usuario_id = cursor.lastrowid

    clave_sesion = _derivar_clave_sesion(contrasena, hash_pass, nombre)

    _auditar(conn, cursor, ACCION_REGISTRO, usuario_id)
    return {"usuario_id": usuario_id, "nombre": nombre, "clave_sesion": clave_sesion}


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
        # Y los códigos de respaldo pasan a hash de un solo sentido: sin esto,
        # el restablecimiento seguiría sin poder comprobarlos sin contraseña.
        _migrar_codigos_de_respaldo(conn, cursor, usuario_id, clave_sesion)

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
    """Consume un código de respaldo. Cada código sirve una sola vez.

    Admite el formato de hash (el actual) y el antiguo cifrado con la clave de
    sesión, para que una cuenta sin migrar siga pudiendo entrar.
    """
    codigo = (codigo or "").strip()
    if not codigo:
        raise SegundoFactorInvalidoError("Ingresa un código de respaldo")

    cursor.execute("SELECT backup_codes FROM Usuarios WHERE id = ?", (usuario_id,))
    fila = cursor.fetchone()
    if not fila or not fila[0]:
        raise SegundoFactorInvalidoError("La cuenta no tiene códigos de respaldo")

    nuevo = _consumir_codigo(fila[0], codigo, clave_sesion)
    if nuevo is None:
        _auditar(conn, cursor, ACCION_RESPALDO_FALLIDO, usuario_id)
        return False

    cursor.execute(
        "UPDATE Usuarios SET backup_codes = ? WHERE id = ?", (nuevo, usuario_id)
    )
    conn.commit()

    _auditar(conn, cursor, ACCION_RESPALDO_OK, usuario_id)
    return True


def verificar_codigo_de_respaldo(
    conn, cursor, *, nombre: str, codigo: str
) -> dict[str, Any]:
    """Comprueba un código de respaldo **sin sesión**, para restablecer (SCRUM-84).

    Es el único paso del restablecimiento que puede autenticar al usuario: el
    secreto TOTP está cifrado con la clave de sesión —derivada de la contraseña
    olvidada— y no se puede descifrar, pero un código de respaldo en formato de
    hash sí se puede comparar. El código se **consume**: no se puede reutilizar
    ni para entrar ni para volver a restablecer.

    Controles aplicados (checklist de `senior-security`):

    * bloqueo por intentos fallidos y recuento de cada fallo, para que los 10^6
      valores posibles de un código de seis dígitos no se puedan recorrer en
      línea;
    * mensaje único para «usuario inexistente» y «código incorrecto», de modo
      que el endpoint no sirva para enumerar cuentas;
    * auditoría de cada intento, con el usuario cuando se conoce.

    Returns:
        ``{"usuario_id", "nombre"}``.

    Raises:
        DatosInvalidosError: falta el usuario o el código, o la cuenta todavía
            guarda los códigos en el formato reversible.
        CuentaBloqueadaError: demasiados intentos fallidos.
        CredencialesInvalidasError: el usuario o el código no son válidos.
    """
    nombre = (nombre or "").strip()
    codigo = (codigo or "").strip()
    if not nombre or not codigo:
        raise DatosInvalidosError("Ingresa tu usuario y un código de respaldo")

    bloqueada, segundos = check_account_locked(cursor, nombre)
    if bloqueada:
        _auditar(conn, cursor, ACCION_BLOQUEO, None)
        minutos = segundos // 60 + 1
        raise CuentaBloqueadaError(
            f"Demasiados intentos fallidos. Intenta de nuevo en {minutos} minuto(s).",
            segundos_restantes=segundos,
        )

    cursor.execute("SELECT id, backup_codes FROM Usuarios WHERE nombre = ?", (nombre,))
    fila = cursor.fetchone()

    if not fila:
        record_failed_attempt(cursor, conn, nombre)
        _auditar(conn, cursor, ACCION_RESTABLECIMIENTO_FALLIDO, None)
        raise CredencialesInvalidasError("El usuario o el código de respaldo no son válidos")

    usuario_id, guardado = fila

    if not guardado or not guardado.startswith(PREFIJO_CODIGOS_HASH):
        # El formato antiguo se cifra con la contraseña: sin ella no hay nada
        # que comparar. Se dice tal cual en vez de dejar el flujo en un error
        # genérico que parecería un fallo del sistema.
        raise DatosInvalidosError(
            "Esta cuenta todavía guarda los códigos en el formato anterior: inicia "
            "sesión una vez con tu contraseña y regenera los códigos de respaldo.")

    nuevo = _consumir_codigo(guardado, codigo, None)
    if nuevo is None:
        record_failed_attempt(cursor, conn, nombre)
        _auditar(conn, cursor, ACCION_RESTABLECIMIENTO_FALLIDO, usuario_id)
        raise CredencialesInvalidasError("El usuario o el código de respaldo no son válidos")

    cursor.execute(
        "UPDATE Usuarios SET backup_codes = ? WHERE id = ?", (nuevo, usuario_id)
    )
    conn.commit()
    reset_failed_attempts(cursor, conn, nombre)

    _auditar(conn, cursor, ACCION_RESTABLECIMIENTO_SOLICITADO, usuario_id)
    return {"usuario_id": usuario_id, "nombre": nombre}


def restablecer_contrasena(
    conn, cursor, *, usuario_id: int, nombre: str, contrasena_nueva: str
) -> dict[str, Any]:
    """Fija la contraseña nueva y **reinicia el segundo factor** (SCRUM-84).

    El secreto TOTP y los códigos de respaldo anteriores quedan cifrados con la
    clave derivada de la contraseña que se ha olvidado, así que no se pueden
    re-cifrar: se descartan. La cuenta vuelve a inscribir el segundo factor en
    el siguiente acceso. Es además lo correcto tras una recuperación —un código
    de respaldo filtrado no debe dejar el 2FA ya resuelto a favor de quien lo
    usó— y se revoca cualquier token de confianza, de modo que el equipo donde
    se restablece tampoco queda recordado.

    Returns:
        ``{"usuario_id", "nombre", "segundo_factor_reiniciado": True}``.

    Raises:
        DatosInvalidosError: la contraseña nueva no cumple las reglas.
        UsuarioInexistenteError: la cuenta no existe.
    """
    contrasena_nueva = (contrasena_nueva or "").strip()
    if len(contrasena_nueva) < LONGITUD_MINIMA_CONTRASENA:
        raise DatosInvalidosError(
            f"La contraseña nueva debe tener al menos {LONGITUD_MINIMA_CONTRASENA} caracteres")

    puntaje, etiqueta, _color = password_strength(contrasena_nueva)
    if puntaje < PUNTAJE_MINIMO_CONTRASENA:
        raise DatosInvalidosError(
            f"Contraseña insegura (fortaleza: {etiqueta}). Usa al menos "
            f"{LONGITUD_MINIMA_CONTRASENA} caracteres con mayúsculas, números y símbolos.")

    cursor.execute("SELECT id FROM Usuarios WHERE id = ?", (usuario_id,))
    if not cursor.fetchone():
        raise UsuarioInexistenteError("La cuenta no existe")

    cursor.execute(
        "UPDATE Usuarios SET contrasena = ?, totp_secret = NULL, totp_enabled = 0, "
        "backup_codes = NULL WHERE id = ?",
        (hash_contrasena(contrasena_nueva), usuario_id),
    )
    clear_trust_token(cursor, conn, usuario_id)
    conn.commit()

    reset_failed_attempts(cursor, conn, nombre)
    _auditar(conn, cursor, ACCION_RESTABLECIMIENTO_OK, usuario_id)

    return {"usuario_id": usuario_id, "nombre": nombre, "segundo_factor_reiniciado": True}


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


# ---------------------------------------------------------------------- #
# Gestión de la propia cuenta (SCRUM-25)
# ---------------------------------------------------------------------- #

ACCION_CAMBIO_CONTRASENA = "Cambio de contraseña"
ACCION_2FA_ACTIVADO = "Configuración 2FA completada"
ACCION_2FA_DESACTIVADO = "2FA desactivado"
ACCION_CODIGOS_REGENERADOS = "Códigos de respaldo regenerados"
ACCION_CONFIANZA_REVOCADA = "Token de confianza revocado"

CODIGOS_DE_RESPALDO = 5
LONGITUD_CODIGO = 6
LONGITUD_MINIMA_CONTRASENA = 8


def _codigos_de_respaldo() -> list[str]:
    """Genera códigos de un solo uso con el generador criptográfico."""
    return [
        "".join(str(secrets.randbelow(10)) for _ in range(LONGITUD_CODIGO))
        for _ in range(CODIGOS_DE_RESPALDO)
    ]


def generar_secreto(usuario_nombre: str) -> dict[str, str]:
    """Prepara un secreto TOTP nuevo y su URI de aprovisionamiento.

    El secreto todavía no se guarda: se activa en ``activar_segundo_factor``
    una vez el usuario demuestra que su autenticador lo acepta.
    """
    secreto = pyotp.random_base32()
    uri = pyotp.TOTP(secreto).provisioning_uri(name=usuario_nombre, issuer_name="DatenJäger")
    return {"secreto": secreto, "uri": uri}


def generar_qr(uri: str) -> bytes:
    """Devuelve el PNG del código QR del URI, para mostrarlo en el cliente."""
    qr = qrcode.QRCode(version=1, box_size=8, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    imagen = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    return buffer.getvalue()


def activar_segundo_factor(conn, cursor, *, usuario_id: int, clave_sesion: bytes,
                           secreto: str, codigo: str) -> list[str]:
    """Activa el 2FA tras comprobar un código del secreto propuesto.

    Devuelve los códigos de respaldo en claro: es la única vez que se muestran.
    """
    if not _codigo_valido(codigo):
        raise SegundoFactorInvalidoError("El código debe tener 6 dígitos")
    if not pyotp.TOTP(secreto).verify(codigo):
        raise SegundoFactorInvalidoError("El código es incorrecto o ha expirado")

    codigos = _codigos_de_respaldo()
    cursor.execute(
        "UPDATE Usuarios SET totp_secret = ?, totp_enabled = 1, backup_codes = ? WHERE id = ?",
        (
            EncryptionManager.encrypt_str_with_key(secreto, clave_sesion),
            # Los códigos se guardan como hash: así se pueden comprobar sin la
            # contraseña y la base deja de contener material reversible.
            _codigos_como_hash(codigos),
            usuario_id,
        ),
    )
    conn.commit()
    _auditar(conn, cursor, ACCION_2FA_ACTIVADO, usuario_id)
    return codigos


def desactivar_segundo_factor(conn, cursor, *, usuario_id: int, clave_sesion: bytes,
                              codigo: str) -> None:
    """Desactiva el 2FA. Exige un código vigente y descarta los tokens de confianza."""
    secreto = _secreto_legible(cursor, usuario_id, clave_sesion)
    if not _codigo_valido(codigo) or not pyotp.TOTP(secreto).verify(codigo):
        raise SegundoFactorInvalidoError("El código es incorrecto o ha expirado")

    cursor.execute(
        "UPDATE Usuarios SET totp_secret = NULL, totp_enabled = 0, backup_codes = NULL"
        " WHERE id = ?",
        (usuario_id,),
    )
    clear_trust_token(cursor, conn, usuario_id)
    conn.commit()
    _auditar(conn, cursor, ACCION_2FA_DESACTIVADO, usuario_id)


def regenerar_codigos_de_respaldo(conn, cursor, *, usuario_id: int, clave_sesion: bytes,
                                  codigo: str) -> list[str]:
    """Emite un juego nuevo de códigos de respaldo y anula los anteriores."""
    secreto = _secreto_legible(cursor, usuario_id, clave_sesion)
    if not _codigo_valido(codigo) or not pyotp.TOTP(secreto).verify(codigo):
        raise SegundoFactorInvalidoError("El código es incorrecto o ha expirado")

    codigos = _codigos_de_respaldo()
    cursor.execute(
        "UPDATE Usuarios SET backup_codes = ? WHERE id = ?",
        (_codigos_como_hash(codigos), usuario_id),
    )
    conn.commit()
    _auditar(conn, cursor, ACCION_CODIGOS_REGENERADOS, usuario_id)
    return codigos


def revocar_token_confianza(conn, cursor, *, usuario_id: int) -> None:
    """Invalida el token de confianza: el próximo acceso volverá a pedir el 2FA."""
    clear_trust_token(cursor, conn, usuario_id)
    _auditar(conn, cursor, ACCION_CONFIANZA_REVOCADA, usuario_id)


def cambiar_contrasena(conn, cursor, *, usuario_id: int, nombre: str, clave_sesion: bytes,
                       contrasena_actual: str, contrasena_nueva: str,
                       codigo: str) -> bytes:
    """Cambia la contraseña y re-cifra los secretos con la clave nueva.

    Devuelve la clave de sesión nueva: la anterior deja de servir en cuanto se
    guarda, así que el cliente debe reemplazarla.

    El 2FA es obligatorio para este cambio: quien tenga la sesión abierta en un
    equipo desatendido no puede apropiarse de la cuenta cambiando la contraseña.
    """
    if not contrasena_actual or not contrasena_nueva:
        raise DatosInvalidosError("Debes indicar la contraseña actual y la nueva")
    if len(contrasena_nueva) < LONGITUD_MINIMA_CONTRASENA:
        raise DatosInvalidosError(
            f"La contraseña nueva debe tener al menos {LONGITUD_MINIMA_CONTRASENA} caracteres")

    puntaje, etiqueta, _color = password_strength(contrasena_nueva)
    if puntaje < 2:
        raise DatosInvalidosError(
            f"Contraseña débil (fortaleza: {etiqueta}). Usa mayúsculas, números y símbolos.")

    cursor.execute(
        "SELECT contrasena, totp_enabled, totp_secret, backup_codes FROM Usuarios WHERE id = ?",
        (usuario_id,),
    )
    fila = cursor.fetchone()
    if not fila:
        raise UsuarioInexistenteError("La cuenta no existe")
    hash_guardado, totp_activo, totp_cifrado, respaldo_cifrado = fila

    correcta, _rehash = verify_contrasena(contrasena_actual, hash_guardado)
    if not correcta:
        raise CredencialesInvalidasError("La contraseña actual es incorrecta")

    if not totp_activo or not totp_cifrado:
        raise segundo_factor_no_configurado()

    secreto = EncryptionManager.decrypt_str_with_key(totp_cifrado, clave_sesion)
    if not _codigo_valido(codigo) or not pyotp.TOTP(secreto).verify(codigo):
        raise SegundoFactorInvalidoError("El código del autenticador es incorrecto o expiró")

    hash_nuevo = hash_contrasena(contrasena_nueva)
    partes = hash_nuevo.split(":")
    sal_nueva = partes[1] if len(partes) == 3 else nombre
    clave_nueva = EncryptionManager.derive_session_key(contrasena_nueva, sal_nueva)

    respaldo_nuevo = respaldo_cifrado
    # Los códigos actuales son hashes (no dependen de la clave); solo el formato
    # antiguo, cifrado con la clave de sesión, hay que re-cifrar.
    if respaldo_cifrado and not respaldo_cifrado.startswith(PREFIJO_CODIGOS_HASH):
        respaldo_nuevo = EncryptionManager.encrypt_str_with_key(
            EncryptionManager.decrypt_str_with_key(respaldo_cifrado, clave_sesion),
            clave_nueva,
        )

    cursor.execute(
        "UPDATE Usuarios SET contrasena = ?, totp_secret = ?, backup_codes = ? WHERE id = ?",
        (
            hash_nuevo,
            EncryptionManager.encrypt_str_with_key(secreto, clave_nueva),
            respaldo_nuevo,
            usuario_id,
        ),
    )
    # La contraseña nueva deja inservible cualquier confianza anterior.
    clear_trust_token(cursor, conn, usuario_id)
    conn.commit()

    _auditar(conn, cursor, ACCION_CAMBIO_CONTRASENA, usuario_id)
    return clave_nueva


def _secreto_legible(cursor, usuario_id: int, clave_sesion: bytes) -> str:
    """Descifra el secreto TOTP de la cuenta o falla si el 2FA no está activo."""
    cursor.execute("SELECT totp_secret FROM Usuarios WHERE id = ?", (usuario_id,))
    fila = cursor.fetchone()
    if not fila or not fila[0]:
        raise segundo_factor_no_configurado()
    return EncryptionManager.decrypt_str_with_key(fila[0], clave_sesion)


def segundo_factor_no_configurado() -> SegundoFactorInvalidoError:
    """Error uniforme cuando la cuenta no tiene 2FA activo."""
    return SegundoFactorInvalidoError(
        "La cuenta no tiene el segundo factor configurado: actívalo antes de continuar")


def _codigo_valido(codigo: str) -> bool:
    """Un código del autenticador son 6 dígitos."""
    return bool(codigo) and len(codigo.strip()) == 6 and codigo.strip().isdigit()
