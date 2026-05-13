
import os
import json
import socket
import time
from urllib import error, request
from transhumano import (
    DECLARACION_PRINCIPAL,
    PILARES,
    RESPUESTAS_REFLEXIVAS,
    obtener_respuesta_reflexiva,
    obtener_frase_aleatoria
)


SYSTEM_PROMPT = (
    "Eres un asistente inteligente integrado en DatenJäger, un sistema seguro "
    "de gestión documental con cifrado AES-256-GCM y autenticación 2FA.\n\n"
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
    "- Responder preguntas generales de forma concisa y directa\n"
    "- Incluir reflexiones sobre autonomía, libertad y responsabilidad cuando sea pertinente\n\n"
    "Reglas:\n"
    "- Responde siempre en el idioma del usuario (por defecto español)\n"
    "- Sé breve y útil; evita respuestas largas a menos que se pida\n"
    "- No reveles información sensible de otros usuarios\n"
    "- No inventes datos sobre documentos que no conoces\n"
    "- Cuando hables de seguridad, cifrado, auditoría o autonomía, conecta con la filosofía transhumana basada en la Universidad de Cundinamarca de colombia en cuanto a innovacion de persona transhumana\n"
    "- Cultiva el bienestar digital y la responsabilidad del usuario"
)


class ChatbotService:
    """Servicio de IA. Una instancia por sesión de usuario."""

    def __init__(self, usuario_nombre: str = ""):
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY no encontrada. Verifica el archivo .env")

        self.api_key = api_key
        self.model_candidates = [
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-flash-latest",
        ]
        self.usuario_nombre = usuario_nombre
        self.history: list[dict[str, list[dict[str, str]]]] = []
        self.enable_local_fallback = True

    def _build_contents(self, user_text: str) -> list[dict[str, list[dict[str, str]]]]:
        contents = list(self.history)
        contents.append({
            "role": "user",
            "parts": [{"text": user_text}]
        })
        return contents

    def _call_gemini_once(self, model_name: str, contents: list[dict[str, list[dict[str, str]]]]) -> str:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent"
        )
        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            }
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": self.api_key,
            },
        )

        try:
            with request.urlopen(req, timeout=60) as response:
                raw = response.read().decode("utf-8")
            result = json.loads(raw)
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} al contactar Gemini: {detail}") from exc
        except error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, socket.gaierror):
                raise RuntimeError(f"DNS al resolver Gemini: {reason}") from exc
            raise RuntimeError(f"Error de red al contactar Gemini: {reason}") from exc
        except Exception as exc:
            raise RuntimeError(f"Error inesperado al contactar Gemini: {exc}") from exc

        candidates = result.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"Respuesta vacía de Gemini: {result}")

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            raise RuntimeError(f"Gemini no devolvió texto utilizable: {result}")
        return text

    def _call_gemini(self, contents: list[dict[str, list[dict[str, str]]]]) -> str:
        last_error = None

        for model_name in self.model_candidates:
            for attempt in range(3):
                try:
                    self.model_name = model_name
                    return self._call_gemini_once(model_name, contents)
                except RuntimeError as exc:
                    last_error = str(exc)
                    lowered = last_error.lower()

                    if "http 403" in lowered or "permission_denied" in lowered:
                        raise RuntimeError(last_error) from exc

                    if "dns" in lowered or "error de red" in lowered:
                        if attempt < 2:
                            time.sleep(0.5)
                            continue

                    if "http 400" in lowered or "http 404" in lowered:
                        break

                    break

        if last_error is None:
            raise RuntimeError("No se pudo contactar Gemini")
        raise RuntimeError(last_error)

    def _friendly_error_message(self, error_message: str) -> str:
        lowered = error_message.lower()

        if "http 403" in lowered or "permission_denied" in lowered:
            return (
                "Gemini rechazó el acceso del proyecto (403 PERMISSION_DENIED). "
                "Revisa en Google Cloud que la API Generative Language esté habilitada, "
                "que la API key pertenezca al proyecto correcto y que tenga permisos activos."
            )

        if "http 401" in lowered or "unauthorized" in lowered:
            return (
                "Gemini rechazó la autenticación (401). "
                "Revisa que la API key sea válida y no esté revocada."
            )

        if "http 400" in lowered or "bad request" in lowered:
            return (
                "Gemini devolvió una petición inválida (400). "
                "Revisa el nombre del modelo y el formato del payload."
            )

        if "dns" in lowered or "no address associated with hostname" in lowered:
            return (
                "No se pudo resolver el host de Gemini desde este equipo. "
                "Revisa la conexión a internet y el DNS del sistema, o inténtalo de nuevo."
            )

        return error_message

    def _local_fallback_response(self, user_text: str) -> str:
        text = (user_text or "").strip().lower()

        if any(token in text for token in ["hola", "buenas", "hey"]):
            return (
                "Hola. Estoy en modo local de prueba porque Gemini está bloqueado en este proyecto. "
                "Puedo ayudarte a validar la UI y el flujo del chat."
            )

        if any(token in text for token in ["buscar", "pdf", "documento"]):
            return (
                "Modo local: para buscar documentos usa la barra de búsqueda del dashboard "
                "y filtra por nombre, cédula o etiquetas."
            )

        if any(token in text for token in ["reporte", "auditoria", "auditoría"]):
            return (
                "Modo local: puedes generar reportes desde la opción 'Reporte' y revisar actividad "
                "en el módulo de auditoría."
            )

        return (
            "Modo local de prueba activo. Tu integración UI funciona, pero Gemini responde 403 "
            "por permisos del proyecto."
        )

    def send_message(self, user_text: str) -> str:
        """Envía un mensaje y devuelve la respuesta del modelo."""
        try:
            contents = self._build_contents(user_text)
            reply = self._call_gemini(contents)
            
            # Enriquecer respuesta con reflexión transhumana si es pertinente
            reply_enriquecida = self._enriquecer_respuesta_con_reflexion(reply, user_text)

            self.history.append({"role": "user", "parts": [{"text": user_text}]})
            self.history.append({"role": "model", "parts": [{"text": reply_enriquecida}]})
            return reply_enriquecida
        except Exception as e:
            raw_error = str(e)
            if self.enable_local_fallback and (
                "permission_denied" in raw_error.lower() or "http 403" in raw_error.lower()
            ):
                fallback = self._local_fallback_response(user_text)
                self.history.append({"role": "user", "parts": [{"text": user_text}]})
                self.history.append({"role": "model", "parts": [{"text": fallback}]})
                return (
                    "[Gemini no disponible por permisos del proyecto. "
                    "Respuesta en modo local de prueba]\n" + fallback
                )

            return f"[Error al contactar la IA: {self._friendly_error_message(raw_error)}]"

    def set_context(self, context: str):
        """Inyecta contexto inicial del sistema (usuario, permisos, etc.)."""
        self.history = []
        try:
            intro = f"[Contexto del sistema]\n{context}\n[Fin de contexto]"
            self.history.append({"role": "user", "parts": [{"text": intro}]})
        except Exception:
            # si falla el contexto inicial, la sesión sigue sin él
            self.history = []

    def clear_history(self):
        """Reinicia el historial de conversación."""
        self.history = []

    def _detectar_palabra_clave_transhumana(self, texto: str) -> str | None:
        """
        Detecta palabras clave relacionadas con la filosofía transhumana.
        Retorna la reflexión si la encuentra, sino None.
        """
        texto_normalizado = texto.lower()
        for palabra in RESPUESTAS_REFLEXIVAS.keys():
            if palabra in texto_normalizado:
                return obtener_respuesta_reflexiva(palabra)
        return None

    def _enriquecer_respuesta_con_reflexion(self, respuesta: str, user_text: str) -> str:
        """
        Si la pregunta del usuario contiene palabras clave transhumanas,
        enriquece la respuesta con una reflexión contextual.
        """
        reflexion = self._detectar_palabra_clave_transhumana(user_text)
        if reflexion:
            return f"{respuesta}\n\n💭 *Reflexión transhumana:* {reflexion}"
        return respuesta
