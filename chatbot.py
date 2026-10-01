# Copyright (c) 2024 DatenJäger. All rights reserved
# chatbot.py - servicio del asistente IA (sin dependencias de UI)
# Trazabilidad Jira: SCRUM-34, SCRUM-35, SCRUM-36, SCRUM-61.

"""Servicio del asistente IA.

``ChatbotService`` encapsula la conversación con el modelo remoto: armado del
historial, llamada a la API, **entrega progresiva de la respuesta** (RF-16,
`SCRUM-34`), **tiempos límite y reintentos** (`SCRUM-35`), y el **anclaje al
proyecto** (`SCRUM-61`): el asistente solo responde sobre DatenJäger y con los
datos reales que el backend le entrega, nunca con información de otro tipo.

Este módulo no importa Tkinter: la UI (``chatbot_ui.py``) solo monta los
widgets y pide los textos a este servicio.

Decisiones que conviene tener presentes al leerlo:

* **La conversación se registra una sola vez.** El turno del usuario entra en el
  historial al empezar el envío; el del modelo, cuando el flujo termina. Si el
  flujo se corta a media respuesta, lo que el usuario **vio** entra igualmente
  al historial: el turno siguiente debe saber qué se respondió (`SCRUM-36`).
* **Un reintento no repite texto.** Solo se reintenta mientras no se haya
  entregado ni un fragmento. Una vez que la respuesta empieza a fluir, un fallo
  se comunica al usuario en vez de reiniciar la generación y duplicar lo ya
  leído.
* **Nada de respuestas inventadas.** Si el modelo no está disponible, se dice el
  motivo real y accionable. No hay respaldo que finja contestar.
"""

import itertools
import json
import os
import socket
import time
from typing import Any
from urllib import error, request

import config  # importar carga el archivo .env (GEMINI_API_KEY)
from transhumano import (
    DECLARACION_PRINCIPAL,
    PILARES,
    RESPUESTAS_REFLEXIVAS,
    obtener_respuesta_reflexiva,
    obtener_frase_aleatoria
)
from backend.errors import BackendError


#: Segundos que se espera a que el modelo empiece (o siga) respondiendo.
TIEMPO_LIMITE_POR_DEFECTO = 45.0

#: Intentos por modelo antes de pasar al siguiente candidato. Solo se agotan
#: mientras no se haya entregado ningún fragmento.
REINTENTOS_POR_DEFECTO = 3

#: Espera entre reintentos, en segundos; crece con cada intento (1 s, 2 s…).
ESPERA_REINTENTO = 1.0

#: Modelos que se prueban, en orden, si el elegido no responde.
MODELOS_POR_DEFECTO = (
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-flash-latest",
)

#: Base del proveedor. El panel de conexión puede guardar otro punto de
#: conexión como referencia, pero el asistente usa el del proveedor.
ENDPOINT_GEMINI = "https://generativelanguage.googleapis.com/v1beta"

SYSTEM_PROMPT = (
    "Eres el asistente de DatenJäger, un sistema de gestión documental cifrado "
    "con AES-256-GCM y autenticación de dos factores.\n\n"
    "DECLARACIÓN FUNDAMENTAL (Universidad de Cundinamarca - Innovación Tecnológica):\n"
    f"'{DECLARACION_PRINCIPAL}'\n\n"
    "Esta declaración guía tu interacción. Los pilares son:\n"
    "- LIBERTAD: Autonomía informativa protegida por cifrado fuerte\n"
    "- AUTONOMÍA: Control total del usuario sobre sus datos y sesión\n"
    "- RESPONSABILIDAD: Auditoría completa de cada acción\n"
    "- DIÁLOGO: Conversación reflexiva que genere crecimiento\n"
    "- CONSTRUCCIÓN: Transformación positiva y continua\n\n"
    "Tu rol es ayudar al usuario autenticado a:\n"
    "- Encontrar y organizar sus documentos PDF\n"
    "- Entender las funciones del sistema (auditoría, personas, reportes, cifrado)\n"
    "- Incluir reflexiones sobre autonomía, libertad y responsabilidad cuando sea pertinente\n\n"
    "Reglas:\n"
    "- Responde siempre en el idioma del usuario (por defecto español)\n"
    "- Sé breve y útil; evita respuestas largas a menos que se pida\n"
    "- No reveles información sensible de otros usuarios\n"
    "- No inventes datos sobre documentos que no conoces\n"
    "- Cuando hables de seguridad, cifrado, auditoría o autonomía, conecta con la "
    "filosofía transhumana basada en la Universidad de Cundinamarca de colombia en "
    "cuanto a innovacion de persona transhumana\n"
    "- Cultiva el bienestar digital y la responsabilidad del usuario"
)


class ConfiguracionChatbotError(BackendError, ValueError):
    """Falta la configuración necesaria para contactar el modelo.

    Hereda de ``BackendError`` para que la capa backend la reconozca y de
    ``ValueError`` para no romper a los llamadores que ya la capturaban.
    """


class ChatbotError(BackendError):
    """Error de conversación con el modelo remoto."""


class ErrorRedChatbot(ChatbotError):
    """Fallo de red, de tiempo o del proveedor al generar la respuesta.

    Lleva el ``motivo`` ya legible para el usuario y una marca ``reintentable``
    que decide si tiene sentido volver a intentarlo.
    """

    def __init__(self, mensaje: str, *, motivo: str = "", reintentable: bool = False):
        super().__init__(mensaje)
        self.motivo = motivo or mensaje
        self.reintentable = reintentable


def declaracion_transhumana() -> str:
    """Declaración principal de la Persona Transhumana (texto corto)."""
    return DECLARACION_PRINCIPAL


def mensaje_bienvenida(usuario_nombre: str) -> str:
    """Texto de apertura del asistente para una sesión recién iniciada."""
    return (
        f"Hola {usuario_nombre}, soy tu asistente de DatenJäger.\n\n"
        f"🌟 Bienvenido a tu espacio de autonomía digital.\n\n"
        f"Aquí aplicamos la **Declaración de Persona Transhumana** "
        f"de la Universidad de Cundinamarca:\n\n"
        f'*"{DECLARACION_PRINCIPAL}"*\n\n'
        f"Tu información está cifrada (AES-256), tu sesión protegida (2FA), "
        f"y tus acciones auditadas.\n\n"
        f"**Eres libre. Eres responsable. Eres el dueño.**\n\n"
        f"¿En qué puedo ayudarte hoy?"
    )


#: Resumen corto de cada pilar tal como se muestra en el panel de reflexión.
#: Si un pilar no aparece aquí se usa su descripción.
_RESUMEN_PILARES = {
    "LIBERTAD": "Autonomía informativa protegida por cifrado",
    "AUTONOMÍA": "Control total sobre tus datos",
    "RESPONSABILIDAD": "Auditoría completa de acciones",
    "DIÁLOGO": "Conversación reflexiva y constructiva",
    "CONSTRUCCIÓN": "Transformación positiva continua",
}


def contenido_reflexion() -> dict:
    """Contenido del panel de reflexión sobre la Persona Transhumana.

    Returns:
        Dict con ``declaracion``, ``pilares`` (lista de dicts con nombre,
        descripción, resumen corto, aspecto digital y reflexión) y ``frase``
        aleatoria.
    """
    return {
        "declaracion": DECLARACION_PRINCIPAL,
        "pilares": [
            {
                "nombre": nombre,
                "descripcion": datos.get("descripcion", ""),
                "resumen": _RESUMEN_PILARES.get(nombre, datos.get("descripcion", "")),
                "aspecto_digital": datos.get("aspecto_digital", ""),
                "reflexion": datos.get("reflexion", ""),
            }
            for nombre, datos in PILARES.items()
        ],
        "frase": obtener_frase_aleatoria("reflexion"),
    }


class ChatbotService:
    """Servicio de IA. Una instancia por sesión de usuario."""

    def __init__(
        self,
        usuario_nombre: str = "",
        api_key: str | None = None,
        modelo: str | None = None,
        *,
        tiempo_limite: float = TIEMPO_LIMITE_POR_DEFECTO,
        reintentos: int = REINTENTOS_POR_DEFECTO,
        contexto: str = "",
    ):
        api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        if not api_key:
            raise ConfiguracionChatbotError(
                "GEMINI_API_KEY no encontrada. Carga la credencial en el panel de conexión de modelos"
            )

        self.api_key = api_key
        self.model_candidates: list[str] = list(MODELOS_POR_DEFECTO)
        if modelo and modelo.strip() and modelo.strip() not in self.model_candidates:
            # El modelo elegido en el panel de conexión se prueba primero; la
            # lista de candidatos se conserva como respaldo si falla.
            self.model_candidates.insert(0, modelo.strip())

        self.tiempo_limite = float(tiempo_limite)
        self.reintentos = max(1, int(reintentos))
        self.usuario_nombre = usuario_nombre
        self.model_name: str | None = None
        #: Contexto del proyecto que se reinyecta en cada turno (`SCRUM-61`).
        self.contexto = (contexto or "").strip()
        self.history: list[dict[str, Any]] = []

    # ------------------------------------------------------------------ #
    # Peticiones al proveedor
    # ------------------------------------------------------------------ #

    def _system_prompt(self) -> str:
        """Instrucciones del sistema, con el contexto real del proyecto.

        El contexto viaja **en cada turno**, no una sola vez al abrir la
        conversación: las cifras del archivo cambian mientras se conversa y el
        asistente debe responder con las de ahora.
        """
        if not self.contexto:
            return SYSTEM_PROMPT
        return f"{SYSTEM_PROMPT}\n\n---\n\n{self.contexto}"

    def _payload(self, contents: list[dict]) -> bytes:
        return json.dumps(
            {
                "contents": contents,
                "systemInstruction": {"parts": [{"text": self._system_prompt()}]},
            },
            ensure_ascii=False,
        ).encode("utf-8")

    def _peticion(self, model_name: str, contents: list[dict], *, flujo: bool) -> request.Request:
        sufijo = ":streamGenerateContent?alt=sse" if flujo else ":generateContent"
        url = f"{ENDPOINT_GEMINI}/models/{model_name}{sufijo}"
        return request.Request(
            url,
            data=self._payload(contents),
            method="POST",
            headers={"Content-Type": "application/json", "X-goog-api-key": self.api_key},
        )

    def _traducir_fallo(self, exc: Exception) -> ErrorRedChatbot:
        """Convierte un fallo del proveedor en un error legible y tipado."""
        if isinstance(exc, error.HTTPError):
            codigo = exc.code
            try:
                detalle = json.loads(exc.read() or b"{}").get("error", {}).get("message", "")
            except Exception:
                detalle = ""

            if codigo == 403:
                return ErrorRedChatbot(
                    "El proveedor rechazó la credencial (403). Revisa en el panel de conexión "
                    "que la API key pertenezca al proyecto correcto y tenga la API habilitada.",
                    motivo=detalle or "403 PERMISSION_DENIED",
                )
            if codigo == 401:
                return ErrorRedChatbot(
                    "El proveedor rechazó la autenticación (401). La API key no es válida o "
                    "fue revocada.",
                    motivo=detalle or "401 UNAUTHORIZED",
                )
            if codigo == 429:
                return ErrorRedChatbot(
                    "El proveedor está limitando las peticiones (429). Espera unos segundos y "
                    "vuelve a intentarlo.",
                    motivo=detalle or "429 RATE_LIMIT",
                    reintentable=True,
                )
            if codigo in (400, 404):
                return ErrorRedChatbot(
                    f"El proveedor rechazó la petición ({codigo}). Revisa el nombre del modelo "
                    "en el panel de conexión.",
                    motivo=detalle or f"{codigo}",
                )
            return ErrorRedChatbot(
                f"El proveedor respondió con un error ({codigo}).",
                motivo=detalle or str(exc),
                reintentable=codigo >= 500,
            )

        if isinstance(exc, error.URLError):
            razon = exc.reason
            if isinstance(razon, socket.gaierror):
                return ErrorRedChatbot(
                    "No se pudo resolver el host del proveedor. Revisa la conexión a internet "
                    "y el DNS del sistema.",
                    motivo=f"DNS: {razon}",
                    reintentable=True,
                )
            if isinstance(razon, (TimeoutError, socket.timeout)):
                return ErrorRedChatbot(
                    f"El proveedor no respondió en {self.tiempo_limite:.0f} s. Puede ser la "
                    "conexión; vuelve a intentarlo.",
                    motivo=f"timeout tras {self.tiempo_limite:.0f} s",
                    reintentable=True,
                )
            return ErrorRedChatbot(
                "No se pudo contactar el proveedor del modelo.",
                motivo=str(razon),
                reintentable=True,
            )

        if isinstance(exc, (TimeoutError, socket.timeout)):
            return ErrorRedChatbot(
                f"El proveedor no respondió en {self.tiempo_limite:.0f} s.",
                motivo=f"timeout tras {self.tiempo_limite:.0f} s",
                reintentable=True,
            )

        if isinstance(exc, ErrorRedChatbot):
            return exc

        return ErrorRedChatbot("Error inesperado al contactar el modelo.", motivo=str(exc))

    def _fragmentos(self, model_name: str, contents: list[dict]):
        """Genera los fragmentos de texto del proveedor, en orden (RF-16).

        Lee el flujo SSE del proveedor línea a línea: cada ``data:`` trae un
        trozo de la respuesta. El iterador se corta en cuanto el proveedor
        cierra, que es cuando ya está todo.
        """
        with request.urlopen(
            self._peticion(model_name, contents, flujo=True), timeout=self.tiempo_limite
        ) as respuesta:
            for cruda in respuesta:
                linea = cruda.decode("utf-8", errors="replace").strip()
                if not linea.startswith("data:"):
                    continue
                cuerpo = linea[len("data:"):].strip()
                if not cuerpo or cuerpo == "[DONE]":
                    continue
                try:
                    trozo = json.loads(cuerpo)
                except ValueError:
                    continue

                candidatos = trozo.get("candidates") or []
                if not candidatos:
                    continue
                partes = candidatos[0].get("content", {}).get("parts", [])
                for parte in partes:
                    texto = parte.get("text")
                    if texto:
                        yield texto

    def _generar_completo(self, model_name: str, contents: list[dict]) -> str:
        """Una respuesta completa, sin streaming. La usa la prueba del panel."""
        with request.urlopen(
            self._peticion(model_name, contents, flujo=False), timeout=self.tiempo_limite
        ) as respuesta:
            cuerpo = json.loads(respuesta.read() or b"{}")

        candidatos = cuerpo.get("candidates") or []
        if not candidatos:
            raise ErrorRedChatbot(
                "El proveedor devolvió una respuesta vacía.",
                motivo=json.dumps(cuerpo)[:300],
            )
        partes = candidatos[0].get("content", {}).get("parts", [])
        texto = "".join(parte.get("text", "") for parte in partes).strip()
        if not texto:
            raise ErrorRedChatbot(
                "El proveedor no devolvió texto utilizable.",
                motivo=json.dumps(cuerpo)[:300],
            )
        return texto

    # ------------------------------------------------------------------ #
    # Reintentos y candidatos
    # ------------------------------------------------------------------ #

    def _con_reintentos(self, operacion, *, ya_emitido):
        """Ejecuta ``operacion(modelo)`` probando modelos y reintentando.

        Args:
            operacion: callable que recibe el nombre del modelo.
            ya_emitido: callable sin argumentos que dice si ya se entregó algún
                fragmento. Con streaming, reintentar después de eso duplicaría
                lo que el usuario ya leyó, así que se deja de reintentar.
        """
        ultimo = None

        for model_name in self.model_candidates:
            for intento in range(self.reintentos):
                try:
                    self.model_name = model_name
                    resultado = operacion(model_name)
                    # Un generador es perezoso: si se devolviera tal cual, el
                    # fallo de conexión ocurriría al iterarlo, **fuera** de este
                    # ámbito, y los reintentos nunca llegarían a aplicarse. Se
                    # fuerza aquí la primera lectura.
                    if hasattr(resultado, "__next__"):
                        return self._con_primer_fragmento_leido(resultado)
                    return resultado
                except Exception as exc:
                    fallo = self._traducir_fallo(exc)
                    ultimo = fallo

                    if ya_emitido():
                        raise fallo
                    if not fallo.reintentable:
                        # Un 403 o un 400 no se arreglan repitiendo: se pasa al
                        # siguiente modelo candidato, si lo hay.
                        break
                    if intento + 1 < self.reintentos:
                        time.sleep(ESPERA_REINTENTO * (intento + 1))

        raise ultimo or ErrorRedChatbot("No se pudo contactar el modelo.")

    @staticmethod
    def _con_primer_fragmento_leido(generador):
        """Iterador con el primer fragmento ya leído dentro del reintento.

        Si el proveedor no devuelve nada, se entrega un iterador vacío en vez de
        dejar que el ``StopIteration`` se confunda con un final de flujo.
        """
        try:
            primero = next(generador)
        except StopIteration:
            return iter(())
        return itertools.chain([primero], generador)

    # ------------------------------------------------------------------ #
    # Conversación
    # ------------------------------------------------------------------ #

    def _registrar_turno(self, user_text: str, respuesta: str) -> None:
        """Añade el par usuario/modelo al historial, una sola vez."""
        self.history.append({"role": "user", "parts": [{"text": user_text}]})
        self.history.append({"role": "model", "parts": [{"text": respuesta}]})

    def enviar_mensaje_stream(self, user_text: str):
        """Envía un mensaje y entrega la respuesta **por fragmentos** (RF-16).

        El turno del usuario entra en el historial al empezar; el del modelo,
        cuando el flujo termina. Si el flujo se corta a media respuesta, entra
        igualmente lo que el usuario llegó a ver, para que el turno siguiente
        sepa qué se respondió (`SCRUM-36`).

        Yields:
            Fragmentos de texto, en orden.

        Raises:
            ErrorRedChatbot: fallo de red, de tiempo o del proveedor.
        """
        self.history.append({"role": "user", "parts": [{"text": user_text}]})
        contents = list(self.history)
        acumulado: list[str] = []

        def ya_emitido() -> bool:
            return bool(acumulado)

        def flujo(model_name: str):
            return self._fragmentos(model_name, contents)

        try:
            for fragmento in self._con_reintentos(flujo, ya_emitido=ya_emitido):
                acumulado.append(fragmento)
                yield fragmento
        finally:
            if acumulado:
                self.history.append(
                    {"role": "model", "parts": [{"text": "".join(acumulado)}]}
                )

    def enviar_mensaje(self, user_text: str) -> str:
        """Envía un mensaje y devuelve la respuesta completa, ya enriquecida.

        Es la variante de una sola pieza; la interfaz usa el flujo progresivo.
        """
        respuesta = "".join(self.enviar_mensaje_stream(user_text))
        return self._enriquecer_respuesta_con_reflexion(respuesta, user_text)

    def probar_respuesta(self, texto: str = "Responde solo con la palabra: listo") -> dict:
        """Comprueba que el modelo **responde**, no solo que la clave existe.

        La usa el panel de conexión: listar modelos prueba la credencial, pero
        no que la generación funcione. Aquí se pide una respuesta de verdad y se
        devuelve lo que el modelo conteste.

        Returns:
            Dict con ``ok``, ``mensaje`` y, si salió bien, ``respuesta`` y
            ``modelo``.
        """
        contents = [{"role": "user", "parts": [{"text": texto}]}]
        try:
            respuesta = self._con_reintentos(
                lambda model_name: self._generar_completo(model_name, contents),
                ya_emitido=lambda: False,
            )
        except ErrorRedChatbot as fallo:
            return {"ok": False, "mensaje": str(fallo), "detalle": fallo.motivo}
        except Exception as fallo:  # pragma: no cover - salvaguarda
            return {"ok": False, "mensaje": "No se pudo generar una respuesta.", "detalle": str(fallo)}

        return {
            "ok": True,
            "mensaje": "El modelo respondió correctamente.",
            "respuesta": respuesta,
            "modelo": self.model_name,
        }

    def set_context(self, context: str):
        """Fija el contexto del proyecto que acompaña a cada turno."""
        self.contexto = (context or "").strip()

    def clear_history(self):
        """Reinicia el historial de conversación."""
        self.history = []

    #: Alias de compatibilidad con el nombre anterior del método.
    send_message = enviar_mensaje

    def _detectar_palabra_clave_transhumana(self, texto: str) -> str | None:
        """Detecta palabras clave de la filosofía transhumana en el texto."""
        texto_normalizado = texto.lower()
        for palabra in RESPUESTAS_REFLEXIVAS.keys():
            if palabra in texto_normalizado:
                return obtener_respuesta_reflexiva(palabra)
        return None

    def _enriquecer_respuesta_con_reflexion(self, respuesta: str, user_text: str) -> str:
        """Añade una reflexión transhumana cuando la pregunta la evoca."""
        reflexion = self._detectar_palabra_clave_transhumana(user_text)
        if reflexion:
            return f"{respuesta}\n\n💭 *Reflexión transhumana:* {reflexion}"
        return respuesta


def crear_servicio(
    usuario_nombre: str,
    contexto: str = "",
    api_key: str | None = None,
    modelo: str | None = None,
    *,
    tiempo_limite: float = TIEMPO_LIMITE_POR_DEFECTO,
    reintentos: int = REINTENTOS_POR_DEFECTO,
) -> ChatbotService:
    """Punto de entrada único para iniciar la conversación de un usuario.

    Args:
        usuario_nombre: nombre del usuario autenticado.
        contexto: contexto del proyecto (``SCRUM-61``); se reinyecta en cada
            turno, así que puede refrescarse con ``set_context``.
        api_key: clave de API ya resuelta por el backend.
        modelo: modelo elegido en el panel de conexión; se prueba primero.
        tiempo_limite: segundos de espera por petición.
        reintentos: intentos por modelo.

    Returns:
        ``ChatbotService`` listo para conversar.

    Raises:
        ConfiguracionChatbotError: no hay clave ni en el parámetro ni en el entorno.
    """
    return ChatbotService(
        usuario_nombre,
        api_key=api_key,
        modelo=modelo,
        tiempo_limite=tiempo_limite,
        reintentos=reintentos,
        contexto=contexto,
    )