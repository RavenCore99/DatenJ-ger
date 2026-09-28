# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/commands.py - punto de entrada único de operaciones

"""Capa de comandos: punto de entrada único del backend.

Agrupa las operaciones de todos los paneles (documentos, personas,
auditoría, reportes, chatbot y sesión) detrás de una sola clase, de modo
que cualquier cliente —la interfaz CustomTkinter hoy, el servidor local
FastAPI mañana— invoque las mismas funciones sin conocer los servicios por
dentro.

Contrato:
    - Todos los comandos verifican que exista sesión activa y levantan
      ``NoAutenticadoError`` si no la hay (salvo los de sesión).
    - Los comandos de escritura y lectura usan ``AppState.db_lock`` para
      serializar el acceso a la conexión SQLite compartida.
    - Los comandos retornan datos simples (``dict``/``list``/``bytes``),
      nunca widgets.

Alcance pendiente: la verificación de credenciales, el flujo 2FA y el
cambio de contraseña siguen viviendo en ``main.py`` porque forman parte del
flujo de autenticación y requieren aprobación explícita antes de moverse
(ver ``operaciones_pendientes``).
"""

from __future__ import annotations

from typing import Any, Optional

from backend.errors import NoAutenticadoError
from backend.services import auditoria as _auditoria
from backend.services import documentos as _documentos
from backend.services import personas as _personas
from backend.services import reportes as _reportes
from chatbot import ChatbotService, crear_servicio

#: Operaciones que todavía viven en la interfaz y su motivo.
OPERACIONES_PENDIENTES = {
    "registro": "Alta de usuario con derivación de claves (flujo de autenticación)",
    "login": "Verificación de credenciales, bloqueo por intentos y token de confianza",
    "login_2fa": "Verificación TOTP y códigos de respaldo",
    "setup_2fa": "Generación del secreto TOTP y códigos de respaldo",
    "cambio_contrasena": "Re-cifrado de secretos con la nueva clave de sesión",
    "confianza_dispositivo": "Emisión y revocación del token de confianza",
}


class ComandosDatenJager:
    """Fachada de operaciones del backend sobre un ``AppState``.

    Args:
        state: instancia de ``backend.state.AppState`` ya construida por la
            aplicación (conexión, cursor, lock y configuración).
    """

    def __init__(self, state):
        self.state = state
        self._chat: Optional[ChatbotService] = None

    # ------------------------------------------------------------------ #
    # Internos
    # ------------------------------------------------------------------ #

    def _exigir_sesion(self) -> Any:
        """Valida que haya sesión activa y devuelve el id del usuario.

        Raises:
            NoAutenticadoError: no hay usuario autenticado.
        """
        if not self.state.is_authenticated:
            raise NoAutenticadoError("No hay sesión activa")
        return self.state.usuario_actual

    @property
    def _usuario_nombre(self) -> str:
        return self.state.usuario_nombre or ""

    def _ejecutar(self, operacion, /, **kwargs):
        """Invoca un servicio bajo el lock de base de datos.

        Todos los servicios del backend comparten la firma
        ``(conn, cursor, ...)``, de modo que esta fachada no necesita saber
        si la operación escribe o solo lee.
        """
        with self.state.db_lock:
            return operacion(self.state.conn, self.state.cursor, **kwargs)

    # ------------------------------------------------------------------ #
    # Sesión
    # ------------------------------------------------------------------ #

    def iniciar_sesion(self, usuario_id: int, nombre: str, session_key: Any = None) -> dict:
        """Marca la sesión como activa (la verificación previa la hace el cliente)."""
        self.state.iniciar_sesion(usuario_id, nombre, session_key)
        return self.sesion_actual()

    def cerrar_sesion(self) -> None:
        """Descarta la sesión y la conversación activa."""
        self._chat = None
        self.state.cerrar_sesion()

    def sesion_actual(self) -> dict:
        """Estado de la sesión en curso."""
        return {
            "autenticado": self.state.is_authenticated,
            "usuario_id": self.state.usuario_actual,
            "usuario_nombre": self.state.usuario_nombre,
            "tema": self.state.tema,
            "minutos_inactividad": self.state.minutos_inactividad(),
        }

    # ------------------------------------------------------------------ #
    # Documentos
    # ------------------------------------------------------------------ #

    def listar_documentos(self, termino: str = "") -> list[dict]:
        """Lista los documentos del usuario, con filtro opcional."""
        usuario_id = self._exigir_sesion()
        return self._ejecutar(
            _documentos.listar_documentos, usuario_id=usuario_id, termino=termino
        )

    def obtener_documento(self, documento_id: int) -> dict:
        """Devuelve los metadatos de un documento."""
        usuario_id = self._exigir_sesion()
        return self._ejecutar(
            _documentos.obtener_documento, usuario_id=usuario_id, documento_id=documento_id
        )

    def contar_documentos(self) -> int:
        """Cuenta los documentos del usuario."""
        usuario_id = self._exigir_sesion()
        return self._ejecutar(_documentos.contar_documentos, usuario_id=usuario_id)

    def agregar_documento(
        self,
        ruta: str,
        descripcion: str = "",
        cedula: Optional[str] = None,
        nombres: Optional[str] = None,
        empresa: Optional[str] = None,
    ) -> dict:
        """Cifra y registra un PDF leído desde disco."""
        usuario_id = self._exigir_sesion()
        return self._ejecutar(
            _documentos.crear_documento_desde_archivo,
            usuario_id=usuario_id,
            usuario_nombre=self._usuario_nombre,
            ruta=ruta,
            descripcion=descripcion,
            cedula=cedula,
            nombres=nombres,
            empresa=empresa,
        )

    def agregar_documento_bytes(
        self,
        nombre: str,
        datos: bytes,
        descripcion: str = "",
        cedula: Optional[str] = None,
        nombres: Optional[str] = None,
        empresa: Optional[str] = None,
    ) -> dict:
        """Cifra y registra un PDF recibido como bytes (carga desde el cliente)."""
        usuario_id = self._exigir_sesion()
        return self._ejecutar(
            _documentos.crear_documento,
            usuario_id=usuario_id,
            usuario_nombre=self._usuario_nombre,
            nombre=nombre,
            datos=datos,
            descripcion=descripcion,
            cedula=cedula,
            nombres=nombres,
            empresa=empresa,
        )

    def abrir_documento(self, documento_id: int) -> tuple[bytes, str]:
        """Descifra un documento y devuelve ``(bytes, nombre)``."""
        usuario_id = self._exigir_sesion()
        return self._ejecutar(
            _documentos.leer_documento,
            usuario_id=usuario_id,
            documento_id=documento_id,
            usuario_nombre=self._usuario_nombre,
        )

    def actualizar_documento(self, documento_id: int, **campos) -> dict:
        """Actualiza los metadatos indicados del documento."""
        usuario_id = self._exigir_sesion()
        return self._ejecutar(
            _documentos.actualizar_documento,
            usuario_id=usuario_id,
            documento_id=documento_id,
            **campos,
        )

    def eliminar_documento(self, documento_id: int) -> dict:
        """Elimina un documento del usuario."""
        usuario_id = self._exigir_sesion()
        return self._ejecutar(
            _documentos.eliminar_documento, usuario_id=usuario_id, documento_id=documento_id
        )

    def exportar_documento(self, documento_id: int, destino: str) -> str:
        """Descifra un documento y lo escribe en ``destino``."""
        usuario_id = self._exigir_sesion()
        return self._ejecutar(
            _documentos.exportar_documento,
            usuario_id=usuario_id,
            documento_id=documento_id,
            usuario_nombre=self._usuario_nombre,
            destino=destino,
        )

    # ------------------------------------------------------------------ #
    # Personas
    # ------------------------------------------------------------------ #

    def listar_personas(self, filtro: str = "") -> list[dict]:
        """Lista las personas registradas con su número de documentos."""
        self._exigir_sesion()
        return self._ejecutar(_personas.listar_personas, filtro=filtro)

    def obtener_persona(self, persona_id: int) -> dict:
        """Devuelve una persona por id."""
        self._exigir_sesion()
        return self._ejecutar(_personas.obtener_persona, persona_id=persona_id)

    def crear_persona(
        self,
        cedula: str,
        nombres: str,
        empresa: Optional[str] = None,
    ) -> dict:
        """Registra una persona nueva."""
        usuario_id = self._exigir_sesion()
        return self._ejecutar(
            _personas.crear_persona,
            cedula=cedula,
            nombres=nombres,
            empresa=empresa,
            usuario_id=usuario_id,
        )

    def actualizar_persona(
        self,
        persona_id: int,
        nombres: str,
        empresa: Optional[str] = None,
    ) -> dict:
        """Actualiza nombre y empresa de una persona."""
        usuario_id = self._exigir_sesion()
        return self._ejecutar(
            _personas.actualizar_persona,
            persona_id=persona_id,
            nombres=nombres,
            empresa=empresa,
            usuario_id=usuario_id,
        )

    def eliminar_persona(self, persona_id: int) -> dict:
        """Elimina una persona; sus documentos quedan sin titular."""
        usuario_id = self._exigir_sesion()
        return self._ejecutar(
            _personas.eliminar_persona, persona_id=persona_id, usuario_id=usuario_id
        )

    # ------------------------------------------------------------------ #
    # Auditoría
    # ------------------------------------------------------------------ #

    def registrar_evento(
        self,
        accion: str,
        documento_id: Optional[int] = None,
        usuario_id: Optional[int] = None,
    ) -> bool:
        """Registra un evento de auditoría."""
        return self._ejecutar(
            _auditoria.registrar_evento,
            accion=accion,
            usuario_id=usuario_id if usuario_id is not None else self.state.usuario_actual,
            documento_id=documento_id,
        )

    def listar_eventos(
        self,
        desde: str = "",
        hasta: str = "",
        accion: str = "",
        limite: int = _auditoria.LIMITE_VISOR,
    ) -> list[dict]:
        """Consulta el historial de auditoría con filtros."""
        self._exigir_sesion()
        return self._ejecutar(
            _auditoria.listar_eventos, desde=desde, hasta=hasta, accion=accion, limite=limite
        )

    def contar_eventos(self) -> int:
        """Cuenta los eventos de auditoría."""
        self._exigir_sesion()
        return self._ejecutar(_auditoria.contar_eventos)

    def limpiar_historial(self) -> int:
        """Vacía el historial de auditoría dejando constancia del vaciado."""
        self._exigir_sesion()
        return self._ejecutar(_auditoria.limpiar_historial, usuario_id=self.state.usuario_actual)

    def log_sistema(self, directorio: str = ".") -> tuple[str, str]:
        """Compone el log del sistema para el visor."""
        self._exigir_sesion()
        return self._ejecutar(_auditoria.construir_log_sistema, directorio=directorio)

    # ------------------------------------------------------------------ #
    # Reportes
    # ------------------------------------------------------------------ #

    def estadisticas_dashboard(self) -> dict:
        """Tarjetas KPI del dashboard."""
        usuario_id = self._exigir_sesion()
        return self._ejecutar(_reportes.estadisticas, usuario_id=usuario_id)

    def documentos_por_empresa(self) -> list[tuple]:
        """Distribución de documentos por empresa."""
        usuario_id = self._exigir_sesion()
        return self._ejecutar(_reportes.documentos_por_empresa, usuario_id=usuario_id)

    def documentos_por_dia(self) -> list[tuple]:
        """Documentos subidos por día."""
        usuario_id = self._exigir_sesion()
        return self._ejecutar(_reportes.documentos_por_dia, usuario_id=usuario_id)

    def datos_inventario(self) -> tuple[list, dict]:
        """Filas y estadísticas del reporte de inventario."""
        usuario_id = self._exigir_sesion()
        return self._ejecutar(_reportes.datos_inventario, usuario_id=usuario_id)

    def exportar_inventario(self, destino: str, formato: str = "pdf") -> str:
        """Genera el reporte de inventario en PDF o CSV."""
        usuario_id = self._exigir_sesion()
        return self._ejecutar(
            _reportes.exportar_inventario,
            usuario_id=usuario_id,
            usuario_nombre=self._usuario_nombre,
            destino=destino,
            formato=formato,
        )

    # ------------------------------------------------------------------ #
    # Chatbot
    # ------------------------------------------------------------------ #

    def iniciar_chat(self, contexto: str = "") -> ChatbotService:
        """Inicia (o reinicia) la conversación del usuario autenticado."""
        self._exigir_sesion()
        self._chat = crear_servicio(self._usuario_nombre, contexto)
        return self._chat

    def enviar_mensaje(self, texto: str) -> str:
        """Envía un mensaje al asistente y devuelve su respuesta.

        Hoy la llamada es bloqueante (el streaming llega en la Fase 4), así
        que el cliente debe invocarla fuera del hilo de interfaz.
        """
        self._exigir_sesion()
        chat = self._chat
        if chat is None:
            chat = self.iniciar_chat()
        return chat.enviar_mensaje(texto)

    def limpiar_chat(self) -> None:
        """Reinicia el historial de la conversación activa."""
        if self._chat is not None:
            self._chat.clear_history()

    # ------------------------------------------------------------------ #
    # Catálogo
    # ------------------------------------------------------------------ #

    @staticmethod
    def operaciones_pendientes() -> dict:
        """Operaciones que aún no forman parte de esta capa y por qué."""
        return dict(OPERACIONES_PENDIENTES)