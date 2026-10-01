# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/server.py - servidor local que expone la capa de comandos por HTTP
# Trazabilidad Jira: SCRUM-62 (DatenJäger — API / Servicios).

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
* **La sesión se crea aquí.** ``POST /api/sesion`` valida credenciales y
  aplica el bloqueo por intentos; ``POST /api/sesion/2fa`` y
  ``/api/sesion/respaldo`` completan el segundo factor. La clave de sesión
  nunca viaja en la respuesta: permanece en el proceso Python.
* ``POST /api/sesion/heredar`` se conserva para que la aplicación de
  escritorio pueda entregar una sesión ya autenticada durante la transición.
* ``POST /api/registro`` da de alta una cuenta nueva (SCRUM-57): es el único
  acceso que no exige sesión previa.
* ``GET /api/salud`` informa también del estado de la base de datos, porque
  un servicio vivo con la base caída fallaba al iniciar sesión sin decirlo.
* **CORS por petición del lanzador.** En `npm run dev` el renderer se sirve
  desde el servidor de Vite y su origen deja de ser `file://`, así que las
  peticiones al servicio son de otro origen. La variable
  ``DATENJAGER_CORS_ORIGENES`` (orígenes separados por comas, nunca ``*``) las
  habilita; `electron/main.js` solo la define en modo desarrollo. Sin ella el
  navegador bloquea las peticiones y la interfaz dice «sin conexión» aunque el
  servicio esté levantado.

Arranque:

    python -m backend.server --puerto 8756 [--token TOKEN] [--db RUTA]

Si la base no se puede abrir, el proceso lo anuncia como
``DATENJAGER_ERROR base de datos: …`` y termina con código 2.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import logging
import os
import secrets
import sys
import threading
import time
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.commands import ComandosDatenJager
from backend.errors import (
    BackendError,
    BaseDeDatosError,
    ConflictoError,
    CredencialesInvalidasError,
    CuentaBloqueadaError,
    DatosInvalidosError,
    NoAutenticadoError,
    NoEncontradoError,
    SegundoFactorInvalidoError,
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
    (SegundoFactorInvalidoError, 401),
    (CredencialesInvalidasError, 401),
    (CuentaBloqueadaError, 423),
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


class Acceso(BaseModel):
    """Credenciales de acceso. El token de confianza es opcional."""

    nombre: str
    contrasena: str
    token_confianza: Optional[str] = None


class Registro(BaseModel):
    """Alta de una cuenta nueva (SCRUM-57)."""

    nombre: str
    contrasena: str


class ConexionModelos(BaseModel):
    """Conexión de modelos: proveedor, modelo, punto de conexión y clave.

    La clave es opcional; ``quitar_clave`` descarta la guardada sin necesidad
    de enviar una nueva.
    """

    proveedor: Optional[str] = None
    modelo: Optional[str] = None
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    quitar_clave: bool = False


class SegundoFactorNuevo(BaseModel):
    """Secreto TOTP propuesto y código con el que el usuario lo confirma."""

    secreto: str
    codigo: str


class CambioDeContrasena(BaseModel):
    """Cambio de contraseña: exige la actual y un código del autenticador."""

    contrasena_actual: str
    contrasena_nueva: str
    codigo: str


class CodigoDeSeguridad(BaseModel):
    """Código del segundo factor: TOTP o código de respaldo."""

    codigo: str


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


class EmpresaNueva(BaseModel):
    """Alta de empresa en el catálogo."""

    nombre: str


class EmpresaPatch(BaseModel):
    nombre: str


class FusionDeEmpresas(BaseModel):
    """Fusión de dos fichas: el personal del origen pasa al destino."""

    destino_id: int


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

    # CORS solo si el lanzador lo pide, y solo para orígenes concretos de bucle
    # local (nunca `*`).
    #
    # Motivo: en `npm run dev` el renderer se sirve desde el servidor de Vite
    # (`http://127.0.0.1:5273`), así que su origen deja de ser `file://` y las
    # peticiones al servicio pasan a ser de otro origen. Sin esta cabecera el
    # navegador las bloquea y la interfaz dice «sin conexión» aunque el servicio
    # esté levantado. En producción el renderer carga desde `file://` y no hace
    # falta: `electron/main.js` solo define la variable en modo desarrollo.
    origenes = os.environ.get("DATENJAGER_CORS_ORIGENES", "").strip()
    if origenes:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[origen.strip() for origen in origenes.split(",") if origen.strip()],
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "X-DatenJager-Token"],
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
        """Disponibilidad del servicio. Sin datos sensibles: sin token.

        Incluye el estado de la base de datos porque «el servicio responde» y
        «la base responde» no son lo mismo: sin esta lectura, una base caída
        se veía como un servicio sano y el fallo aparecía al iniciar sesión.
        """
        return {
            "estado": "ok",
            "version": VERSION_API,
            "autenticado": comandos.sesion_actual()["autenticado"],
            "base_datos": comandos.estado_base_datos(),
        }

    @app.get("/api/sesion", dependencies=protegido)
    async def sesion_actual() -> dict[str, Any]:
        return comandos.sesion_actual()

    @app.post("/api/sesion", dependencies=protegido)
    async def iniciar_sesion(cuerpo: Acceso) -> dict[str, Any]:
        """Valida las credenciales.

        Responde con ``estado: "segundo_factor"`` cuando la cuenta usa 2FA; en
        ese caso hay que llamar a ``/api/sesion/2fa`` o ``/api/sesion/respaldo``.
        La clave de sesión nunca viaja en la respuesta: se queda en el proceso.
        """
        return comandos.iniciar_sesion_credenciales(
            cuerpo.nombre, cuerpo.contrasena, cuerpo.token_confianza)

    @app.post("/api/registro", status_code=201, dependencies=protegido)
    async def registrar_usuario(cuerpo: Registro) -> dict[str, Any]:
        """Da de alta una cuenta y abre su sesión (SCRUM-57).

        Es el único acceso que no exige sesión previa; con ella se configura
        el segundo factor. La clave de sesión, como en el acceso, se queda en
        el proceso de Python.
        """
        return comandos.registrar_usuario(cuerpo.nombre, cuerpo.contrasena)

    @app.post("/api/sesion/2fa", dependencies=protegido)
    async def verificar_segundo_factor(cuerpo: CodigoDeSeguridad) -> dict[str, Any]:
        """Completa el acceso con el código TOTP."""
        return comandos.verificar_segundo_factor(cuerpo.codigo)

    @app.post("/api/sesion/respaldo", dependencies=protegido)
    async def usar_codigo_de_respaldo(cuerpo: CodigoDeSeguridad) -> dict[str, Any]:
        """Completa el acceso con un código de respaldo de un solo uso."""
        return comandos.usar_codigo_de_respaldo(cuerpo.codigo)

    @app.get("/api/cuenta", dependencies=protegido)
    async def estado_de_cuenta() -> dict[str, Any]:
        """Estado de seguridad de la cuenta en sesión."""
        return comandos.estado_de_cuenta()

    @app.post("/api/cuenta/2fa/preparar", dependencies=protegido)
    async def preparar_segundo_factor() -> dict[str, Any]:
        """Genera un secreto TOTP y el PNG del QR, sin activarlo todavía."""
        return comandos.preparar_segundo_factor()

    @app.post("/api/cuenta/2fa/activar", dependencies=protegido)
    async def activar_segundo_factor(cuerpo: SegundoFactorNuevo) -> dict[str, Any]:
        """Activa el 2FA y devuelve los códigos de respaldo (una sola vez)."""
        return comandos.activar_segundo_factor(cuerpo.secreto, cuerpo.codigo)

    @app.post("/api/cuenta/2fa/desactivar", dependencies=protegido)
    async def desactivar_segundo_factor(cuerpo: CodigoDeSeguridad) -> dict[str, Any]:
        """Desactiva el 2FA y descarta la confianza de este dispositivo."""
        return comandos.desactivar_segundo_factor(cuerpo.codigo)

    @app.post("/api/cuenta/2fa/codigos", dependencies=protegido)
    async def regenerar_codigos_de_respaldo(cuerpo: CodigoDeSeguridad) -> dict[str, Any]:
        """Emite códigos de respaldo nuevos, invalidando los anteriores."""
        return comandos.regenerar_codigos_de_respaldo(cuerpo.codigo)

    @app.post("/api/cuenta/contrasena", dependencies=protegido)
    async def cambiar_contrasena(cuerpo: CambioDeContrasena) -> dict[str, Any]:
        """Cambia la contraseña y re-cifra los secretos con la clave nueva."""
        return comandos.cambiar_contrasena(
            cuerpo.contrasena_actual, cuerpo.contrasena_nueva, cuerpo.codigo)

    @app.delete("/api/cuenta/confianza", dependencies=protegido)
    async def revocar_confianza() -> dict[str, Any]:
        """Olvida este dispositivo: el próximo acceso pedirá el segundo factor."""
        return comandos.revocar_confianza()

    # ---------------------------------------------------------------- #
    # Conexión de modelos (SCRUM-64)
    # ---------------------------------------------------------------- #

    @app.get("/api/modelos", dependencies=protegido)
    async def estado_de_modelos() -> dict[str, Any]:
        """Conexión de modelos vigente. La clave nunca viaja en la respuesta."""
        return comandos.estado_de_modelos()

    @app.post("/api/modelos", dependencies=protegido)
    async def guardar_conexion_de_modelos(cuerpo: ConexionModelos) -> dict[str, Any]:
        """Guarda la conexión de modelos; el chatbot la adopta al reiniciar el chat."""
        return comandos.guardar_conexion_de_modelos(**cuerpo.model_dump())

    @app.post("/api/modelos/probar", dependencies=protegido)
    async def probar_conexion_de_modelos() -> dict[str, Any]:
        """Prueba real de la credencial contra el proveedor configurado."""
        return comandos.probar_conexion_de_modelos()

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
    # Empresas
    # ---------------------------------------------------------------- #

    @app.get("/api/empresas", dependencies=protegido)
    async def listar_empresas(buscar: str = "") -> list[dict[str, Any]]:
        return comandos.listar_empresas(buscar)

    @app.get("/api/empresas/conteo", dependencies=protegido)
    async def contar_empresas() -> dict[str, int]:
        return {"total": comandos.contar_empresas()}

    @app.get("/api/empresas/{empresa_id}", dependencies=protegido)
    async def obtener_empresa(empresa_id: int) -> dict[str, Any]:
        return comandos.obtener_empresa(empresa_id)

    @app.post("/api/empresas", status_code=201, dependencies=protegido)
    async def crear_empresa(cuerpo: EmpresaNueva) -> dict[str, Any]:
        return comandos.crear_empresa(cuerpo.nombre)

    @app.patch("/api/empresas/{empresa_id}", dependencies=protegido)
    async def renombrar_empresa(empresa_id: int, cuerpo: EmpresaPatch) -> dict[str, Any]:
        return comandos.renombrar_empresa(empresa_id, cuerpo.nombre)

    @app.post("/api/empresas/{origen_id}/fusionar", dependencies=protegido)
    async def fusionar_empresas(origen_id: int, cuerpo: FusionDeEmpresas) -> dict[str, Any]:
        return comandos.fusionar_empresas(origen_id, cuerpo.destino_id)

    @app.delete("/api/empresas/{empresa_id}", dependencies=protegido)
    async def eliminar_empresa(empresa_id: int) -> dict[str, Any]:
        return comandos.eliminar_empresa(empresa_id)

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

    @app.get("/api/reportes/por-empresa", dependencies=protegido)
    async def documentos_por_empresa() -> list[dict[str, Any]]:
        """Distribución de documentos por empresa, para el gráfico de barras."""
        return [
            {"empresa": empresa, "total": total}
            for empresa, total in comandos.documentos_por_empresa()
        ]

    @app.get("/api/reportes/por-dia", dependencies=protegido)
    async def documentos_por_dia() -> list[dict[str, Any]]:
        """Documentos subidos por día, para la serie temporal."""
        return [
            {"dia": dia, "total": total}
            for dia, total in comandos.documentos_por_dia()
        ]

    @app.get("/api/reportes/tendencia", dependencies=protegido)
    async def tendencia_documentos() -> dict[str, Any]:
        """Serie temporal con regresión, predicción, R² y la paleta de gráficos.

        El cálculo vive en Python (``backend/services/reportes.py``) y el
        frontend solo dibuja; la paleta viaja como **roles semánticos** para que
        el renderer la resuelva contra sus tokens (SCRUM-57).
        """
        return comandos.tendencia_documentos()

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
    """Abre la base de datos y devuelve (aplicación, fachada de comandos).

    Raises:
        BaseDeDatosError: la base no se pudo abrir o preparar. Se distingue del
            resto de fallos de arranque porque es el único que deja el servicio
            sin ninguna operación posible (ver `main`).
    """
    try:
        conn, cursor = conectar_db(db_path)
    except Exception as error:
        raise BaseDeDatosError(str(error)) from error

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

    try:
        app, _comandos = crear_servicio(argumentos.db, token)
    except BaseDeDatosError as error:
        # Fallo de arranque, no de operación: sin base no hay nada que servir.
        # Se anuncia con una línea propia para que el lanzador (Electron) lo
        # distinga de un error de importación y lo muestre tal cual, en lugar
        # de dejar la interfaz en «servicio no disponible» sin motivo.
        print(f"DATENJAGER_ERROR base de datos: {error.mensaje}", flush=True)
        LOG.error("No se pudo abrir la base de datos: %s", error.mensaje)
        return 2

    import uvicorn

    configuracion = uvicorn.Config(
        app, host=argumentos.host, port=argumentos.puerto, log_level="warning",
    )
    servidor = uvicorn.Server(configuracion)

    def puerto_efectivo() -> int:
        """Puerto realmente enlazado.

        Cuando se pide `--puerto 0` el sistema elige uno libre: el número que
        se pasó por línea de comandos no sirve para anunciar nada.
        """
        for servidor_uvicorn in getattr(servidor, "servers", ()) or ():
            for enchufe in getattr(servidor_uvicorn, "sockets", None) or ():
                try:
                    return enchufe.getsockname()[1]
                except Exception:
                    continue
        return argumentos.puerto

    def anunciar_cuando_escuche() -> None:
        # uvicorn ejecuta el ciclo de vida antes de enlazar el socket, así que
        # el hook de la aplicación no sirve para anunciar: hay que esperar a
        # `servidor.started`, que se activa tras crear el socket. Si el puerto
        # está ocupado no se anuncia nada y el lanzador ve el error por stderr.
        while not servidor.started and not servidor.should_exit:
            time.sleep(0.05)
        if servidor.started:
            print(
                f"DATENJAGER_LISTO puerto={puerto_efectivo()} token={token}",
                flush=True,
            )

    threading.Thread(target=anunciar_cuando_escuche, daemon=True).start()
    servidor.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())