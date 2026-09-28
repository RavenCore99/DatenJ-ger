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