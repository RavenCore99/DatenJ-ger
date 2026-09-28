# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/server.py - servidor local que expone la capa de comandos por HTTP

"""Puente Python <-> Electron (SCRUM-21).

Expone `backend/commands.py` por HTTP en la interfaz de bucle local, para
que el renderer de Electron consuma el backend de Python sin conocer su
implementación. Es el mecanismo decidido en la Fase 0 de `planning.md`.

Decisiones de diseño:

* **Solo bucle local.** Escucha en `127.0.0.1`; no se publica en la red.
* **Token de proceso.** Cada arranque genera un token aleatorio que el
  proceso que lanza el servidor (Electron o la app de escritorio) conoce y
  el renderer reenvía en la cabecera ``X-DatenJager-Token``. Sin él, otro
  programa local o una página web no puede operar sobre los documentos.
* **Errores tipados -> códigos HTTP.** Las excepciones de
  `backend/errors.py` se traducen al formato ``{"detail": {"tipo",
  "mensaje"}}`` que espera `src/lib/api.js`.
* **La sesión no se crea aquí.** La verificación de credenciales y el 2FA
  viven en `main.py`; este servidor solo *hereda* una sesión ya autenticada
  (``POST /api/sesion/heredar``) o informa que el inicio de sesión todavía
  no está disponible (``POST /api/sesion`` -> 501).

Arranque:

    python -m backend.server --puerto 8756 [--token TOKEN] [--db RUTA]
"""

from __future__ import annotations

import argparse
import base64
import binascii
import logging
import secrets
import sys
import threading
import time
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.commands import ComandosDatenJager
from backend.errors import (
    BackendError,
    ConflictoError,
    DatosInvalidosError,
    NoAutenticadoError,
    NoEncontradoError,
)
from backend.services.auditoria import LIMITE_VISOR
from backend.state import AppState
from database import conectar_db

LOG = logging.getLogger("datenjager.servidor")

VERSION_API = "1.0"

#: Código HTTP asociado a cada error de la capa de negocio.
CODIGOS_HTTP: tuple[tuple[type[BackendError], int], ...] = (
    (NoAutenticadoError, 401),
    (NoEncontradoError, 404),
    (ConflictoError, 409),
    (DatosInvalidosError, 422),
    (BackendError, 400),
)


# --------------------------------------------------------------------------- #
# Modelos de entrada
# --------------------------------------------------------------------------- #


class SesionHeredada(BaseModel):
    """Sesión ya autenticada que el proceso de escritorio entrega al puente."""

    usuario_id: int
    nombre: str
    session_key: str = Field(description="clave de sesión en base64")


class DocumentoNuevo(BaseModel):
    """Alta de documento: bytes en base64 o una ruta del sistema de archivos."""

    nombre: str
    contenido_b64: Optional[str] = None
    ruta: Optional[str] = None
    descripcion: Optional[str] = None
    cedula: Optional[str] = None
    nombres: Optional[str] = None
    empresa: Optional[str] = None


class DocumentoPatch(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    cedula: Optional[str] = None
    nombres: Optional[str] = None
    empresa: Optional[str] = None


class PersonaNueva(BaseModel):
    cedula: str
    nombres: str
    empresa: Optional[str] = None


class PersonaPatch(BaseModel):
    cedula: Optional[str] = None
    nombres: Optional[str] = None
    empresa: Optional[str] = None


class Destino(BaseModel):
    destino: str


class Exportacion(BaseModel):
    destino: str
    formato: str = "pdf"


class MensajeChat(BaseModel):
    mensaje: str


class InicioChat(BaseModel):
    contexto: str = ""


# --------------------------------------------------------------------------- #
# Ayudas
# --------------------------------------------------------------------------- #


def _decodificar_base64(datos: str) -> bytes:
    """Decodifica base64 aceptando el alfabeto estándar y el de URL."""
    limpio = datos.strip()
    relleno = "=" * (-len(limpio) % 4)
    try:
        return base64.b64decode(limpio + relleno, validate=True)
    except (binascii.Error, ValueError):
        try:
            return base64.urlsafe_b64decode(limpio + relleno)
        except (binascii.Error, ValueError) as error:
            raise DatosInvalidosError("El contenido del documento no es base64 válido") from error


def _codigo_para(error: BackendError) -> int:
    for tipo, codigo in CODIGOS_HTTP:
        if isinstance(error, tipo):
            return codigo
    return 400


def _cuerpo_error(error: BackendError) -> dict[str, Any]:
    return {"detail": {"tipo": type(error).__name__, "mensaje": str(error)}}


# --------------------------------------------------------------------------- #
# Aplicación
# --------------------------------------------------------------------------- #


def crear_app(
    comandos: ComandosDatenJager,
    token: str | None = None,
) -> FastAPI:
    """Construye la aplicación HTTP sobre una fachada de comandos.

    `token` es el secreto compartido con el proceso que lanza el servidor.
    Si es `None`, el servidor queda abierto en bucle local (solo para
    pruebas unitarias).
    """
    app = FastAPI(
        title="DatenJäger — servicio local",
        version=VERSION_API,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    # ---------------------------------------------------------------- #
    # Errores
    # ---------------------------------------------------------------- #

    @app.exception_handler(BackendError)
    async def manejar_error_backend(_peticion: Request, error: BackendError) -> JSONResponse:
        return JSONResponse(status_code=_codigo_para(error), content=_cuerpo_error(error))

    @app.exception_handler(Exception)
    async def manejar_error_inesperado(_peticion: Request, error: Exception) -> JSONResponse:
        # El detalle real queda en el log del proceso; al cliente solo va un
        # mensaje genérico para no filtrar rutas ni trazas internas.
        LOG.exception("Error inesperado atendiendo la petición", exc_info=error)
        return JSONResponse(
            status_code=500,
            content={"detail": {"tipo": "ErrorInterno", "mensaje": "Error interno del servicio local"}},
        )

    # ---------------------------------------------------------------- #
    # Control de acceso
    # ---------------------------------------------------------------- #

    async def exigir_token(
        x_datenjager_token: str | None = Header(default=None, alias="X-DatenJager-Token"),
    ) -> None:
        if token is None:
            return
        if not x_datenjager_token or not secrets.compare_digest(x_datenjager_token, token):
            raise NoAutenticadoError("Token del servicio local ausente o inválido")

    protegido = [Depends(exigir_token)]

    # ---------------------------------------------------------------- #
    # Salud y sesión
    # ---------------------------------------------------------------- #

    @app.get("/api/salud")
    async def salud() -> dict[str, Any]:
        """Disponibilidad del servicio. Sin datos sensibles: sin token."""
        return {
            "estado": "ok",
            "version": VERSION_API,
            "autenticado": comandos.sesion_actual()["autenticado"],
        }

    @app.get("/api/sesion", dependencies=protegido)
    async def sesion_actual() -> dict[str, Any]:
        return comandos.sesion_actual()

    @app.post("/api/sesion", dependencies=protegido)
    async def iniciar_sesion() -> JSONResponse:
        pendientes = comandos.operaciones_pendientes()
        return JSONResponse(
            status_code=501,
            content={
                "detail": {
                    "tipo": "NoImplementadoError",
                    "mensaje": (
                        "El inicio de sesión todavía se atiende en la aplicación de "
                        "escritorio: la verificación de credenciales y el 2FA no se han "
                        "movido al backend."
                    ),
                    "pendiente": sorted(clave for clave, falta in pendientes.items() if falta),
                }
            },
        )

    @app.post("/api/sesion/heredar", dependencies=protegido)
    async def heredar_sesion(cuerpo: SesionHeredada) -> dict[str, Any]:
        """Adopta una sesión ya autenticada por el proceso de escritorio."""
        try:
            clave = _decodificar_base64(cuerpo.session_key)
        except DatosInvalidosError:
            raise DatosInvalidosError("La clave de sesión no es base64 válido") from None

        comandos.iniciar_sesion(cuerpo.usuario_id, cuerpo.nombre, clave)
        return comandos.sesion_actual()

    @app.delete("/api/sesion", dependencies=protegido)
    async def cerrar_sesion() -> dict[str, bool]:
        comandos.cerrar_sesion()
        return {"cerrado": True}

    # ---------------------------------------------------------------- #
    # Documentos
    # ---------------------------------------------------------------- #

    @app.get("/api/documentos", dependencies=protegido)
    async def listar_documentos(buscar: str = "") -> list[dict[str, Any]]:
        return comandos.listar_documentos(buscar)

    @app.get("/api/documentos/conteo", dependencies=protegido)
    async def contar_documentos() -> dict[str, int]:
        return {"total": comandos.contar_documentos()}

    @app.get("/api/documentos/{documento_id}", dependencies=protegido)
    async def obtener_documento(documento_id: int) -> dict[str, Any]:
        return comandos.obtener_documento(documento_id)

    @app.post("/api/documentos", status_code=201, dependencies=protegido)
    async def crear_documento(cuerpo: DocumentoNuevo) -> dict[str, Any]:
        titulares = {"cedula": cuerpo.cedula, "nombres": cuerpo.nombres, "empresa": cuerpo.empresa}

        if cuerpo.contenido_b64:
            return comandos.agregar_documento_bytes(
                cuerpo.nombre, _decodificar_base64(cuerpo.contenido_b64),
                descripcion=cuerpo.descripcion or "", **titulares)

        if not cuerpo.ruta:
            raise DatosInvalidosError(
                "Hay que enviar 'contenido_b64' o 'ruta' para agregar el documento")

        return comandos.agregar_documento(
            cuerpo.ruta, cuerpo.descripcion or "", **titulares)

    @app.patch("/api/documentos/{documento_id}", dependencies=protegido)
    async def actualizar_documento(documento_id: int, cuerpo: DocumentoPatch) -> dict[str, Any]:
        return comandos.actualizar_documento(documento_id, **cuerpo.model_dump(exclude_none=True))

    @app.delete("/api/documentos/{documento_id}", dependencies=protegido)
    async def eliminar_documento(documento_id: int) -> dict[str, Any]:
        return comandos.eliminar_documento(documento_id)

    @app.get("/api/documentos/{documento_id}/descarga", dependencies=protegido)
    async def descargar_documento(documento_id: int) -> dict[str, str]:
        datos, nombre = comandos.abrir_documento(documento_id)
        return {"nombre": nombre, "contenido_b64": base64.b64encode(datos).decode("ascii")}

    @app.post("/api/documentos/{documento_id}/exportar", dependencies=protegido)
    async def exportar_documento(documento_id: int, cuerpo: Destino) -> dict[str, str]:
        comandos.exportar_documento(documento_id, cuerpo.destino)
        return {"destino": cuerpo.destino}

    # ---------------------------------------------------------------- #
    # Personas
    # ---------------------------------------------------------------- #

    @app.get("/api/personas", dependencies=protegido)
    async def listar_personas(buscar: str = "") -> list[dict[str, Any]]:
        return comandos.listar_personas(buscar)

    @app.get("/api/personas/{persona_id}", dependencies=protegido)
    async def obtener_persona(persona_id: int) -> dict[str, Any]:
        return comandos.obtener_persona(persona_id)

    @app.post("/api/personas", status_code=201, dependencies=protegido)
    async def crear_persona(cuerpo: PersonaNueva) -> dict[str, Any]:
        return comandos.crear_persona(cuerpo.cedula, cuerpo.nombres, cuerpo.empresa)

    @app.patch("/api/personas/{persona_id}", dependencies=protegido)
    async def actualizar_persona(persona_id: int, cuerpo: PersonaPatch) -> dict[str, Any]:
        return comandos.actualizar_persona(persona_id, **cuerpo.model_dump(exclude_none=True))

    @app.delete("/api/personas/{persona_id}", dependencies=protegido)
    async def eliminar_persona(persona_id: int) -> dict[str, Any]:
        return comandos.eliminar_persona(persona_id)

    # ---------------------------------------------------------------- #
    # Auditoría
    # ---------------------------------------------------------------- #

    @app.get("/api/auditoria", dependencies=protegido)
    async def listar_auditoria(
        desde: str = "",
        hasta: str = "",
        accion: str = "",
        limite: int = 0,
    ) -> list[dict[str, Any]]:
        return comandos.listar_eventos(
            desde=desde, hasta=hasta, accion=accion,
            limite=limite or LIMITE_VISOR,
        )

    @app.get("/api/auditoria/conteo", dependencies=protegido)
    async def contar_auditoria() -> dict[str, int]:
        return {"total": comandos.contar_eventos()}

    @app.delete("/api/auditoria", dependencies=protegido)
    async def limpiar_auditoria() -> dict[str, int]:
        return {"eliminados": comandos.limpiar_historial()}

    @app.get("/api/auditoria/log", dependencies=protegido)
    async def log_sistema() -> dict[str, str]:
        contenido, origen = comandos.log_sistema()
        return {"contenido": contenido, "origen": origen}

    # ---------------------------------------------------------------- #
    # Reportes
    # ---------------------------------------------------------------- #

    @app.get("/api/reportes/estadisticas", dependencies=protegido)
    async def estadisticas() -> dict[str, Any]:
        return comandos.estadisticas_dashboard()

    @app.get("/api/reportes/inventario", dependencies=protegido)
    async def inventario() -> dict[str, Any]:
        filas, metricas = comandos.datos_inventario()
        return {"filas": filas, "metricas": metricas}

    @app.post("/api/reportes/exportar", dependencies=protegido)
    async def exportar_reporte(cuerpo: Exportacion) -> dict[str, str]:
        destino = comandos.exportar_inventario(cuerpo.destino, cuerpo.formato)
        return {"destino": destino}

    # ---------------------------------------------------------------- #
    # Asistente
    # ---------------------------------------------------------------- #

    @app.post("/api/chat", dependencies=protegido)
    async def iniciar_chat(cuerpo: InicioChat) -> dict[str, Any]:
        chat = comandos.iniciar_chat(cuerpo.contexto)
        return {"mensajes": list(chat.history)}

    @app.post("/api/chat/mensajes", dependencies=protegido)
    async def enviar_mensaje(cuerpo: MensajeChat) -> dict[str, str]:
        return {"respuesta": comandos.enviar_mensaje(cuerpo.mensaje)}

    @app.delete("/api/chat", dependencies=protegido)
    async def limpiar_chat() -> dict[str, bool]:
        comandos.limpiar_chat()
        return {"limpio": True}

    return app


# --------------------------------------------------------------------------- #
# Arranque
# --------------------------------------------------------------------------- #


def crear_servicio(
    db_path: str | None = None,
    token: str | None = None,
) -> tuple[FastAPI, ComandosDatenJager]:
    """Abre la base de datos y devuelve (aplicación, fachada de comandos)."""
    conn, cursor = conectar_db(db_path)
    comandos = ComandosDatenJager(
        AppState(conn=conn, cursor=cursor, db_lock=threading.Lock())
    )
    return crear_app(comandos, token=token), comandos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Servicio local de DatenJäger")
    parser.add_argument("--host", default="127.0.0.1", help="interfaz de escucha")
    parser.add_argument("--puerto", type=int, default=8756, help="puerto de escucha")
    parser.add_argument("--db", default=None, help="ruta alternativa de la base SQLite")
    parser.add_argument(
        "--token",
        default=None,
        help="token compartido; si se omite se genera uno y se imprime en la salida estándar",
    )
    argumentos = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    token = argumentos.token or secrets.token_urlsafe(32)
    app, _comandos = crear_servicio(argumentos.db, token)

    import uvicorn

    configuracion = uvicorn.Config(
        app, host=argumentos.host, port=argumentos.puerto, log_level="warning",
    )
    servidor = uvicorn.Server(configuracion)

    def anunciar_cuando_escuche() -> None:
        # uvicorn ejecuta el ciclo de vida antes de enlazar el socket, así que
        # el hook de la aplicación no sirve para anunciar: hay que esperar a
        # `servidor.started`, que se activa tras crear el socket. Si el puerto
        # está ocupado no se anuncia nada y el lanzador ve el error por stderr.
        while not servidor.started and not servidor.should_exit:
            time.sleep(0.05)
        if servidor.started:
            print(f"DATENJAGER_LISTO puerto={argumentos.puerto} token={token}", flush=True)

    threading.Thread(target=anunciar_cuando_escuche, daemon=True).start()
    servidor.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())