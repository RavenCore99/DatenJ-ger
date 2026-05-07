
# chatbot_ui.py
# panel visual del chatbot - CustomTkinter

import threading
import customtkinter as ctk
from chatbot import ChatbotService
from ui_components import get_dynamic_colors


class ChatbotPanel(ctk.CTkFrame):
    """
    Panel de chat integrado al dashboard.
    Se monta dentro de una CTkToplevel desde main.py.
    Interfaz pública: init_session() / end_session()
    """

    def __init__(self, parent, app_ref, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app_ref
        self._service: ChatbotService | None = None
        self._build_ui()

    # ── construcción del panel ─────────────────────────────────────────────

    def _build_ui(self):
        colors = get_dynamic_colors()

        # cabecera
        header = ctk.CTkFrame(self, fg_color=(colors["bg_secondary"]), corner_radius=0)
        header.pack(fill="x", padx=0, pady=(0, 2))

        ctk.CTkLabel(
            header,
            text="  Asistente IA – DatenJäger",
            font=("Arial", 14, "bold"),
            text_color=colors["text_primary"]
        ).pack(side="left", padx=16, pady=10)

        ctk.CTkButton(
            header,
            text="Limpiar chat",
            width=90, height=28,
            fg_color=("#546e7a", "#37474f"),
            hover_color=("#455a64", "#263238"),
            text_color="white",
            font=("Arial", 10),
            corner_radius=8,
            command=self._clear_chat
        ).pack(side="right", padx=12, pady=8)

        # área de mensajes (scroll)
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=(colors["bg_primary"]),
            corner_radius=8,
            label_text=""
        )
        self._scroll.pack(fill="both", expand=True, padx=8, pady=4)

        # zona de entrada
        input_frame = ctk.CTkFrame(
            self,
            fg_color=(colors["bg_secondary"]),
            corner_radius=10
        )
        input_frame.pack(fill="x", padx=8, pady=(4, 8))

        self._entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Escribe tu pregunta...",
            height=42,
            corner_radius=8,
            border_width=2,
            font=("Arial", 12)
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(10, 6), pady=8)
        self._entry.bind("<Return>", lambda e: self._send())

        self._btn_send = ctk.CTkButton(
            input_frame,
            text="Enviar",
            width=85,
            height=42,
            fg_color="#1a6b3c",
            hover_color="#145c32",
            text_color="white",
            font=("Arial", 12, "bold"),
            corner_radius=8,
            command=self._send
        )
        self._btn_send.pack(side="right", padx=(0, 10), pady=8)

    # ── burbujas de chat ───────────────────────────────────────────────────

    def _add_bubble(self, text: str, role: str):
        """Agrega una burbuja al área de mensajes. role = 'user' | 'bot'"""
        colors = get_dynamic_colors()
        is_user = (role == "user")

        row = ctk.CTkFrame(self._scroll, fg_color="transparent")
        row.pack(fill="x", pady=3)

        # ajustar wraplength según tamaño actual del panel
        try:
            wrap = max(250, self._scroll.winfo_width() - 100)
        except Exception:
            wrap = 360

        bubble = ctk.CTkLabel(
            row,
            text=text,
            wraplength=wrap,
            justify="left",
            font=("Arial", 12),
            fg_color="#1a6b3c" if is_user else (colors["bg_secondary"]),
            text_color="white" if is_user else colors["text_primary"],
            corner_radius=12,
            padx=14,
            pady=8
        )
        bubble.pack(
            side="right" if is_user else "left",
            padx=8
        )

        # auto-scroll al último mensaje
        self._scroll.after(
            100,
            lambda: self._scroll._parent_canvas.yview_moveto(1.0)
        )

    def _add_typing_indicator(self):
        """Indicador visual mientras espera respuesta de la IA."""
        colors = get_dynamic_colors()
        self._typing_lbl = ctk.CTkLabel(
            self._scroll,
            text="  IA pensando...",
            font=("Arial", 11, "italic"),
            text_color=colors["text_secondary"]
        )
        self._typing_lbl.pack(anchor="w", padx=16, pady=2)

    def _remove_typing_indicator(self):
        if hasattr(self, "_typing_lbl") and self._typing_lbl.winfo_exists():
            self._typing_lbl.destroy()

    # ── lógica de envío ────────────────────────────────────────────────────

    def _send(self):
        text = self._entry.get().strip()
        if not text or self._service is None:
            return

        self._entry.delete(0, "end")
        self._btn_send.configure(state="disabled")
        self._add_bubble(text, "user")
        self._add_typing_indicator()

        # respuesta en hilo separado para no congelar la UI
        threading.Thread(
            target=self._fetch_response,
            args=(text,),
            daemon=True
        ).start()

    def _fetch_response(self, text: str):
        response = self._service.send_message(text)
        # volver al hilo principal para actualizar widgets
        self.after(0, lambda: self._on_response(response))

    def _on_response(self, text: str):
        self._remove_typing_indicator()
        self._add_bubble(text, "bot")
        self._btn_send.configure(state="normal")

    def _clear_chat(self):
        for widget in self._scroll.winfo_children():
            widget.destroy()
        if self._service:
            self._service.clear_history()

    # ── API pública (llamada desde main.py) ────────────────────────────────

    def init_session(self, usuario_nombre: str, context: str = ""):
        """Inicializa el servicio y saluda al usuario. Llamar post-login."""
        try:
            self._service = ChatbotService(usuario_nombre)
            if context:
                self._service.set_context(context)
            self._add_bubble(
                f"Hola {usuario_nombre}, soy tu asistente de DatenJäger. "
                "¿En qué puedo ayudarte hoy?",
                "bot"
            )
        except ValueError as e:
            # API key no configurada — mostrar aviso en el chat
            self._service = None
            self._add_bubble(
                f"⚠ No se pudo iniciar el asistente: {e}\n"
                "Configura GEMINI_API_KEY en el archivo .env",
                "bot"
            )

    def end_session(self):
        """Limpia historial y referencia al servicio. Llamar en logout."""
        self._service = None
        self._clear_chat()
