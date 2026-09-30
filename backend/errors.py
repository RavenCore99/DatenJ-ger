# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/errors.py - errores comunes de la capa backend

"""Excepciones transversales de la capa backend.

Los servicios levantan estos errores; la UI (o el servidor local) los
captura y decide cómo mostrarlos. Los servicios nunca muestran mensajes.
"""


class BackendError(Exception):
    """Error base de la capa backend.

    Attributes:
        mensaje: texto apto para mostrar al usuario.
    """

    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


class NoAutenticadoError(BackendError):
    """No hay sesión activa o el usuario no tiene permiso sobre el recurso."""


class NoEncontradoError(BackendError):
    """El recurso pedido no existe (o no pertenece al usuario)."""


class DatosInvalidosError(BackendError):
    """Los datos entregados no cumplen las validaciones del servicio."""


class ConflictoError(BackendError):
    """La operación choca con un registro existente (p. ej. cédula duplicada)."""


class CredencialesInvalidasError(BackendError):
    """El usuario o la contraseña no coinciden con ningún registro."""


class UsuarioInexistenteError(CredencialesInvalidasError):
    """El nombre de usuario no está registrado.

    Hereda de `CredencialesInvalidasError` para que el servidor local pueda
    responder lo mismo que ante una contraseña incorrecta sin revelar qué
    usuarios existen.
    """


class CuentaBloqueadaError(BackendError):
    """La cuenta está bloqueada temporalmente por intentos fallidos."""

    def __init__(self, mensaje: str, segundos_restantes: int = 0):
        super().__init__(mensaje)
        self.segundos_restantes = segundos_restantes


class SegundoFactorInvalidoError(BackendError):
    """El código 2FA o el código de respaldo no son válidos."""


class BaseDeDatosError(BackendError):
    """La base de datos no se pudo abrir o preparar.

    Es un fallo de arranque, no de operación: sin base no hay sesión, ni
    documentos, ni auditoría. La distinción importa porque el servicio puede
    estar vivo y la base caída, y en ese caso la interfaz debe decirlo con
    esas palabras en lugar de dejar caer cada pantalla por su cuenta.
    """