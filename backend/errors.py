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