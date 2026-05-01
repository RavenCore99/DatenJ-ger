

# Copyright (c) 2024 DatenJäger. All rights reserved.
# sistema de gestion documental | 2FA | aes-256 |
# main.py - aplicacion principal datenjager v2

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import secrets
from datetime import datetime, timedelta
import hashlib
import random
import threading
import pyotp
import qrcode
from PIL import ImageTk, Image
from io import BytesIO

# modulos del proyecto
from config import Config
from encryption import EncryptionManager
from database import (conectar_db, hash_contrasena, verify_contrasena,
                      format_size, format_date_friendly, ease_in_out,
                      check_account_locked, record_failed_attempt,
                      reset_failed_attempts, password_strength,
                      set_trust_token, check_trust_token, clear_trust_token)
from ui_components import (Notification, ProgressBarModerno, DashboardWidget,
                           GradientBackground, CosmicBackground,
                           PasswordStrengthBar, ConfirmDialog,
                           PDFViewerWindow, get_dynamic_colors)
from reporter import ReporteInventario
from icons import get_icon
from personas import GestorPersonas
from audit import GestorAuditoria
from pdf_manager import GestorPDF



# config customtkinter


ctk.set_default_color_theme("blue")


# colores

COLOR_BG_LIGHT   = "#f0f4ff"
COLOR_BG_DARK    = "#1a1a2e"
COLOR_PRIMARY    = "#4CAF50"
COLOR_SECONDARY  = "#2196F3"
COLOR_WARNING    = "#FF9800"
COLOR_ERROR      = "#F44336"
COLOR_SUCCESS    = "#4CAF50"
COLOR_TEXT_LIGHT = "#1a237e"
COLOR_TEXT_DARK  = "#e0e0e0"


# clase principal


class AppDBPDF:
    

    def __init__(self, root):
        # init
        self.root = root
        self.root.title("DatenJäger v.2.0 – Gestión Documental ")
        self.root.geometry("1100x760")

        self.config = Config()
        window_size = self.config.get("window_size", "1100x760")
        self.root.geometry(window_size)

        # tema guardado
        theme = self.config.get("theme", "System")
        ctk.set_appearance_mode(theme)

        self.conn, self.cursor = conectar_db()
        self._db_lock = threading.Lock()
        self.usuario_actual = None
        self.usuario_nombre = None
        self._session_key   = None
        self.animating = False
        self._search_timer = None
        self._configure_timer = None
        self._idle_timer = None
        self._idle_warning_timer = None
        self._idle_bind_ids = []
        self._theme_refresh_job = None
        self._last_theme_mode = ctk.get_appearance_mode()

        # modulos externos
        self.personas = GestorPersonas(self)
        self.auditoria = GestorAuditoria(self)
        self.pdf = GestorPDF(self)

        self._setup_atajos()
        self._crear_frames()
        self._apply_treeview_style()
        self._setup_treeview_sorting()
        self._start_theme_autorefresh()
        self.root.minsize(900, 650)
        

        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Configure>", self._on_window_configure)

        # restaurar ventana
        if self.config.get("window_maximized", False):
            self.root.after(100, self._maximize_window)

    def get_colors(self):
        # colores segun tema
        return get_dynamic_colors()

    def _get_auth_palette(self):
        # paleta de pantallas de acceso (fuera de dashboard)
        if ctk.get_appearance_mode() == "Dark":
            return {
                "card_border": "#2a3f72",
                "btn_primary_fg": "#2e7d32",
                "btn_primary_hover": "#1b5e20",
                "btn_secondary_fg": "#1565c0",
                "btn_secondary_hover": "#0d47a1",
                "btn_warning_fg": "#ef6c00",
                "btn_warning_hover": "#e65100",
                "btn_neutral_fg": "#546e7a",
                "btn_neutral_hover": "#455a64",
            }
        return {
            "card_border": "#b6c8f7",
            "btn_primary_fg": "#2e7d32",
            "btn_primary_hover": "#1b5e20",
            "btn_secondary_fg": "#1565c0",
            "btn_secondary_hover": "#0d47a1",
            "btn_warning_fg": "#f57c00",
            "btn_warning_hover": "#ef6c00",
            "btn_neutral_fg": "#607d8b",
            "btn_neutral_hover": "#546e7a",
        }

    def _start_theme_autorefresh(self):
        # refresco periodico para asegurar consistencia visual sin reiniciar app
        def _tick():
            try:
                current_mode = ctk.get_appearance_mode()
                self.actualizar_colores_dinamicos(refresh_data=False)
                self.root.event_generate("<<ThemeChanged>>", when="tail")
                self._last_theme_mode = current_mode
            except Exception:
                pass
            self._theme_refresh_job = self.root.after(1400, _tick)

        if self._theme_refresh_job is None:
            self._theme_refresh_job = self.root.after(1400, _tick)

    def _show_modal_window(self, window, delay_ms=0):
        # mostrar ventana modal
        def _activate():
            if not window.winfo_exists():
                return
            try:
                window.deiconify()
                window.lift()
                window.focus_force()
                window.update_idletasks()
                if window.winfo_viewable():
                    window.grab_set()
            except tk.TclError:
                # si falla el grab
                pass

        window.after(delay_ms, _activate)

    def _setup_atajos(self):
                # atajos
        self.root.bind("<Control-q>", lambda e: self.cerrar_conexion_y_salir())
        self.root.bind("<Control-f>", lambda e: self.entry_busqueda.focus() if hasattr(self, 'entry_busqueda') else None)
        self.root.bind("<Control-n>", lambda e: self.mostrar_agregar_pdf() if self.usuario_actual else None)
        self.root.bind("<Delete>", lambda e: self.eliminar_pdf() if self.usuario_actual else None)

    def toggle_fullscreen(self, event=None):
                        # toggle fullscreen
        try:
            if os.name == 'nt':                 # Windows
                state = self.root.state()
                if state == 'zoomed':
                    self.root.state('normal')
                else:
                    self.root.state('zoomed')
            else:                                # Linux / macOS
                zoomed = self.root.attributes('-zoomed')
                self.root.attributes('-zoomed', not zoomed)
        except Exception:
            pass

    def _maximize_window(self):
                                        # maximizar ventana
        try:
            if os.name == 'nt':
                self.root.state('zoomed')
            else:
                self.root.attributes('-zoomed', True)
        except Exception:
            pass

    def _on_window_configure(self, event=None):
                        # guardar tamaño
        if event is None or event.widget is not self.root:
            return
                        # cancelar guardado pendiente
        if self._configure_timer:
            self.root.after_cancel(self._configure_timer)
        self._configure_timer = self.root.after(500, self._save_window_state)

    def _save_window_state(self):
                        # guardar estado
        self._configure_timer = None
        try:
            maximized = False
            if os.name == 'nt':
                maximized = self.root.state() == 'zoomed'
            else:
                maximized = bool(self.root.attributes('-zoomed'))
            self.config.set("window_maximized", maximized)
            if not maximized:
                w = self.root.winfo_width()
                h = self.root.winfo_height()
                if w > 100 and h > 100:
                    self.config.set("window_size", f"{w}x{h}")
        except Exception:
            pass

    def _crear_frames(self):
                    # crear frames
        colors = self.get_colors()

        # pantalla intro
        self.frame_intro = ctk.CTkFrame(self.root, fg_color=COLOR_BG_DARK)
        self.frame_intro.pack(expand=True, fill="both")

        # fondo cosmico (siempre dark, no cambia con tema)
        self._intro_bg = CosmicBackground(
            self.frame_intro, num_stars=70,
            colors_dark=[("#050510", "#0d1b3e"), ("#0d1b3e", "#1a0a2e")],
            colors_light=[("#050510", "#0d1b3e"), ("#0d1b3e", "#1a0a2e")]
        )
        self._intro_bg.place(relx=0, rely=0, relwidth=1, relheight=1)

        intro_card = ctk.CTkFrame(
            self.frame_intro, fg_color="#0d0d2b",
            corner_radius=18,
            bg_color="#050510"
        )
        self._intro_card = intro_card
        intro_card.place(relx=0.5, rely=0.5, anchor="center")

        # typewriter
        self.intro_text = ctk.CTkLabel(
            intro_card,
            text="",
            font=("Arial", 48, "bold"),
            text_color="#e0e0e0"
        )
        self.intro_text.pack(padx=80, pady=(44, 4))

        self._intro_subtitle = ctk.CTkLabel(
            intro_card,
            text="",
            text_color="#a0b4ff",
            font=("Arial", 13)
        )
        self._intro_subtitle.pack(pady=(0, 2))

        self._intro_tech = ctk.CTkLabel(
            intro_card,
            text="AES-256-GCM  ·  2FA  ·  PBKDF2",
            text_color="#5c6bc0",
            font=("Arial", 11)
        )
        self._intro_tech.pack(pady=(0, 16))
        self._intro_tech.configure(text_color="#0d0d2b")  # oculto al inicio dark-only

        # hint
        self._intro_hint = ctk.CTkLabel(
            intro_card,
            text="Presiona cualquier tecla o haz clic para continuar",
            font=("Arial", 11),
            text_color="#0d0d2b"
        )
        self._intro_hint.pack(pady=(8, 36))

        # motor typewriter
        self._tw_phrases = [
            "DatenJäger",
            "Seguridad Inquebrantable",
            "Gestión Inteligente",
            "Tus Documentos, Protegidos",
            "Cifrado  AES-256",
            "Privacidad Sin Compromiso",
        ]
        self._tw_idx = 0       # índice de frase actual
        self._tw_char_idx = 0  # posición del carácter
        self._tw_deleting = False
        self._tw_paused = False
        self._intro_revealed = False

        def _typewriter_tick():
            try:
                if not self.frame_intro.winfo_ismapped():
                    return
            except tk.TclError:
                return

            phrase = self._tw_phrases[self._tw_idx]

            if self._tw_paused:
                self._tw_paused = False
                self._tw_deleting = True
                self.root.after(50, _typewriter_tick)
                return

            if not self._tw_deleting:
                # escribir
                self._tw_char_idx += 1
                display = phrase[:self._tw_char_idx]
                self.intro_text.configure(text=display)

                if self._tw_char_idx >= len(phrase):
                    # pausa
                    self._tw_paused = True
                    # mostrar subtitulo
                    if self._tw_idx == 0:
                        self.root.after(600, lambda: (
                            setattr(self, "_intro_revealed", True),
                            self._intro_subtitle.configure(
                                text="Sistema de Gestión Documental Seguro",
                                text_color="#a0b4ff"),
                            self._intro_tech.configure(text_color="#5c6bc0"),
                            self._intro_hint.configure(text_color="#5c6bc0")
                        ))
                    self.root.after(2200, _typewriter_tick)
                    return

                speed = 65 if self._tw_char_idx > 2 else 120
                self.root.after(speed, _typewriter_tick)
            else:
                # borrar
                self._tw_char_idx -= 1
                display = phrase[:max(0, self._tw_char_idx)]
                self.intro_text.configure(text=display if display else " ")

                if self._tw_char_idx <= 0:
                    # siguiente frase
                    self._tw_deleting = False
                    self._tw_idx = (self._tw_idx + 1) % len(self._tw_phrases)
                    self._tw_char_idx = 0
                    self.root.after(400, _typewriter_tick)
                    return

                self.root.after(35, _typewriter_tick)

        # delay inicial
        self.root.after(500, _typewriter_tick)

        # pulso hint
        def _pulse_hint(visible=True):
            try:
                if self.frame_intro.winfo_ismapped():
                    col = "#5c6bc0" if visible else "#2a2a5e"
                    self._intro_hint.configure(text_color=col)
                    self.root.after(800, lambda: _pulse_hint(not visible))
            except tk.TclError:
                pass
        self.root.after(4000, _pulse_hint)

        # binds para avanzar
        self._intro_active = True

        def _intro_trigger(event=None):
            if self._intro_active:
                self._intro_active = False
                # limpiar binds
                self.root.unbind("<Key>")
                self.root.unbind("<Button-1>")
                self.on_intro_click()

        self.root.bind("<Key>", _intro_trigger)
        self.root.bind("<Button-1>", _intro_trigger)
        # bind en hijos
        self.frame_intro.bind("<Button-1>", _intro_trigger)
        intro_card.bind("<Button-1>", _intro_trigger)
        self.intro_text.bind("<Button-1>", _intro_trigger)
        self._intro_subtitle.bind("<Button-1>", _intro_trigger)
        self._intro_tech.bind("<Button-1>", _intro_trigger)
        self._intro_hint.bind("<Button-1>", _intro_trigger)

        # pantalla inicial
        self.frame_inicial = ctk.CTkFrame(self.root, fg_color=COLOR_BG_DARK)

        _bg_inicial = CosmicBackground(
            self.frame_inicial,
            num_stars=30, num_comets=2, num_sparkles=0,
            colors_dark=[("#1a1a2e", "#16213e"), ("#16213e", "#0f3460")],
            colors_light=[("#e3f2fd", "#bbdefb"), ("#bbdefb", "#e8f5e9")]
        )
        _bg_inicial.place(relx=0, rely=0, relwidth=1, relheight=1)

        card_inicial = ctk.CTkFrame(
            self.frame_inicial, fg_color=("#f5f7ff", "#1e2a4a"),
            corner_radius=18,
            bg_color=("#e3f2fd", "#1a1a2e")
        )
        self._card_inicial = card_inicial
        card_inicial.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            card_inicial,
            text="  DatenJäger",
            image=get_icon("key-round", 28),
            compound="left",
            font=("Arial", 28, "bold"),
            text_color=colors["text_primary"]
        ).pack(pady=(30, 4))

        self._initial_subtitle = ctk.CTkLabel(
            card_inicial,
            text="Seguridad · Privacidad · Control",
            font=("Arial", 11),
            text_color=COLOR_SECONDARY
        )
        self._initial_subtitle.pack(pady=(0, 24))

        self._btn_initial_login = ctk.CTkButton(
            card_inicial,
            text="  Iniciar Sesión",
            image=get_icon("unlock", 20),
            compound="left",
            command=self.mostrar_login,
            fg_color=COLOR_PRIMARY,
            hover_color="#388E3C",
            text_color="white",
            font=("Arial", 13, "bold"),
            corner_radius=12,
            width=280, height=48
        )
        self._btn_initial_login.pack(pady=8)

        self._btn_initial_register = ctk.CTkButton(
            card_inicial,
            text="  Crear Usuario",
            image=get_icon("pen-line", 20),
            compound="left",
            command=self.mostrar_registro,
            fg_color=COLOR_SECONDARY,
            hover_color="#1976D2",
            text_color="white",
            font=("Arial", 13, "bold"),
            corner_radius=12,
            width=280, height=48
        )
        self._btn_initial_register.pack(pady=8)

        self._initial_footer = ctk.CTkLabel(
            card_inicial,
            text="v.2.0 – AES-256-GCM + PBKDF2 + 2FA",
            font=("Arial", 9),
            text_color=colors["text_secondary"]
        )
        self._initial_footer.pack(pady=(16, 28))

        # pantalla login
        self.frame_login = ctk.CTkFrame(self.root, fg_color=COLOR_BG_DARK)

        _bg_login = GradientBackground(
            self.frame_login,
            colors_dark=[("#1a1a2e", "#0d47a1"), ("#0d47a1", "#1a1a2e")],
            colors_light=[("#e8f5e9", "#c8e6c9"), ("#c8e6c9", "#e8f5e9")]
        )
        _bg_login.place(relx=0, rely=0, relwidth=1, relheight=1)

        card_login = ctk.CTkFrame(
            self.frame_login, fg_color=("#f5f7ff", "#1e2a4a"),
            corner_radius=18,
            bg_color=("#d8edda", "#0d2a54")
        )
        self._card_login = card_login
        card_login.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            card_login,
            text="Iniciar Sesión",
            font=("Arial", 24, "bold"),
            text_color=colors["text_primary"]
        ).pack(pady=(28, 4))

        ctk.CTkLabel(
            card_login,
            text="Ingresa tus credenciales para continuar",
            font=("Arial", 11),
            text_color=colors["text_secondary"]
        ).pack(pady=(0, 16))

        ctk.CTkLabel(
            card_login, text="Usuario",
            text_color=colors["text_primary"], font=("Arial", 11, "bold")
        ).pack(anchor="w", padx=40)
        self.entry_usuario_login = ctk.CTkEntry(
            card_login, placeholder_text="Tu nombre de usuario",
            width=320, height=42, corner_radius=8, border_width=2,
            font=("Arial", 12)
        )
        self.entry_usuario_login.pack(pady=(4, 12))
        self.entry_usuario_login.bind("<Return>", lambda e: self.entry_contrasena_login.focus())

        ctk.CTkLabel(
            card_login, text="Contraseña",
            text_color=colors["text_primary"], font=("Arial", 11, "bold")
        ).pack(anchor="w", padx=40)
        pw_row_login = ctk.CTkFrame(card_login, fg_color="transparent")
        pw_row_login.pack(pady=(4, 4))
        self.entry_contrasena_login = ctk.CTkEntry(
            pw_row_login, placeholder_text="Tu contraseña",
            width=278, height=42, corner_radius=8, border_width=2,
            font=("Arial", 12), show="●"
        )
        self.entry_contrasena_login.pack(side="left")
        self._show_pw_login = False
        ctk.CTkButton(
            pw_row_login, text="", image=get_icon("eye", 16), width=38, height=42,
            fg_color=COLOR_SECONDARY, hover_color="#1565c0",
            corner_radius=8, font=("Arial", 13),
            command=lambda: self._toggle_pw(
                self.entry_contrasena_login, "_show_pw_login")
        ).pack(side="left", padx=(4, 0))

        self.entry_contrasena_login.bind("<Return>", lambda e: self.login())

        self._btn_login_next = ctk.CTkButton(
            card_login, text="  Siguiente",
            image=get_icon("check-circle", 18),
            compound="left",
            command=self.login,
            fg_color=COLOR_PRIMARY, hover_color="#388E3C",
            text_color="white", font=("Arial", 12, "bold"),
            corner_radius=10, width=320, height=44
        )
        self._btn_login_next.pack(pady=(16, 8))

        self._btn_login_back = ctk.CTkButton(
            card_login, text="  Volver",
            image=get_icon("arrow-left", 16),
            compound="left",
            command=self.mostrar_inicial,
            fg_color=("#90a4ae", "#546e7a"), hover_color=("#78909c", "#455a64"),
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=10, width=320, height=38
        )
        self._btn_login_back.pack(pady=(0, 28))

                         # pantalla 2fa
        self.frame_2fa = ctk.CTkFrame(self.root, fg_color=COLOR_BG_DARK)

        _bg_2fa = GradientBackground(
            self.frame_2fa,
            colors_dark=[("#1a1a2e", "#4a0072"), ("#4a0072", "#1a1a2e")],
            colors_light=[("#f3e5f5", "#e1bee7"), ("#e1bee7", "#f3e5f5")]
        )
        _bg_2fa.place(relx=0, rely=0, relwidth=1, relheight=1)

        card_2fa = ctk.CTkFrame(
            self.frame_2fa, fg_color=("#f5f0ff", "#1e1a2e"),
            corner_radius=18,
            bg_color=("#ead5f5", "#30004e")
        )
        self._card_2fa = card_2fa
        card_2fa.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            card_2fa, text="Verificación 2FA",
            font=("Arial", 22, "bold"),
            text_color=colors["text_primary"]
        ).pack(pady=(28, 6))

        ctk.CTkLabel(
            card_2fa,
            text="Ingresa el código de 6 dígitos de tu\naplicación autenticadora:",
            text_color=colors["text_secondary"],
            font=("Arial", 11), justify="center"
        ).pack(pady=(0, 14))

        self.entry_2fa_code = ctk.CTkEntry(
            card_2fa, placeholder_text="• • • • • •",
            width=220, height=54, corner_radius=10, border_width=2,
            font=("Arial", 26, "bold"), justify="center"
        )
        self.entry_2fa_code.pack(pady=(0, 6))
        self.entry_2fa_code.bind("<Return>", lambda e: self.verificar_2fa())

                     # countdown ring totp
        self._totp_timer_label = ctk.CTkLabel(
            card_2fa, text="30s", font=("Arial", 10),
            text_color=colors["text_secondary"]
        )
        self._totp_timer_label.pack()
        self._start_totp_timer()

        self._btn_2fa_verify = ctk.CTkButton(
            card_2fa, text="  Verificar",
            image=get_icon("check-circle", 18),
            compound="left",
            command=self.verificar_2fa,
            fg_color=COLOR_PRIMARY, hover_color="#388E3C",
            text_color="white", font=("Arial", 12, "bold"),
            corner_radius=10, width=280, height=44
        )
        self._btn_2fa_verify.pack(pady=(12, 6))

        self._backup_hint_2fa = ctk.CTkLabel(
            card_2fa,
            text="¿Sin acceso al teléfono? Usa un código de respaldo",
            text_color=COLOR_WARNING, font=("Arial", 10)
        )
        self._backup_hint_2fa.pack(pady=(4, 0))

        self._btn_2fa_backup = ctk.CTkButton(
            card_2fa, text="  Código de Respaldo",
            image=get_icon("refresh-cw", 16),
            compound="left",
            command=self.usar_codigo_respaldo,
            fg_color=COLOR_WARNING, hover_color=("#FB8C00", "#F57C00"),
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=10, width=280, height=36
        )
        self._btn_2fa_backup.pack(pady=6)

        self._btn_2fa_back = ctk.CTkButton(
            card_2fa, text="  Volver",
            image=get_icon("arrow-left", 16),
            compound="left",
            command=self.mostrar_login,
            fg_color=("#90a4ae", "#546e7a"), hover_color=("#78909c", "#455a64"),
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=10, width=280, height=36
        )
        self._btn_2fa_back.pack(pady=(0, 28))

        # pantalla registro
        self.frame_registro = ctk.CTkFrame(self.root, fg_color=COLOR_BG_DARK)

        _bg_reg = GradientBackground(
            self.frame_registro,
            colors_dark=[("#1a2e1a", "#0d3b2e"), ("#0d3b2e", "#1a2e1a")],
            colors_light=[("#e8f5e9", "#c8e6c9"), ("#c8e6c9", "#a5d6a7")]
        )
        _bg_reg.place(relx=0, rely=0, relwidth=1, relheight=1)

        card_reg = ctk.CTkFrame(
            self.frame_registro, fg_color=("#f0fff4", "#142e1e"),
            corner_radius=18,
            bg_color=("#d8edda", "#122e22")
        )
        self._card_reg = card_reg
        card_reg.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            card_reg, text="Crear Usuario",
            font=("Arial", 24, "bold"),
            text_color=colors["text_primary"]
        ).pack(pady=(28, 4))

        ctk.CTkLabel(
            card_reg,
            text="Crea tu cuenta segura con 2FA",
            font=("Arial", 11),
            text_color=colors["text_secondary"]
        ).pack(pady=(0, 16))

        ctk.CTkLabel(
            card_reg, text="Nombre de usuario",
            text_color=colors["text_primary"], font=("Arial", 11, "bold")
        ).pack(anchor="w", padx=40)
        self.entry_usuario_registro = ctk.CTkEntry(
            card_reg, placeholder_text="Elige un nombre de usuario",
            width=340, height=42, corner_radius=8, border_width=2,
            font=("Arial", 12)
        )
        self.entry_usuario_registro.pack(pady=(4, 10))

        ctk.CTkLabel(
            card_reg, text="Contraseña",
            text_color=colors["text_primary"], font=("Arial", 11, "bold")
        ).pack(anchor="w", padx=40)

        pw_row_reg = ctk.CTkFrame(card_reg, fg_color="transparent")
        pw_row_reg.pack(pady=(4, 2))
        self.entry_contrasena_registro = ctk.CTkEntry(
            pw_row_reg, placeholder_text="Mínimo 8 caracteres",
            width=298, height=42, corner_radius=8, border_width=2,
            font=("Arial", 12), show="●"
        )
        self.entry_contrasena_registro.pack(side="left")
        self._show_pw_reg = False
        ctk.CTkButton(
            pw_row_reg, text="", image=get_icon("eye", 16), width=38, height=42,
            fg_color=COLOR_SECONDARY, hover_color="#1565c0",
            corner_radius=8, font=("Arial", 13),
            command=lambda: self._toggle_pw(
                self.entry_contrasena_registro, "_show_pw_reg")
        ).pack(side="left", padx=(4, 0))

        # barra fortaleza
        self._pw_strength_bar = PasswordStrengthBar(card_reg)
        self._pw_strength_bar.pack(fill="x", padx=40, pady=(4, 8))
        self.entry_contrasena_registro.bind(
            "<KeyRelease>",
            lambda e: self._pw_strength_bar.update(
                self.entry_contrasena_registro.get())
        )

        self._btn_reg_submit = ctk.CTkButton(
            card_reg, text="  Registrar",
            image=get_icon("check-circle", 18),
            compound="left",
            command=self.registrarse,
            fg_color=COLOR_SECONDARY, hover_color="#1976D2",
            text_color="white", font=("Arial", 12, "bold"),
            corner_radius=10, width=340, height=44
        )
        self._btn_reg_submit.pack(pady=(8, 8))

        self._btn_reg_back = ctk.CTkButton(
            card_reg, text="  Volver",
            image=get_icon("arrow-left", 16),
            compound="left",
            command=self.mostrar_inicial,
            fg_color=("#90a4ae", "#546e7a"), hover_color=("#78909c", "#455a64"),
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=10, width=340, height=36
        )
        self._btn_reg_back.pack(pady=(0, 28))

        # setup 2fa
        self.frame_setup_2fa = ctk.CTkFrame(self.root, fg_color=COLOR_BG_DARK)

        _bg_s2fa = GradientBackground(
            self.frame_setup_2fa,
            colors_dark=[("#2e1a00", "#5d2d00"), ("#5d2d00", "#2e1a00")],
            colors_light=[("#fff8e1", "#ffe082"), ("#ffe082", "#fff8e1")]
        )
        _bg_s2fa.place(relx=0, rely=0, relwidth=1, relheight=1)

        # scroll para qr
        self._setup2fa_scroll = ctk.CTkScrollableFrame(
            self.frame_setup_2fa,
            fg_color=("#fffde7", "#1e1600"),
            corner_radius=18,
            bg_color=("#ffe082", "#3a2200"),
            width=460, height=520
        )
        self._setup2fa_scroll.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            self._setup2fa_scroll,
            text="Configurar Autenticación 2FA",
            font=("Arial", 20, "bold"),
            text_color=colors["text_primary"]
        ).pack(pady=(20, 6))

        ctk.CTkLabel(
            self._setup2fa_scroll,
            text="1. Abre Google Authenticator o Microsoft Authenticator",
            text_color=colors["text_primary"], font=("Arial", 11)
        ).pack(pady=4, anchor="w", padx=20)
        ctk.CTkLabel(
            self._setup2fa_scroll,
            text="2. Escanea el código QR de abajo:",
            text_color=colors["text_primary"], font=("Arial", 11)
        ).pack(pady=2, anchor="w", padx=20)

        # espacio para el qr
        qr_card = ctk.CTkFrame(
            self._setup2fa_scroll, fg_color=("#ffffff", "#1a1a1a"),
            corner_radius=12, bg_color="transparent"
        )
        self._qr_card = qr_card
        qr_card.pack(pady=10)
        self.label_qr = ctk.CTkLabel(
            qr_card, text="[QR Code]",
            text_color=colors["text_primary"], font=("Arial", 11)
        )
        self.label_qr.pack(padx=16, pady=16)

        ctk.CTkLabel(
            self._setup2fa_scroll,
            text="Clave secreta (si el QR no funciona):",
            text_color=colors["text_primary"], font=("Arial", 11)
        ).pack(pady=(6, 2), anchor="w", padx=20)

        secret_row = ctk.CTkFrame(self._setup2fa_scroll, fg_color="transparent")
        secret_row.pack(pady=2)
        self.label_secret = ctk.CTkLabel(
            secret_row, text="",
            text_color=COLOR_WARNING, font=("Arial", 13, "bold")
        )
        self.label_secret.pack(side="left", padx=(0, 8))
        self._btn_copy_secret = ctk.CTkButton(
            secret_row, text="  Copiar",
            image=get_icon("clipboard", 14),
            compound="left",
            width=90, height=30,
            fg_color=COLOR_SECONDARY, hover_color="#1565c0",
            font=("Arial", 10, "bold"), corner_radius=6,
            command=self._copy_totp_secret
        )
        self._btn_copy_secret.pack(side="left")

        ctk.CTkLabel(
            self._setup2fa_scroll,
            text="3. Ingresa el código de 6 dígitos para confirmar:",
            text_color=colors["text_primary"], font=("Arial", 11)
        ).pack(pady=(12, 4), anchor="w", padx=20)

        self.entry_confirm_2fa = ctk.CTkEntry(
            self._setup2fa_scroll, placeholder_text="000000",
            width=300, height=48, corner_radius=8, border_width=2,
            font=("Arial", 22, "bold"), justify="center"
        )
        self.entry_confirm_2fa.pack(pady=6)

        self._btn_setup_confirm = ctk.CTkButton(
            self._setup2fa_scroll, text="  Confirmar y Activar 2FA",
            image=get_icon("check-circle", 18),
            compound="left",
            command=self.confirmar_setup_2fa,
            fg_color=COLOR_PRIMARY, hover_color="#388E3C",
            text_color="white", font=("Arial", 12, "bold"),
            corner_radius=10, width=320, height=44
        )
        self._btn_setup_confirm.pack(pady=(10, 6))

        self._setup_warning_label = ctk.CTkLabel(
            self._setup2fa_scroll,
            text="Guarda tus códigos de respaldo en un lugar seguro",
            text_color=COLOR_WARNING, font=("Arial", 10, "bold")
        )
        self._setup_warning_label.pack(pady=(4, 16))

        # panel principal
        # tuple ctk claro/oscuro
        self.frame_principal = ctk.CTkFrame(self.root, fg_color=(COLOR_BG_LIGHT, COLOR_BG_DARK))

        # navbar
        navbar = ctk.CTkFrame(
            self.frame_principal,
            fg_color=("#1a237e", "#0d1b3e"),
            height=56, corner_radius=0
        )
        navbar.pack(fill="x")
        navbar.pack_propagate(False)

        ctk.CTkLabel(
            navbar, text="  DatenJäger",
            image=get_icon("key-round", 22),
            compound="left",
            font=("Arial", 18, "bold"), text_color="white"
        ).pack(side="left", padx=16, pady=10)

        # badge usuario
        self._user_badge = ctk.CTkLabel(
            navbar, text="",
            font=("Arial", 11), text_color="#90caf9",
            fg_color=("#1e3a8a", "#0a1929"),
            corner_radius=8
        )
        self._user_badge.pack(side="left", padx=8)

                    # botones navbar
        def _make_nav_btn(text, command, color="#2e3f8a", hover="#3a4faa"):
            return ctk.CTkButton(
                navbar, text=text, command=command,
                width=110, height=34,
                fg_color=color, hover_color=hover,
                corner_radius=7, font=("Arial", 10, "bold")
            )

        _make_nav_btn("  Cerrar Sesión", self._logout,
                      "#C62828", "#B71C1C").pack(side="right", padx=6, pady=10)

        def toggle_theme():
            current_mode = ctk.get_appearance_mode()
            new_mode = "Light" if current_mode == "Dark" else "Dark"
            ctk.set_appearance_mode(new_mode)
            self.config.set("theme", new_mode)
            btn_theme.configure(
                text="  Claro" if new_mode == "Dark" else "  Oscuro"
            )
            self.actualizar_colores_dinamicos()
            self.root.event_generate("<<ThemeChanged>>", when="tail")

        current_theme = ctk.get_appearance_mode()
        btn_theme = _make_nav_btn(
            "  Claro" if current_theme == "Dark" else "  Oscuro",
            toggle_theme
        )
        btn_theme.pack(side="right", padx=4, pady=10)

        _make_nav_btn(
            "  Mi Cuenta",
            self.abrir_configuracion_cuenta,
            color="#1565c0", hover="#0d47a1"
        ).pack(side="right", padx=4, pady=10)

        _make_nav_btn(
            "  Auditoría",
            self.auditoria.mostrar,
            color="#37474f", hover="#455a64"
        ).pack(side="right", padx=4, pady=10)

        _make_nav_btn(
            "  Personas",
            self.personas.mostrar,
            color="#6A1B9A", hover="#4A148C"
        ).pack(side="right", padx=4, pady=10)

        _make_nav_btn(
            "  Reporte",
            lambda: self.exportar_reporte_dashboard("pdf"),
            color="#00695c", hover="#004d40"
        ).pack(side="right", padx=4, pady=10)

        _make_nav_btn(
            "  Acerca de",
            lambda: Notification(
                self.root,
                "DatenJäger v.2.0",
                "Encriptación AES-256-GCM · PBKDF2 · 2FA\nSeguridad Empresarial Moderna",
                notification_type="info", duration=4000
            )
        ).pack(side="right", padx=4, pady=10)

                # progress bar
        self.progress_bar = ProgressBarModerno(self.frame_principal)
        self.progress_bar.pack(fill="x", pady=0)

                    # dashboard
        self.dashboard_container = ctk.CTkFrame(
            self.frame_principal, fg_color="transparent"
        )
        self.dashboard_container.pack(fill="x", padx=14)

            # toolbar
        toolbar_container = ctk.CTkFrame(self.frame_principal, fg_color="transparent")
        toolbar_container.pack(fill="x", padx=14, pady=(6, 0))

                    # busqueda
        search_row = ctk.CTkFrame(toolbar_container, fg_color="transparent")
        search_row.pack(fill="x", pady=(0, 4))


        search_card = ctk.CTkFrame(search_row, fg_color=("#e8f0fe", "#1e2a4a"), corner_radius=10)
        search_card.pack(side="left")

        ctk.CTkLabel(
            search_card, text="",
            image=get_icon("search", 16),
            font=("Arial", 14), text_color=colors["text_secondary"]
        ).pack(side="left", padx=(10, 2))

        self.entry_busqueda = ctk.CTkEntry(
            search_card, placeholder_text="Buscar PDF, cédula, persona…",
            width=260, height=36, corner_radius=8, border_width=0,
            font=("Arial", 11), fg_color="transparent"
        )
        self.entry_busqueda.pack(side="left", padx=4, pady=6)
        self.entry_busqueda.bind("<Return>", lambda e: self.buscar_pdfs())
        self.entry_busqueda.bind("<KeyRelease>", self._debounced_search)

        ctk.CTkButton(
            search_card, text="Buscar",
            command=self.buscar_pdfs,
            fg_color=COLOR_SECONDARY, hover_color="#1565c0",
            font=("Arial", 10, "bold"),
            corner_radius=7, width=70, height=30
        ).pack(side="left", padx=(2, 8), pady=6)

                    # botones
        actions_row = ctk.CTkFrame(toolbar_container, fg_color="transparent")
        actions_row.pack(fill="x", pady=(0, 2))


        actions = [
            ("  Agregar",  self.mostrar_agregar_pdf,   COLOR_PRIMARY,   "#388E3C"),
            ("  Ver Todos", self.ver_pdfs,               COLOR_SECONDARY, "#1565c0"),
            ("  Detalles",  self.mostrar_detalles_pdf,   COLOR_WARNING,   "#E65100"),
            ("  Editar",    self.editar_pdf,             "#7B1FA2",       "#6A1B9A"),
            ("  Exportar",  self.exportar_pdf,           "#00897B",       "#00695C"),
            ("  Eliminar",  self.eliminar_pdf,           COLOR_ERROR,     "#B71C1C"),
        ]
        for text, cmd, fg, hover in actions:
            ctk.CTkButton(
                actions_row, text=text, command=cmd,
                fg_color=fg, hover_color=hover,
                text_color="white", font=("Arial", 10, "bold"),
                corner_radius=7, height=36, width=108
            ).pack(side="left", padx=4)

        # toggle lista/mosaico
        self._view_mode = "list"  # "list" | "mosaic"
        self._btn_toggle_view = ctk.CTkButton(
            actions_row, text="  Mosaico",
            command=self._toggle_view_mode,
            fg_color=("#546e7a", "#37474f"), hover_color="#455a64",
            text_color="white", font=("Arial", 10, "bold"),
            corner_radius=7, height=36, width=108
        )
        self._btn_toggle_view.pack(side="right", padx=4)

                         # treeview + preview
        content_area = ctk.CTkFrame(self.frame_principal, fg_color="transparent")
        content_area.pack(fill="both", expand=True, padx=14, pady=8)
        self._content_area = content_area  # referencia para toggle


        tree_frame = ctk.CTkFrame(content_area, fg_color=("#ffffff", "#1e2a4a"), corner_radius=10)
        tree_frame.pack(side="left", fill="both", expand=True)
        self._tree_frame = tree_frame  # referencia para toggle

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("ID", "Nombre", "Descripción", "Tamaño", "Fecha", "Cédula", "Nombres", "Empresa"),
            show="headings",
            height=14
        )

        for col, width in [("ID", 46), ("Nombre", 150), ("Descripción", 180),
                           ("Tamaño", 80), ("Fecha", 110), ("Cédula", 90), ("Nombres", 140), ("Empresa", 130)]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda e: self.abrir_pdf_doble_click())
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Button-3>", self._show_context_menu)

                        # menu contextual
        self._ctx_menu = tk.Menu(self.root, tearoff=0)
        self._ctx_menu.add_command(label="Abrir / Desencriptar", command=self.abrir_pdf_doble_click)
        self._ctx_menu.add_command(label="Ver Detalles",         command=self.mostrar_detalles_pdf)
        self._ctx_menu.add_command(label="Editar Metadatos",     command=self.editar_pdf)
        self._ctx_menu.add_command(label="Exportar PDF",         command=self.exportar_pdf)
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="Eliminar",             command=self.eliminar_pdf)

                        # mosaico
        self._mosaic_frame = ctk.CTkScrollableFrame(
            content_area, fg_color=("#f0f4ff", "#16213e"),
            corner_radius=10
        )
        
        self._mosaic_rows_cache = []  # cached data for mosaic
        self._mosaic_selected_id = None

                        # sidebar preview
        self._preview_panel = ctk.CTkFrame(
            content_area, fg_color=("#e8f0fe", "#1a2540"),
            corner_radius=10, width=230
        )
        self._preview_panel.pack(side="right", fill="y", padx=(8, 0))
        self._preview_panel.pack_propagate(False)

        ctk.CTkLabel(
            self._preview_panel, text="  Detalle del Documento",
            image=get_icon("clipboard", 16),
            compound="left",
            font=("Arial", 11, "bold"),
            text_color=colors["text_primary"]
        ).pack(pady=(14, 6), padx=10)

        sep = ctk.CTkFrame(self._preview_panel, height=1, fg_color=COLOR_SECONDARY)
        sep.pack(fill="x", padx=10)

        self._preview_name = ctk.CTkLabel(
            self._preview_panel, text="—",
            font=("Arial", 12, "bold"),
            text_color=COLOR_SECONDARY, wraplength=200
        )
        self._preview_name.pack(pady=(10, 4), padx=10)

        self._preview_info = ctk.CTkLabel(
            self._preview_panel, text="Selecciona un PDF\npara ver sus detalles",
            font=("Arial", 10),
            text_color=colors["text_secondary"],
            justify="left", wraplength=200
        )
        self._preview_info.pack(pady=4, padx=14, anchor="w")

        ctk.CTkButton(
            self._preview_panel,
            text="  Abrir",
            image=get_icon("folder-open", 16),
            compound="left",
            command=self.abrir_pdf_doble_click,
            fg_color=COLOR_SECONDARY, hover_color="#1565c0",
            font=("Arial", 10, "bold"),
            corner_radius=7, width=160, height=34
        ).pack(pady=(10, 4))

        ctk.CTkButton(
            self._preview_panel,
            text="  Exportar",
            command=self.exportar_pdf,
            fg_color="#00897B", hover_color="#00695C",
            font=("Arial", 10, "bold"),
            corner_radius=7, width=160, height=34
        ).pack(pady=4)

        ctk.CTkButton(
            self._preview_panel,
            text="  Editar",
            command=self.editar_pdf,
            fg_color="#7B1FA2", hover_color="#6A1B9A",
            font=("Arial", 10, "bold"),
            corner_radius=7, width=160, height=34
        ).pack(pady=4)

        ctk.CTkButton(
            self._preview_panel,
            text="  Eliminar",
            command=self.eliminar_pdf,
            fg_color=COLOR_ERROR, hover_color="#B71C1C",
            font=("Arial", 10, "bold"),
            corner_radius=7, width=160, height=34
        ).pack(pady=4)

                            # status bar
        self.status = ctk.CTkLabel(
            self.frame_principal,
            text="Listo",
            text_color=colors["text_primary"],
            font=("Arial", 10),
            anchor="w"
        )
        self.status.pack(side="bottom", fill="x", padx=16, pady=(2, 6))

    def _refresh_entry_theme(self, entry, colors, transparent=False):
        # normaliza colores de campos al alternar tema
        if not entry or not entry.winfo_exists():
            return
        kwargs = {
            "text_color": colors["text_primary"],
            "placeholder_text_color": colors["text_secondary"],
        }
        if not transparent:
            kwargs["fg_color"] = colors["bg_secondary"]
            kwargs["border_color"] = colors["secondary"]
        try:
            entry.configure(**kwargs)
        except Exception:
            pass

    def _refresh_intro_theme(self, colors):
        # intro siempre dark, independiente del tema elegido
        hint_active = "#5c6bc0"
        hint_inactive = "#2a2a5e"
        hidden_hint = "#0d0d2b"

        # forzar frame intro a dark
        if hasattr(self, "frame_intro") and self.frame_intro.winfo_exists():
            self.frame_intro.configure(fg_color=COLOR_BG_DARK)

        if hasattr(self, "_intro_card") and self._intro_card.winfo_exists():
            self._intro_card.configure(
                fg_color="#0d0d2b",
                bg_color="#050510"
            )
        if hasattr(self, "intro_text") and self.intro_text.winfo_exists():
            self.intro_text.configure(text_color="#e0e0e0")
        if hasattr(self, "_intro_subtitle") and self._intro_subtitle.winfo_exists():
            self._intro_subtitle.configure(text_color="#a0b4ff")
        if hasattr(self, "_intro_tech") and self._intro_tech.winfo_exists():
            self._intro_tech.configure(
                text_color=hint_active if getattr(self, "_intro_revealed", False) else hidden_hint
            )
        if hasattr(self, "_intro_hint") and self._intro_hint.winfo_exists():
            if getattr(self, "_intro_revealed", False):
                current = self._intro_hint.cget("text_color")
                self._intro_hint.configure(
                    text_color=hint_active if current in ("#5c6bc0", "#3f51b5") else hint_inactive
                )
            else:
                self._intro_hint.configure(text_color=hidden_hint)

    def actualizar_colores_dinamicos(self, refresh_data=True):
        # actualizar colores del tema
        colors = self.get_colors()
        auth_palette = self._get_auth_palette()

        self._refresh_intro_theme(colors)

        # colores de cards de acceso (bg_color coincide con gradiente padre)
        card_theme_map = [
            ("_card_inicial", ("#f5f7ff", "#1e2a4a"), ("#e3f2fd", "#1a1a2e")),
            ("_card_login",   ("#f5f7ff", "#1e2a4a"), ("#d8edda", "#0d2a54")),
            ("_card_2fa",     ("#f5f0ff", "#1e1a2e"), ("#ead5f5", "#30004e")),
            ("_card_reg",     ("#f0fff4", "#142e1e"), ("#d8edda", "#122e22")),
        ]
        for card_attr, fg_color, bg_color in card_theme_map:
            if hasattr(self, card_attr):
                card = getattr(self, card_attr)
                if card and card.winfo_exists():
                    card.configure(fg_color=fg_color, bg_color=bg_color)

        if hasattr(self, "_qr_card") and self._qr_card.winfo_exists():
            self._qr_card.configure(fg_color=("#ffffff", "#1a1a1a"))
        if hasattr(self, "_setup2fa_scroll") and self._setup2fa_scroll.winfo_exists():
            self._setup2fa_scroll.configure(bg_color=("#ffe082", "#3a2200"))

        # refresco de entries principales
        for entry_name in [
            "entry_usuario_login",
            "entry_contrasena_login",
            "entry_2fa_code",
            "entry_usuario_registro",
            "entry_contrasena_registro",
            "entry_confirm_2fa",
        ]:
            self._refresh_entry_theme(getattr(self, entry_name, None), colors)
        self._refresh_entry_theme(getattr(self, "entry_busqueda", None), colors, transparent=True)

        # actualiza colores status
        self.status.configure(text_color=colors["text_primary"])
        if hasattr(self, "_totp_timer_label") and self._totp_timer_label.winfo_exists():
            self._totp_timer_label.configure(text_color=colors["text_secondary"])
        if hasattr(self, "_initial_subtitle") and self._initial_subtitle.winfo_exists():
            self._initial_subtitle.configure(text_color=colors["secondary"])
        if hasattr(self, "_initial_footer") and self._initial_footer.winfo_exists():
            self._initial_footer.configure(text_color=colors["text_secondary"])
        if hasattr(self, "label_secret") and self.label_secret.winfo_exists():
            self.label_secret.configure(text_color=colors["warning"])
        if hasattr(self, "_backup_hint_2fa") and self._backup_hint_2fa.winfo_exists():
            self._backup_hint_2fa.configure(text_color=colors["warning"] if ctk.get_appearance_mode() == "Dark" else colors["secondary"])
        if hasattr(self, "_setup_warning_label") and self._setup_warning_label.winfo_exists():
            self._setup_warning_label.configure(text_color=colors["warning"] if ctk.get_appearance_mode() == "Dark" else colors["secondary"])
        if hasattr(self, "label_qr") and self.label_qr.winfo_exists():
            self.label_qr.configure(text_color=colors["text_primary"])

        # botones de pantallas de acceso
        button_specs = [
            ("_btn_initial_login", "btn_primary_fg", "btn_primary_hover"),
            ("_btn_login_next", "btn_primary_fg", "btn_primary_hover"),
            ("_btn_2fa_verify", "btn_primary_fg", "btn_primary_hover"),
            ("_btn_setup_confirm", "btn_primary_fg", "btn_primary_hover"),
            ("_btn_initial_register", "btn_secondary_fg", "btn_secondary_hover"),
            ("_btn_reg_submit", "btn_secondary_fg", "btn_secondary_hover"),
            ("_btn_copy_secret", "btn_secondary_fg", "btn_secondary_hover"),
            ("_btn_2fa_backup", "btn_warning_fg", "btn_warning_hover"),
            ("_btn_login_back", "btn_neutral_fg", "btn_neutral_hover"),
            ("_btn_2fa_back", "btn_neutral_fg", "btn_neutral_hover"),
            ("_btn_reg_back", "btn_neutral_fg", "btn_neutral_hover"),
        ]
        for btn_attr, fg_key, hover_key in button_specs:
            if hasattr(self, btn_attr):
                btn = getattr(self, btn_attr)
                if btn and btn.winfo_exists():
                    btn.configure(
                        fg_color=auth_palette[fg_key],
                        hover_color=auth_palette[hover_key],
                        text_color="white",
                    )

        if hasattr(self, "frame_principal") and self.frame_principal.winfo_exists():
            self.frame_principal.configure(fg_color=(COLOR_BG_LIGHT, COLOR_BG_DARK))
        if hasattr(self, "_preview_name") and self._preview_name.winfo_exists():
            self._preview_name.configure(text_color=colors["secondary"])
        if hasattr(self, "_preview_info") and self._preview_info.winfo_exists():
            self._preview_info.configure(text_color=colors["text_secondary"])
        if hasattr(self, "_preview_panel") and self._preview_panel.winfo_exists():
            self._preview_panel.configure(fg_color=("#e8f0fe", "#1a2540"))
        if hasattr(self, "_tree_frame") and self._tree_frame.winfo_exists():
            self._tree_frame.configure(fg_color=("#ffffff", "#1e2a4a"))
        if hasattr(self, "_mosaic_frame") and self._mosaic_frame.winfo_exists():
            self._mosaic_frame.configure(fg_color=("#f0f4ff", "#16213e"))

        # re-aplicar estilos treeview
        self._apply_treeview_style()
        if hasattr(self, "tree"):
            try:
                self.tree.update_idletasks()
            except Exception:
                pass
        if self.usuario_actual and refresh_data:
            self.cargar_dashboard()
            self.ver_pdfs()

        # refrescar labels de pantallas de acceso
        self._refresh_auth_labels(colors)

    
    def _refresh_auth_labels(self, colors):
        # recorrer labels de auth cards y actualizar text_color segun tema
        for card_attr in ("_card_inicial", "_card_login", "_card_2fa", "_card_reg"):
            card = getattr(self, card_attr, None)
            if not card or not card.winfo_exists():
                continue
            for child in card.winfo_children():
                if isinstance(child, ctk.CTkLabel):
                    try:
                        current = child.cget("text_color")
                        # no tocar labels con colores especiales (white, warning, fixed)
                        if current in ("white", "#FF9800", "#c8e6c9"):
                            continue
                        font_val = str(child.cget("font"))
                        if "bold" in font_val:
                            child.configure(text_color=colors["text_primary"])
                        else:
                            child.configure(text_color=colors["text_secondary"])
                    except Exception:
                        pass
                # recorrer subframes (ej: pw_row)
                elif isinstance(child, ctk.CTkFrame):
                    for sub in child.winfo_children():
                        if isinstance(sub, ctk.CTkLabel):
                            try:
                                font_val = str(sub.cget("font"))
                                if "bold" in font_val:
                                    sub.configure(text_color=colors["text_primary"])
                                else:
                                    sub.configure(text_color=colors["text_secondary"])
                            except Exception:
                                pass

        # setup 2fa scroll labels
        if hasattr(self, "_setup2fa_scroll") and self._setup2fa_scroll.winfo_exists():
            for child in self._setup2fa_scroll.winfo_children():
                if isinstance(child, ctk.CTkLabel):
                    try:
                        current = child.cget("text_color")
                        if current in ("white", "#FF9800", "#c8e6c9"):
                            continue
                        font_val = str(child.cget("font"))
                        if "bold" in font_val:
                            child.configure(text_color=colors["text_primary"])
                        else:
                            child.configure(text_color=colors["text_secondary"])
                    except Exception:
                        pass

    # navegacion
  

    def _hide_all_frames(self):
         # ocultar frames
        for f in [self.frame_intro, self.frame_inicial, self.frame_login,
                  self.frame_2fa, self.frame_setup_2fa, self.frame_principal,
                  self.frame_registro]:
            f.pack_forget()
            f.place_forget()
        self.root.update()

    # transicion fade

    def _fade_to(self, show_callback):
        # fade con overlay
        if getattr(self, '_fading', False):
            return
        self._fading = True

        # overlay oscuro
        overlay = tk.Frame(self.root, bg="#0a0a14")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.tkraise()

        # overlay → switch → quitar
        def _do_switch():
            self.root.update_idletasks()
            show_callback()
            self.root.update_idletasks()
            # Mantener overlay un momento para que el frame destino renderice
            self.root.after(80, _do_remove)

        def _do_remove():
            try:
                overlay.place_forget()
                overlay.destroy()
            except tk.TclError:
                pass
            self._fading = False

        # Dar un instante para que el overlay se muestre antes de switchear
        self.root.after(100, _do_switch)

    
    # HELPERS: TREEVIEW Estilismo y clasificacion
   

    def _apply_treeview_style(self):
                    # Aplica un estilo ttk dinamico al TreeView para que coincida con el tema activo
        style = ttk.Style()
        mode = ctk.get_appearance_mode()

        if mode == "Dark":
            bg        = "#2b2b2b"
            fg        = "#FFFFFF"
            even_bg   = "#2b2b2b"
            odd_bg    = "#333333"
            heading_bg = "#1a6b20"
            sel_bg    = "#2196F3"
            sel_fg    = "#FFFFFF"
        else:
            bg        = "#FFFFFF"
            fg        = "#004D40"
            even_bg   = "#FFFFFF"
            odd_bg    = "#F0F4F0"
            heading_bg = "#4CAF50"
            sel_bg    = "#BBDEFB"
            sel_fg    = "#004D40"

        style.theme_use("default")
        style.configure("Treeview",
            background=bg,
            foreground=fg,
            fieldbackground=bg,
            rowheight=28,
            font=("Arial", 10)
        )
        style.configure("Treeview.Heading",
            background=heading_bg,
            foreground="white",
            font=("Arial", 10, "bold"),
            relief="flat"
        )
        style.map("Treeview",
            background=[('selected', sel_bg)],
            foreground=[('selected', sel_fg)]
        )

        if hasattr(self, 'tree'):
            self.tree.tag_configure('evenrow', background=even_bg)
            self.tree.tag_configure('oddrow',  background=odd_bg)

    def _setup_treeview_sorting(self):
                     # permite ordenar haciendo clic en cada encabezado de columna de TreeView
        for col in ("ID", "Nombre", "Descripción", "Tamaño", "Fecha", "Cédula", "Nombres", "Empresa"):
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_column(c, False))

    def _sort_column(self, col, reverse):
                        # ordena las filas de TreeView por la columna especificada
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try:
            # intenta ordenar numericamente si es la columna ID, de lo contrario ordena alfabeticamente ignorando mayusculas
            if col == "ID":
                data.sort(key=lambda x: int(x[0]), reverse=reverse)
            else:
                data.sort(key=lambda x: x[0].lower(), reverse=reverse)
        except (ValueError, AttributeError):
            data.sort(key=lambda x: x[0], reverse=reverse)

        for index, (_, k) in enumerate(data):
            self.tree.move(k, '', index)
            self.tree.item(k, tags=('evenrow' if index % 2 == 0 else 'oddrow',))

        # cambiar la direccion de ordenacion en el siguiente clic.
        self.tree.heading(col, command=lambda: self._sort_column(col, not reverse))

    
    # HELPERS: Datos TREEVIEW 
   

    def _format_pdf_row(self, row):
        # formatea una tupla de fila de la base de datos para mostrarla en la vista de arbol
        return (
            row[0],
            row[1],
            row[2][:50] + "..." if row[2] and len(row[2]) > 50 else (row[2] or ""),
            format_size(row[3]),
            format_date_friendly(row[4]),
            row[5] or "",
            row[6] or "",
            row[7] or ""
        )

    def _populate_treeview(self, rows):
        # borra el TreeView e inserta filas formateadas con colores alternos
        self._mosaic_rows_cache = rows  # cache for mosaic
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, row in enumerate(rows):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.tree.insert('', 'end', values=self._format_pdf_row(row), tags=(tag,))
        # si estamos en modo mosaico, también pintar el mosaic
        if self._view_mode == "mosaic":
            self._populate_mosaic(rows)

    # ──────────────────────────────────────────────────────────────
    # VISTA MOSAICO  — improvement #12
    # ──────────────────────────────────────────────────────────────

    def _toggle_view_mode(self):
        """Alterna entre vista lista (Treeview) y vista mosaico (grid cards)."""
        if self._view_mode == "list":
            # Cambiar a mosaico
            self._view_mode = "mosaic"
            self._btn_toggle_view.configure(text="  Lista")

            self._tree_frame.pack_forget()
            self._preview_panel.pack_forget()

            self._mosaic_frame.pack(side="left", fill="both", expand=True)
            self._preview_panel.pack(side="right", fill="y", padx=(8, 0))

            self._populate_mosaic(self._mosaic_rows_cache)
        else:
            # Cambiar a lista
            self._view_mode = "list"
            self._btn_toggle_view.configure(text="  Mosaico")

            self._mosaic_frame.pack_forget()
            self._preview_panel.pack_forget()

            self._tree_frame.pack(side="left", fill="both", expand=True)
            self._preview_panel.pack(side="right", fill="y", padx=(8, 0))

    def _populate_mosaic(self, rows):
        """Rellena el frame scrollable con tarjetas de PDF estilizadas."""
        # Limpiar contenido anterior
        for w in self._mosaic_frame.winfo_children():
            w.destroy()

        colors = self.get_colors()
        is_dark = ctk.get_appearance_mode() == "Dark"

        if not rows:
            ctk.CTkLabel(
                self._mosaic_frame,
                text="No hay documentos para mostrar",
                font=("Arial", 13), text_color=colors["text_secondary"]
            ).pack(pady=40)
            return

        # Paleta de colores para los íconos de PDF
        icon_colors = ["#E53935", "#D81B60", "#8E24AA", "#5E35B1",
                       "#3949AB", "#1E88E5", "#00897B", "#43A047"]

        # Container grid
        grid = ctk.CTkFrame(self._mosaic_frame, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=4, pady=4)

        COLS = 4  # tarjetas por fila

        for i, row in enumerate(rows):
            pdf_id   = row[0]
            nombre   = row[1] or "Sin nombre"
            desc     = row[2][:40] + "…" if row[2] and len(row[2]) > 40 else (row[2] or "")
            tamano   = format_size(row[3])
            fecha    = format_date_friendly(row[4])
            cedula   = row[5] or ""
            persona  = row[6] or "—"
            empresa  = row[7] or ""

            r, c = divmod(i, COLS)
            color_accent = icon_colors[i % len(icon_colors)]

            card_bg = ("#ffffff", "#1e2a4a")  # CTk resuelve por tema
            card = ctk.CTkFrame(
                grid, fg_color=card_bg,
                corner_radius=12, border_width=2,
                border_color=(color_accent, color_accent)
            )
            card.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")

            # hacer que la columna expanda uniformemente
            grid.grid_columnconfigure(c, weight=1)

            # ── Ícono de PDF estilizado ──
            icon_frame = ctk.CTkFrame(card, fg_color=color_accent,
                                       corner_radius=8, height=60, width=60)
            icon_frame.pack(pady=(12, 4))
            icon_frame.pack_propagate(False)

            ctk.CTkLabel(
                icon_frame, text="",
                image=get_icon("file-text", 24),
                font=("Arial", 24), text_color="white"
            ).pack(expand=True)

            # extensión badge
            ext = nombre.rsplit(".", 1)[-1].upper() if "." in nombre else "PDF"
            ctk.CTkLabel(
                card, text=ext,
                font=("Arial", 8, "bold"),
                text_color="white",
                fg_color=color_accent,
                corner_radius=4, width=32, height=16
            ).pack(pady=(0, 4))

            # ── Nombre del archivo ──
            nombre_display = nombre[:22] + "…" if len(nombre) > 22 else nombre
            ctk.CTkLabel(
                card, text=nombre_display,
                font=("Arial", 10, "bold"),
                text_color=colors["text_primary"],
                wraplength=150
            ).pack(padx=8, pady=(0, 2))

            # ── Persona / Empresa ──
            if persona != "—":
                persona_txt = persona[:18] + "…" if len(persona) > 18 else persona
                ctk.CTkLabel(
                    card, text=f"{persona_txt}",
                    font=("Arial", 8),
                    text_color=colors["text_secondary"]
                ).pack(padx=8)

            if empresa:
                emp_txt = empresa[:18] + "…" if len(empresa) > 18 else empresa
                ctk.CTkLabel(
                    card, text=f"{emp_txt}",
                    font=("Arial", 8),
                    text_color=colors["text_secondary"]
                ).pack(padx=8)

            # ── Tamaño + Fecha ──
            meta_frame = ctk.CTkFrame(card, fg_color="transparent")
            meta_frame.pack(padx=8, pady=(4, 8))

            ctk.CTkLabel(
                meta_frame, text=f"{tamano}",
                font=("Arial", 8), text_color=colors["text_secondary"]
            ).pack(side="left", padx=(0, 6))

            ctk.CTkLabel(
                meta_frame, text=f"{fecha}",
                font=("Arial", 8), text_color=colors["text_secondary"]
            ).pack(side="left")

            # ── Interacciones: click selecciona, doble-click abre ──
            def _on_card_click(event, _id=pdf_id, _card=card, _row=row):
                self._mosaic_selected_id = _id
                # resaltar la card seleccionada y des-resaltar las demás
                for ch in grid.winfo_children():
                    try:
                        ch.configure(border_color=(
                            icon_colors[list(grid.winfo_children()).index(ch) % len(icon_colors)],
                            icon_colors[list(grid.winfo_children()).index(ch) % len(icon_colors)]
                        ))
                    except Exception:
                        pass
                _card.configure(border_color=("#FFD600", "#FFD600"))

                # Actualizar preview lateral
                self._preview_name.configure(text=_row[1] or "—")
                info_parts = []
                if _row[5]: info_parts.append(f"ID: {_row[5]}")
                if _row[6]: info_parts.append(f"Persona: {_row[6]}")
                if _row[7]: info_parts.append(f"Empresa: {_row[7]}")
                info_parts.append(f"Tamaño: {format_size(_row[3])}")
                info_parts.append(f"Fecha: {format_date_friendly(_row[4])}")
                info_parts.append(f"Cifrado: AES-256-GCM")
                self._preview_info.configure(text="\n".join(info_parts))

                # sincronizar selección en el Treeview (para que las acciones funcionen)
                for item in self.tree.get_children():
                    vals = self.tree.item(item)["values"]
                    if vals and int(vals[0]) == _id:
                        self.tree.selection_set(item)
                        break

            def _on_card_dblclick(event, _id=pdf_id):
                self._mosaic_selected_id = _id
                # sincronizar y abrir
                for item in self.tree.get_children():
                    vals = self.tree.item(item)["values"]
                    if vals and int(vals[0]) == _id:
                        self.tree.selection_set(item)
                        break
                self.abrir_pdf_doble_click()

            def _on_card_rclick(event, _id=pdf_id):
                self._mosaic_selected_id = _id
                for item in self.tree.get_children():
                    vals = self.tree.item(item)["values"]
                    if vals and int(vals[0]) == _id:
                        self.tree.selection_set(item)
                        break
                self._ctx_menu.tk_popup(event.x_root, event.y_root)

            # Bind a todos los hijos del card también
            def _bind_recursive(widget, _id=pdf_id, _card=card, _row=row):
                widget.bind("<Button-1>",
                            lambda e, i=_id, c=_card, r=_row: _on_card_click(e, i, c, r))
                widget.bind("<Double-1>",
                            lambda e, i=_id: _on_card_dblclick(e, i))
                widget.bind("<Button-3>",
                            lambda e, i=_id: _on_card_rclick(e, i))
                for child in widget.winfo_children():
                    _bind_recursive(child, _id, _card, _row)

            _bind_recursive(card)

    
    # HELPERS: BUSCA   DEBOUNCE
    

    def _debounced_search(self, event=None):
        #t riggers de busuqeda a 400ms despues de que el usuario deje de escribir, para evitar consultas excesivas a la base de datos mientras se escribe
        if self._search_timer:
            self.root.after_cancel(self._search_timer)
        self._search_timer = self.root.after(400, self.buscar_pdfs)

    
    # HELPERS: UTILIDADES UI 
   

    def _toggle_pw(self, entry, attr_name):
        # activa o desactiva la visibilidad de la contraseña en un widget de entrada
        current = getattr(self, attr_name, False)
        new_val = not current
        setattr(self, attr_name, new_val)
        entry.configure(show="" if new_val else "●")

    def _copy_totp_secret(self):
        #   copia el secret TOTP actual al portapapeles
        secret = self.label_secret.cget("text")
        if secret:
            self.root.clipboard_clear()
            self.root.clipboard_append(secret)
            Notification(self.root, "Copiado",
                         "Clave secreta copiada al portapapeles",
                         notification_type="success", duration=2000)

    def _start_totp_timer(self):
        # atualiza la etiqueta de cuenta regresiva TOTP cada segundo mientras el marco de 2FA esté visible
        import time

        def tick():
            if not self.root.winfo_exists():
                return
            remaining = 30 - (int(time.time()) % 30)
            if hasattr(self, '_totp_timer_label') and self._totp_timer_label.winfo_exists():
                color = "#4CAF50" if remaining > 10 else "#FF9800" if remaining > 5 else "#F44336"
                self._totp_timer_label.configure(
                    text=f"Código válido: {remaining}s",
                    text_color=color
                )
            self.root.after(1000, tick)

        tick()

    def _show_context_menu(self, event):
         # muestra el menu contextual del clic derecho en la vista de arbol
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            try:
                self._ctx_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self._ctx_menu.grab_release()

    def _on_tree_select(self, event=None):
        # actualiza el panel de vista previa cuando se selecciona una fila
        selected = self.tree.selection()
        if not selected:
            self._reset_preview_panel()
            return
        values = self.tree.item(selected[0])['values']
        if not values:
            return
        pdf_id, pdf_nombre, descripcion, tamano, fecha, cedula, nombres, empresa = values
        colors = self.get_colors()
        self._preview_name.configure(text=pdf_nombre)
        info = (
            f"{pdf_nombre}\n\n"
            f"Desc: {descripcion or '—'}\n\n"
            f"Tamaño: {tamano}\n"
            f"Fecha: {fecha}\n"
            f"Cédula: {cedula or '—'}\n"
            f"Persona: {nombres or '—'}\n"
            f"Empresa: {empresa or '—'}\n\n"
            f"AES-256-GCM Encriptado"
        )
        self._preview_info.configure(text=info)

    def _reset_preview_panel(self):
        # restablece el panel de vista previa a su estado predeterminado
        colors = self.get_colors()
        self._preview_name.configure(text="—")
        self._preview_info.configure(
            text="Selecciona un PDF\npara ver sus detalles"
        )

   
    # HELPERS: OPERACIONES PDF (devoluciones de llamada de subprocesos + limpieza de archivos temporales)
    

    def _save_pdf_to_db(self, datos_enc, tamano, nombre, descripcion,
                        cedula, nombres, empresa, usuario_actual, window):
        # delegado a pdf_manager.py
        self.pdf._save_to_db(datos_enc, tamano, nombre, descripcion,
                             cedula, nombres, empresa, usuario_actual, window)

    def _on_pdf_added(self, nombre, window):
        # delegado a pdf_manager.py
        self.pdf._on_added(nombre, window)

    def _on_pdf_add_error(self, error):
        # delegado a pdf_manager.py
        self.pdf._on_add_error(error)

    def _abrir_visor_pdf(self, pdf_bytes: bytes, nombre: str, window=None):
        # delegado a pdf_manager.py
        self.pdf._abrir_visor(pdf_bytes, nombre, window)

    def mostrar_inicial(self):
        # muestra la pantalla inicial con fade
        def _show():
            self._hide_all_frames()
            self.frame_inicial.pack(expand=True, fill="both")
        self._fade_to(_show)

    def mostrar_login(self):
        # muestra la pantalla de login con fade
        def _show():
            self._hide_all_frames()
            self.entry_usuario_login.delete(0, tk.END)
            self.entry_contrasena_login.delete(0, tk.END)
            self.frame_login.pack(expand=True, fill="both")
        self._fade_to(_show)

    def mostrar_registro(self):
        # muestra la pantalla de registro con fade
        def _show():
            self._hide_all_frames()
            self.entry_usuario_registro.delete(0, tk.END)
            self.entry_contrasena_registro.delete(0, tk.END)
            self.frame_registro.pack(expand=True, fill="both")
        self._fade_to(_show)

    def registrarse(self):
        # registrar usuario
        nombre = self.entry_usuario_registro.get().strip()
        contrasena = self.entry_contrasena_registro.get().strip()

        if not nombre or not contrasena:
            Notification(
                self.root, "Error",
                "Ingresa nombre de usuario y contraseña",
                notification_type="error"
            )
            return

        if len(nombre) < 3:
            Notification(
                self.root, "Error",
                "El nombre de usuario debe tener al menos 3 caracteres",
                notification_type="error"
            )
            return

        if len(contrasena) < 8:
            Notification(
                self.root, "Error",
                "La contraseña debe tener mínimo 8 caracteres",
                notification_type="error"
            )
            return

        score, label, _ = password_strength(contrasena)
        if score < 2:
            Notification(
                self.root, "Contraseña insegura",
                f"Fortaleza: {label}\n"
                "Requisitos: 8+ caracteres, mayúsculas,\nnúmeros y caracteres especiales (!@#$…)",
                notification_type="warning", duration=5000
            )
            return

        try:
            hash_pass = hash_contrasena(contrasena)
            self.cursor.execute(
                "INSERT INTO Usuarios (nombre, contrasena, fecha_creacion) VALUES (?, ?, ?)",
                (nombre, hash_pass, datetime.now().isoformat())
            )
            self.conn.commit()

            # derivar session key desde el salt del hash recién creado (nunca guardar la contraseña plana)
            parts = hash_pass.split(":")
            user_salt = parts[1] if len(parts) == 3 else nombre
            self._session_key = EncryptionManager.derive_session_key(contrasena, user_salt)

            self.usuario_nombre = nombre
            self.mostrar_setup_2fa()

            Notification(
                self.root, "Éxito",
                f"Usuario {nombre} registrado\nConfigurando 2FA…",
                notification_type="success"
            )
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                Notification(
                    self.root, "Error",
                    f"El usuario '{nombre}' ya existe",
                    notification_type="error"
                )
            else:
                Notification(self.root, "Error", str(e), notification_type="error")

    def login(self):
        # login paso 1
        nombre = self.entry_usuario_login.get().strip()
        contrasena = self.entry_contrasena_login.get().strip()

        if not nombre or not contrasena:
            Notification(
                self.root, "Error",
                "Ingresa nombre de usuario y contraseña",
                notification_type="error"
            )
            return

        # ver si esta bloqueada
        locked, secs = check_account_locked(self.cursor, nombre)
        if locked:
            mins = secs // 60 + 1
            Notification(
                self.root, "Cuenta bloqueada",
                f"Demasiados intentos fallidos.\nIntenta de nuevo en {mins} minuto(s).",
                notification_type="error", duration=5000
            )
            return

        try:
            self.cursor.execute(
                "SELECT id, contrasena, totp_enabled FROM Usuarios WHERE nombre = ?",
                (nombre,)
            )
            result = self.cursor.fetchone()

            if result:
                usuario_id, hash_stored, totp_enabled = result
                ok, needs_rehash = verify_contrasena(contrasena, hash_stored)

                if ok:
                    # rehash si es legacy
                    new_hash = None
                    if needs_rehash:
                        new_hash = hash_contrasena(contrasena)
                        self.cursor.execute(
                            "UPDATE Usuarios SET contrasena = ? WHERE id = ?",
                            (new_hash, usuario_id)
                        )
                        self.cursor.execute(
                            "INSERT INTO Auditoria (accion, pdf_id, usuario_id, fecha) "
                            "VALUES (?, NULL, ?, ?)",
                            ("Migración hash contraseña (SHA-256→PBKDF2)",
                             usuario_id, datetime.now().isoformat())
                        )
                        self.conn.commit()

                    reset_failed_attempts(self.cursor, self.conn, nombre)

                    # derivar session key
                    ref_hash = new_hash if new_hash else hash_stored
                    ref_parts = ref_hash.split(":") if ref_hash.startswith("pbkdf2:") else []
                    user_salt = ref_parts[1] if len(ref_parts) == 3 else nombre
                    session_key = EncryptionManager.derive_session_key(contrasena, user_salt)

                    # migrar ENC: a ENCK:
                    if totp_enabled:
                        self.cursor.execute(
                            "SELECT totp_secret, backup_codes FROM Usuarios WHERE id = ?",
                            (usuario_id,)
                        )
                        totp_row = self.cursor.fetchone()
                        if totp_row:
                            totp_enc, backup_enc = totp_row
                            migrated = False
                            if totp_enc and totp_enc.startswith("ENC:"):
                                plain    = EncryptionManager.decrypt_str(totp_enc, contrasena)
                                totp_enc = EncryptionManager.encrypt_str_with_key(plain, session_key)
                                migrated = True
                            if backup_enc and backup_enc.startswith("ENC:"):
                                plain      = EncryptionManager.decrypt_str(backup_enc, contrasena)
                                backup_enc = EncryptionManager.encrypt_str_with_key(plain, session_key)
                                migrated   = True
                            if migrated:
                                self.cursor.execute(
                                    "UPDATE Usuarios SET totp_secret = ?, backup_codes = ? WHERE id = ?",
                                    (totp_enc, backup_enc, usuario_id)
                                )
                                self.conn.commit()

                    # guardar session key
                    self._session_key   = session_key
                    self.usuario_actual = usuario_id
                    self.usuario_nombre = nombre

                    if totp_enabled:
                        # verificar token confianza
                        trust_hours = self.config.get("2fa_trust_hours", 0)
                        if trust_hours > 0:
                            local_tokens = self.config.get("trust_tokens", {})
                            local_token  = local_tokens.get(nombre)
                            if local_token and check_trust_token(
                                self.cursor, usuario_id, local_token
                            ):
                                # skip 2fa
                                self._audit("Login con token de confianza (2FA omitido)")
                                self.completar_login()
                                return

                        self._hide_all_frames()
                        self.entry_2fa_code.delete(0, tk.END)
                        self.frame_2fa.pack(expand=True, fill="both")
                        self.entry_2fa_code.focus()
                    else:
                        self.completar_login()
                else:
                    record_failed_attempt(self.cursor, self.conn, nombre)
                    self._audit("Login fallido: contraseña incorrecta", usuario_id=usuario_id)
                    locked2, secs2 = check_account_locked(self.cursor, nombre)
                    if locked2:
                        Notification(
                            self.root, "Cuenta bloqueada",
                            "Se bloqueó tu cuenta por múltiples intentos fallidos.\n"
                            f"Espera {secs2 // 60 + 1} min.",
                            notification_type="error", duration=5000
                        )
                    else:
                        Notification(
                            self.root, "Error",
                            "Contraseña incorrecta",
                            notification_type="error"
                        )
            else:
                Notification(
                    self.root, "Error",
                    "Usuario no encontrado",
                    notification_type="error"
                )
        except Exception as e:
            Notification(self.root, "Error", str(e), notification_type="error")

    def mostrar_setup_2fa(self):
        # setup 2fa
        self.totp_secret = pyotp.random_base32()
        totp = pyotp.totp.TOTP(self.totp_secret)
        totp_uri = totp.provisioning_uri(
            name=self.usuario_nombre,
            issuer_name='DatenJäger'
        )

        qr = qrcode.QRCode(version=1, box_size=8, border=4)
        qr.add_data(totp_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        img = img.resize((220, 220), Image.LANCZOS)

        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(220, 220))
        self.label_qr.configure(image=ctk_img, text="")
        self.label_qr.image = ctk_img

        self.label_secret.configure(text=self.totp_secret)

        self._hide_all_frames()
        self.frame_setup_2fa.pack(expand=True, fill="both")
        self.entry_confirm_2fa.focus()

    def confirmar_setup_2fa(self):
        # confirmar 2fa
        codigo = self.entry_confirm_2fa.get().strip()

        if not codigo or len(codigo) != 6:
            Notification(
                self.root, "Error",
                "Ingresa un código válido de 6 dígitos",
                notification_type="error"
            )
            return

        try:
            totp = pyotp.TOTP(self.totp_secret)

            if totp.verify(codigo):
                backup_codes = [f"{random.randint(100000, 999999)}" for _ in range(5)]
                backup_codes_str = ",".join(backup_codes)

                # cifrar con session key
                secret_enc   = EncryptionManager.encrypt_str_with_key(self.totp_secret,  self._session_key)
                backups_enc  = EncryptionManager.encrypt_str_with_key(backup_codes_str, self._session_key)

                self.cursor.execute(
                    "UPDATE Usuarios SET totp_secret = ?, totp_enabled = 1, backup_codes = ? WHERE nombre = ?",
                    (secret_enc, backups_enc, self.usuario_nombre)
                )
                self.conn.commit()

                # mostrar codigos respaldo
                self._mostrar_codigos_respaldo(backup_codes)
                self._audit("Configuración 2FA completada")

                
                Notification(
                    self.root, "2FA Configurado",
                    "Autenticación 2FA activada correctamente",
                    notification_type="success"
                )

                self.mostrar_login()
            else:
                Notification(
                    self.root, "Error",
                    "El código es incorrecto o ha expirado",
                    notification_type="error"
                )
        except Exception as e:
            Notification(self.root, "Error", str(e), notification_type="error")

    def _mostrar_codigos_respaldo(self, backup_codes):
            # ventana codigos respaldo
        colors = self.get_colors()
        win = ctk.CTkToplevel(self.root)
        win.title("Códigos de Respaldo")
        win.geometry("440x420")
        win.resizable(False, False)
        win.transient(self.root)
        win.configure(fg_color=colors["bg_secondary"])
        win.withdraw()  # ocultar hasta que el contenido esté listo

        def _build():
            ctk.CTkLabel(
                win, text="Guarda tus Códigos de Respaldo",
                font=("Arial", 16, "bold"),
                text_color=COLOR_WARNING
            ).pack(pady=(20, 8))

            ctk.CTkLabel(
                win,
                text="Usa estos códigos si pierdes acceso a tu\naplicación autenticadora. Guárdalos en un lugar seguro.",
                font=("Arial", 11),
                text_color=colors["text_secondary"],
                justify="center"
            ).pack(padx=20)

            codes_frame = ctk.CTkFrame(win, fg_color=("#f5f5f5", "#1e1e1e"),
                                        corner_radius=10, border_width=1,
                                        border_color=("#d0d8e8", "#2a3a5e"))
            codes_frame.pack(padx=30, pady=12, fill="x")

            for code in backup_codes:
                ctk.CTkLabel(
                    codes_frame, text=f"  {code}",
                    font=("Arial", 15, "bold"),
                    text_color=COLOR_WARNING
                ).pack(pady=4)

            def copiar_todos():
                texto = "\n".join(backup_codes)
                win.clipboard_clear()
                win.clipboard_append(texto)
                Notification(win, "Copiado", "Códigos copiados al portapapeles",
                             notification_type="success", duration=2000)

            ctk.CTkButton(
                win, text="  Copiar todos",
                image=get_icon("clipboard", 14),
                compound="left",
                command=copiar_todos,
                fg_color=COLOR_SECONDARY, hover_color="#1565c0",
                text_color="white", font=("Arial", 11, "bold"),
                corner_radius=8, width=200, height=36
            ).pack(pady=8)

            ctk.CTkButton(
                win, text="  Entendido",
                image=get_icon("check-circle", 16),
                compound="left",
                command=win.destroy,
                fg_color=COLOR_PRIMARY, hover_color="#388E3C",
                text_color="white", font=("Arial", 12, "bold"),
                corner_radius=8, width=200, height=40
            ).pack(pady=(0, 20))

            win.update_idletasks()
            self._show_modal_window(win)

        win.after(250, _build)  # esperar a que CTkToplevel termine su init interno
        win.wait_window()

    def verificar_2fa(self):
        # verificar 2fa
        codigo = self.entry_2fa_code.get().strip()

        if not codigo or len(codigo) != 6:
            Notification(
                self.root,
                "Error",
                "Ingresa un código válido de 6 dígitos",
                notification_type="error"
            )
            return

        try:
            self.cursor.execute(
                "SELECT totp_secret FROM Usuarios WHERE id = ?",
                (self.usuario_actual,)
            )
            result = self.cursor.fetchone()

            if result:
                # descifrar secret
                totp_secret = EncryptionManager.decrypt_str_with_key(result[0], self._session_key)
                totp = pyotp.TOTP(totp_secret)

                if totp.verify(codigo):
                    self._audit("2FA verificado exitosamente")
                    self._save_trust_token()
                    self.completar_login()
                else:
                    self._audit("2FA fallido: código incorrecto o expirado")
                    Notification(
                        self.root,
                        "Error",
                        "El código es incorrecto o ha expirado",
                        notification_type="error"
                    )
            else:
                Notification(
                    self.root,
                    "Error",
                    "Usuario no encontrado",
                    notification_type="error"
                )
        except Exception as e:
            Notification(
                self.root,
                "Error",
                str(e),
                notification_type="error"
            )

    def usar_codigo_respaldo(self):
        # codigo de respaldo
        from tkinter.simpledialog import askstring
        codigo = askstring(
            "Código de Respaldo",
            "Ingresa tu código de respaldo de 6 dígitos:",
            parent=self.root
        )

        if not codigo:
            return

        try:
            self.cursor.execute(
                "SELECT backup_codes FROM Usuarios WHERE id = ?",
                (self.usuario_actual,)
            )
            result = self.cursor.fetchone()

            if result and result[0]:
                # descifrar codigos
                codes_raw    = EncryptionManager.decrypt_str_with_key(result[0], self._session_key)
                backup_codes = codes_raw.split(",")

                if codigo in backup_codes:
                    backup_codes.remove(codigo)
                    backup_codes_str = ",".join(backup_codes)

                    # recifrar lista
                    backups_enc = EncryptionManager.encrypt_str_with_key(backup_codes_str, self._session_key)
                    self.cursor.execute(
                        "UPDATE Usuarios SET backup_codes = ? WHERE id = ?",
                        (backups_enc, self.usuario_actual)
                    )
                    self.conn.commit()
                    self._audit("Login con código de respaldo")
                    self._save_trust_token()

                    Notification(
                        self.root,
                        "Código Aceptado",
                        "Login completado con código de respaldo",
                        notification_type="success"
                    )

                    self.completar_login()
                else:
                    self._audit("Código de respaldo inválido")
                    Notification(
                        self.root,
                        "Error",
                        "El código de respaldo es inválido",
                        notification_type="error"
                    )
        except Exception as e:
            Notification(
                self.root,
                "Error",
                str(e),
                notification_type="error"
            )

    # configuracion de cuenta

    def abrir_configuracion_cuenta(self):
        # abrir config cuenta
        if not self.usuario_actual:
            return

        colors = self.get_colors()
        win = ctk.CTkToplevel(self.root)
        win.title("Configuración de Cuenta")
        win.geometry("520x560")
        win.resizable(False, False)
        win.transient(self.root)
        win.configure(fg_color=colors["bg_secondary"])
        win.withdraw()

        def _build():
            ctk.CTkLabel(
                win, text=f"  {self.usuario_nombre}",
                image=get_icon("user", 20),
                compound="left",
                font=("Arial", 17, "bold"),
                text_color=colors["text_primary"]
            ).pack(pady=(20, 4))

            ctk.CTkLabel(
                win, text="Configuración de Cuenta",
                font=("Arial", 11), text_color=colors["text_secondary"]
            ).pack(pady=(0, 14))

            tabs = ctk.CTkTabview(win, width=480, height=440, corner_radius=12)
            tabs.pack(padx=18, pady=(0, 18), fill="both", expand=True)

            tabs.add("Contraseña")
            tabs.add("Códigos 2FA")
            tabs.add("Confianza")

            self._build_tab_contrasena(tabs.tab("Contraseña"), win, colors)
            self._build_tab_codigos(tabs.tab("Códigos 2FA"), colors)
            self._build_tab_confianza(tabs.tab("Confianza"), colors)

            win.update_idletasks()
            win.deiconify()
            win.lift()
            win.focus_force()

        win.after(200, _build)

    def _build_tab_contrasena(self, parent, win, colors):
        # tab cambiar contraseña
        ctk.CTkLabel(
            parent, text="Cambiar Contraseña",
            font=("Arial", 13, "bold"), text_color=colors["text_primary"]
        ).pack(pady=(14, 10))


        ctk.CTkLabel(parent, text="Contraseña actual",
                     font=("Arial", 10, "bold"), text_color=colors["text_secondary"]
                     ).pack(anchor="w", padx=24)
        entry_actual = ctk.CTkEntry(
            parent, placeholder_text="Tu contraseña actual",
            width=360, height=38, show="●", font=("Arial", 11), corner_radius=8
        )
        entry_actual.pack(pady=(2, 8))


        ctk.CTkLabel(parent, text="Nueva contraseña",
                     font=("Arial", 10, "bold"), text_color=colors["text_secondary"]
                     ).pack(anchor="w", padx=24)
        entry_nueva = ctk.CTkEntry(
            parent, placeholder_text="Mínimo 8 caracteres",
            width=360, height=38, show="●", font=("Arial", 11), corner_radius=8
        )
        entry_nueva.pack(pady=(2, 2))

        from ui_components import PasswordStrengthBar
        pw_bar = PasswordStrengthBar(parent)
        pw_bar.pack(fill="x", padx=24, pady=(2, 6))
        entry_nueva.bind("<KeyRelease>", lambda e: pw_bar.update(entry_nueva.get()))


        ctk.CTkLabel(parent, text="Confirmar nueva contraseña",
                     font=("Arial", 10, "bold"), text_color=colors["text_secondary"]
                     ).pack(anchor="w", padx=24)
        entry_confirm = ctk.CTkEntry(
            parent, placeholder_text="Repite la nueva contraseña",
            width=360, height=38, show="●", font=("Arial", 11), corner_radius=8
        )
        entry_confirm.pack(pady=(2, 8))

        # codigo totp
        ctk.CTkLabel(parent, text="Código 2FA del autenticador",
                     font=("Arial", 10, "bold"), text_color=colors["text_secondary"]
                     ).pack(anchor="w", padx=24)
        entry_totp = ctk.CTkEntry(
            parent, placeholder_text="Código de 6 dígitos",
            width=360, height=38, font=("Arial", 14, "bold"),
            justify="center", corner_radius=8
        )
        entry_totp.pack(pady=(2, 12))

        def aplicar():
            pw_actual  = entry_actual.get()
            pw_nueva   = entry_nueva.get()
            pw_confirm = entry_confirm.get()
            totp_code  = entry_totp.get().strip()


            if not all([pw_actual, pw_nueva, pw_confirm, totp_code]):
                Notification(win, "Campos incompletos",
                             "Completa todos los campos", notification_type="warning")
                return
            if pw_nueva != pw_confirm:
                Notification(win, "Error", "Las nuevas contraseñas no coinciden",
                             notification_type="error")
                return
            score, label, _ = password_strength(pw_nueva)
            if score < 2:
                Notification(win, "Contraseña débil",
                             f"Fortaleza: {label}. Usa mayúsculas, números y símbolos.",
                             notification_type="warning")
                return

            try:
                # verificar actual
                self.cursor.execute(
                    "SELECT contrasena, totp_enabled, totp_secret FROM Usuarios WHERE id = ?",
                    (self.usuario_actual,)
                )
                row = self.cursor.fetchone()
                if not row:
                    return
                hash_stored, totp_enabled, totp_enc = row
                ok, _ = verify_contrasena(pw_actual, hash_stored)
                if not ok:
                    Notification(win, "Error", "Contraseña actual incorrecta",
                                 notification_type="error")
                    return

                # verificar totp
                if not totp_enabled or not totp_enc:
                    Notification(win, "Error",
                                 "El 2FA no está configurado. Configúralo primero.",
                                 notification_type="error")
                    return
                totp_secret = EncryptionManager.decrypt_str_with_key(
                    totp_enc, self._session_key
                )
                if not pyotp.TOTP(totp_secret).verify(totp_code):
                    Notification(win, "Código inválido",
                                 "El código del autenticador es incorrecto o expiró",
                                 notification_type="error")
                    return

                # rehash y nueva key
                new_hash  = hash_contrasena(pw_nueva)
                parts     = new_hash.split(":")
                new_salt  = parts[1] if len(parts) == 3 else self.usuario_nombre
                new_key   = EncryptionManager.derive_session_key(pw_nueva, new_salt)

                # recifrar datos
                self.cursor.execute(
                    "SELECT backup_codes FROM Usuarios WHERE id = ?",
                    (self.usuario_actual,)
                )
                backup_enc_old = self.cursor.fetchone()[0]
                new_totp_enc   = EncryptionManager.encrypt_str_with_key(totp_secret, new_key)
                new_backup_enc = backup_enc_old
                if backup_enc_old:
                    backup_plain   = EncryptionManager.decrypt_str_with_key(
                        backup_enc_old, self._session_key
                    )
                    new_backup_enc = EncryptionManager.encrypt_str_with_key(
                        backup_plain, new_key
                    )

                # guardar en db
                self.cursor.execute(
                    "UPDATE Usuarios SET contrasena = ?, totp_secret = ?, backup_codes = ? "
                    "WHERE id = ?",
                    (new_hash, new_totp_enc, new_backup_enc, self.usuario_actual)
                )
                clear_trust_token(self.cursor, self.conn, self.usuario_actual)
                self.conn.commit()

                # limpiar token local
                tokens = self.config.get("trust_tokens", {})
                tokens.pop(self.usuario_nombre, None)
                self.config.set("trust_tokens", tokens)

                # actualizar key
                self._session_key = new_key
                self._audit("Cambio de contraseña")

                Notification(self.root, "Contraseña cambiada",
                             "Tu contraseña fue actualizada correctamente.\n"
                             "El token de confianza fue invalidado.",
                             notification_type="success", duration=4000)
                win.destroy()

            except Exception as e:
                Notification(win, "Error", str(e), notification_type="error")

        ctk.CTkButton(
            parent, text="  Cambiar Contraseña",
            image=get_icon("check-circle", 18),
            compound="left",
            command=aplicar,
            fg_color=COLOR_PRIMARY, hover_color="#388E3C",
            text_color="white", font=("Arial", 12, "bold"),
            width=360, height=42, corner_radius=8
        ).pack(pady=4)

    def _build_tab_codigos(self, parent, colors):
        # tab codigos respaldo
        ctk.CTkLabel(
            parent, text="Códigos de Respaldo 2FA",
            font=("Arial", 13, "bold"), text_color=colors["text_primary"]
        ).pack(pady=(14, 4))
        ctk.CTkLabel(
            parent,
            text="Úsalos si no tienes acceso a tu autenticador.\nCada código es de un solo uso.",
            font=("Arial", 10), text_color=colors["text_secondary"], justify="center"
        ).pack(pady=(0, 10))

        codes_frame = ctk.CTkFrame(parent, fg_color=colors["bg_card"], corner_radius=10)
        codes_frame.pack(padx=24, fill="x")

        self._refresh_backup_codes_display(codes_frame, colors)

        def copiar():
            try:
                self.cursor.execute(
                    "SELECT backup_codes FROM Usuarios WHERE id = ?", (self.usuario_actual,)
                )
                row = self.cursor.fetchone()
                if row and row[0]:
                    plain = EncryptionManager.decrypt_str_with_key(row[0], self._session_key)
                    self.root.clipboard_clear()
                    self.root.clipboard_append(plain.replace(",", "\n"))
                    Notification(parent, "Copiado", "Códigos copiados al portapapeles",
                                 notification_type="success", duration=2000)
            except Exception as e:
                Notification(parent, "Error", str(e), notification_type="error")

        def regenerar():
            dlg = ConfirmDialog(
                parent, "Regenerar Códigos",
                "¿Generar nuevos códigos de respaldo?\nLos actuales quedarán inválidos.",
                confirm_text="Regenerar", danger=True
            )
            if not dlg.result:
                return
            try:
                nuevos = [f"{random.randint(100000, 999999)}" for _ in range(5)]
                enc    = EncryptionManager.encrypt_str_with_key(
                    ",".join(nuevos), self._session_key
                )
                self.cursor.execute(
                    "UPDATE Usuarios SET backup_codes = ? WHERE id = ?",
                    (enc, self.usuario_actual)
                )
                self.conn.commit()
                self._audit("Regeneración de códigos de respaldo")
                self._refresh_backup_codes_display(codes_frame, colors)
                Notification(parent, "Códigos regenerados",
                             "Guarda los nuevos códigos en un lugar seguro.",
                             notification_type="success")
            except Exception as e:
                Notification(parent, "Error", str(e), notification_type="error")

        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(pady=14)
        ctk.CTkButton(btn_row, text="  Copiar todos",
                image=get_icon("clipboard", 14),
                compound="left", command=copiar,
                      fg_color=COLOR_SECONDARY, hover_color="#1565c0",
                      text_color="white", font=("Arial", 11, "bold"),
                      width=166, height=36, corner_radius=8).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="  Regenerar", command=regenerar,
                      fg_color=COLOR_WARNING, hover_color="#F57C00",
                      text_color="white", font=("Arial", 11, "bold"),
                      width=166, height=36, corner_radius=8).pack(side="left", padx=6)

    def _refresh_backup_codes_display(self, codes_frame, colors):
        # refrescar codigos
        for w in codes_frame.winfo_children():
            w.destroy()
        try:
            self.cursor.execute(
                "SELECT backup_codes FROM Usuarios WHERE id = ?", (self.usuario_actual,)
            )
            row = self.cursor.fetchone()
            if row and row[0]:
                plain  = EncryptionManager.decrypt_str_with_key(row[0], self._session_key)
                codigos = [c for c in plain.split(",") if c.strip()]
                for c in codigos:
                    ctk.CTkLabel(
                        codes_frame, text=f"  {c}",
                        font=("Arial", 13, "bold"), text_color=COLOR_WARNING
                    ).pack(pady=3)
                ctk.CTkLabel(
                    codes_frame,
                    text=f"{len(codigos)} código(s) disponible(s)",
                    font=("Arial", 9), text_color=colors["text_secondary"]
                ).pack(pady=(0, 6))
            else:
                ctk.CTkLabel(
                    codes_frame, text="Sin códigos de respaldo registrados",
                    font=("Arial", 10), text_color=colors["text_secondary"]
                ).pack(pady=14)
        except Exception:
            pass

    def _build_tab_confianza(self, parent, colors):
        # tab confianza
        ctk.CTkLabel(
            parent, text="Confianza de Dispositivo",
            font=("Arial", 13, "bold"), text_color=colors["text_primary"]
        ).pack(pady=(14, 6))
        ctk.CTkLabel(
            parent,
            text="Tras verificar el 2FA, este dispositivo\n"
                 "no solicitará el código durante el período elegido.",
            font=("Arial", 10), text_color=colors["text_secondary"], justify="center"
        ).pack(pady=(0, 18))

        opciones  = ["Siempre solicitar", "24 horas", "48 horas", "7 días"]
        horas_map = {"Siempre solicitar": 0, "24 horas": 24, "48 horas": 48, "7 días": 168}
        horas_inv = {v: k for k, v in horas_map.items()}

        actual_horas = self.config.get("2fa_trust_hours", 0)
        actual_texto = horas_inv.get(actual_horas, "Siempre solicitar")

        selector = ctk.CTkOptionMenu(
            parent, values=opciones,
            width=280, height=40, corner_radius=8,
            font=("Arial", 12), fg_color=COLOR_SECONDARY,
            button_color="#1565c0", button_hover_color="#0d47a1"
        )
        selector.set(actual_texto)
        selector.pack(pady=6)

        info_label = ctk.CTkLabel(
            parent, text="",
            font=("Arial", 10), text_color=colors["text_secondary"], wraplength=340
        )
        info_label.pack(pady=8)

        def guardar_trust():
            elegido = selector.get()
            horas   = horas_map.get(elegido, 0)
            self.config.set("2fa_trust_hours", horas)
            if horas == 0:
                # invalidar token
                clear_trust_token(self.cursor, self.conn, self.usuario_actual)
                tokens = self.config.get("trust_tokens", {})
                tokens.pop(self.usuario_nombre, None)
                self.config.set("trust_tokens", tokens)
                info_label.configure(text="Siempre se solicitará el código 2FA.")
            else:
                info_label.configure(
                    text=f"Guardado. El código 2FA no se pedirá durante {elegido} "
                         "tras la próxima verificación exitosa."
                )

        ctk.CTkButton(
            parent, text="  Guardar preferencia",
            image=get_icon("save", 18),
            compound="left",
            command=guardar_trust,
            fg_color=COLOR_PRIMARY, hover_color="#388E3C",
            text_color="white", font=("Arial", 12, "bold"),
            width=280, height=42, corner_radius=8
        ).pack(pady=6)

        ctk.CTkLabel(
            parent,
            text="Cambiar la contraseña invalida\nautomáticamente el token de confianza.",
            font=("Arial", 9), text_color=COLOR_WARNING, justify="center"
        ).pack(pady=(14, 0))

    def _save_trust_token(self):
        # generar token confianza
        trust_hours = self.config.get("2fa_trust_hours", 0)
        if trust_hours <= 0 or not self.usuario_actual:
            return
        token   = secrets.token_hex(32)
        expires = (datetime.now() + timedelta(hours=trust_hours)).isoformat()
        set_trust_token(self.cursor, self.conn, self.usuario_actual, token, expires)
        tokens  = self.config.get("trust_tokens", {})
        tokens[self.usuario_nombre] = token
        self.config.set("trust_tokens", tokens)

    def _audit(self, accion: str, pdf_id=None, usuario_id=None):
        # delega al modulo de auditoria
        self.auditoria.registrar(accion, pdf_id, usuario_id)

    # timeout inactividad

    def _start_idle_tracking(self):
        # iniciar tracking inactividad
        self._stop_idle_tracking()
        timeout_s = self.config.get("session_timeout_minutes", 10) * 60
        self._idle_timeout_ms  = int(timeout_s * 1000)
        self._idle_warning_ms  = int(max(timeout_s - 30, 5) * 1000)
        
        for event in ("<Motion>", "<KeyPress>", "<ButtonPress>"):
            bid = self.root.bind(event, self._reset_idle_timer, add="+")
            self._idle_bind_ids.append((event, bid))
        self._schedule_idle_timers()

    def _stop_idle_tracking(self):
        # parar tracking
        if self._idle_timer:
            self.root.after_cancel(self._idle_timer)
            self._idle_timer = None
        if self._idle_warning_timer:
            self.root.after_cancel(self._idle_warning_timer)
            self._idle_warning_timer = None
        for event, bid in self._idle_bind_ids:
            try:
                self.root.unbind(event, bid)
            except Exception:
                pass
        self._idle_bind_ids = []

    def _schedule_idle_timers(self):
        # reprogramar timers
        if self._idle_warning_timer:
            self.root.after_cancel(self._idle_warning_timer)
        if self._idle_timer:
            self.root.after_cancel(self._idle_timer)
        self._idle_warning_timer = self.root.after(
            self._idle_warning_ms, self._idle_warning
        )
        self._idle_timer = self.root.after(
            self._idle_timeout_ms, self._idle_logout
        )

    def _reset_idle_timer(self, event=None):
        # reset timer
        if not self.usuario_actual:
            return
        self._schedule_idle_timers()

    def _idle_warning(self):
        # warning 30s
        if not self.usuario_actual:
            return
        Notification(
            self.root,
            "Sesión por expirar",
            "Sin actividad detectada.\nLa sesión se cerrará en 30 segundos.",
            notification_type="warning",
            duration=28000
        )

    def _idle_logout(self):
        # logout por inactividad
        if not self.usuario_actual:
            return
        self._stop_idle_tracking()
        self._audit("Logout automático por inactividad")
        nombre = self.usuario_nombre
        self.usuario_actual = None
        self.usuario_nombre = None
        self._session_key   = None
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._reset_preview_panel()
        self.mostrar_inicial()
        Notification(
            self.root, "Sesión expirada",
            f"La sesión de {nombre} se cerró automáticamente\npor inactividad.",
            notification_type="warning", duration=5000
        )

    def completar_login(self):
         # completar login
        self._hide_all_frames()
        self.frame_principal.pack(expand=True, fill="both")
        colors = self.get_colors()
        self.status.configure(text=f"Sesión activa: {self.usuario_nombre}",
                              text_color=colors["text_primary"])
        
        if hasattr(self, '_user_badge'):
            self._user_badge.configure(text=f"  {self.usuario_nombre} ", image=get_icon("user", 14), compound="left")
        Notification(
            self.root,
            "Sesión Iniciada",
            f"Bienvenido, {self.usuario_nombre}!\n2FA verificado – AES-256-GCM activo",
            notification_type="success",
            duration=3000
        )
        self._audit("Login exitoso")
        self.cargar_dashboard()
        self.ver_pdfs()
        self._start_idle_tracking()

    def _logout(self):
            # logout
        dlg = ConfirmDialog(
            self.root,
            "  Cerrar Sesión",
            f"¿Deseas cerrar la sesión de {self.usuario_nombre}?",
            confirm_text="Cerrar Sesión",
            cancel_text="Cancelar",
            danger=False
        )
        if dlg.result:
            self._stop_idle_tracking()
            self._audit("Logout")
            self.usuario_actual  = None
            self.usuario_nombre  = None
            self._session_key    = None
            
            for item in self.tree.get_children():
                self.tree.delete(item)
            self._reset_preview_panel()
            self.mostrar_inicial()
            Notification(
                self.root, "Sesión cerrada",
                "Has cerrado sesión correctamente",
                notification_type="info", duration=2500
            )

    def cargar_dashboard(self):
         # cargar dashboard
        for widget in self.dashboard_container.winfo_children():
            widget.destroy()

        dashboard = DashboardWidget(self.dashboard_container, self.cursor, self.usuario_actual)
        dashboard.pack(fill="both", padx=20)

    def _obtener_datos_reporte_dashboard(self):
        # datos para el reporte
        from database import format_size

        with self._db_lock:
            self.cursor.execute(
                """
                SELECT p.id, p.nombre, p.descripcion, p.tamano,
                       p.fecha_subida, pe.cedula, pe.nombres, pe.empresa
                FROM PDFs p
                LEFT JOIN Personas pe ON p.persona_id = pe.id
                WHERE p.usuario_id = ?
                ORDER BY p.fecha_subida DESC
                """,
                (self.usuario_actual,)
            )
            rows = self.cursor.fetchall()

            self.cursor.execute(
                "SELECT COUNT(*), COALESCE(SUM(tamano), 0) FROM PDFs WHERE usuario_id = ?",
                (self.usuario_actual,)
            )
            total_pdfs, total_size = self.cursor.fetchone()
            total_pdfs = total_pdfs or 0
            total_size = total_size or 0

            self.cursor.execute(
                "SELECT COUNT(DISTINCT persona_id) FROM PDFs WHERE usuario_id = ?",
                (self.usuario_actual,)
            )
            total_personas = self.cursor.fetchone()[0] or 0

            self.cursor.execute(
                """
                SELECT COALESCE(pe.empresa, 'Sin empresa') AS empresa, COUNT(*) AS total
                FROM PDFs p
                LEFT JOIN Personas pe ON p.persona_id = pe.id
                WHERE p.usuario_id = ?
                GROUP BY COALESCE(pe.empresa, 'Sin empresa')
                ORDER BY total DESC, empresa ASC
                """,
                (self.usuario_actual,)
            )
            empresas_data = self.cursor.fetchall()

        stats = {
            "total_pdfs": total_pdfs,
            "total_size_str": format_size(total_size),
            "total_personas": total_personas,
            "total_empresas": len(empresas_data),
            "empresas_data": empresas_data,
        }
        return rows, stats

    def exportar_reporte_dashboard(self, formato="pdf"):
        # exportar reporte
        if not self.usuario_actual:
            Notification(self.root, "Error", "No hay sesión activa.",
                         notification_type="error")
            return

        formato = (formato or "pdf").lower().strip()
        if formato not in ("pdf", "csv"):
            formato = "pdf"

        ext = f".{formato}"
        destino = filedialog.asksaveasfilename(
            defaultextension=ext,
            initialfile=f"reporte_dashboard_{datetime.now().strftime('%Y%m%d_%H%M')}{ext}",
            filetypes=[(f"Archivo {formato.upper()}", f"*{ext}"), ("Todos", "*.*")]
        )
        if not destino:
            return

        self.progress_bar.start(f"Generando reporte {formato.upper()}...")
        try:
            rows, stats = self._obtener_datos_reporte_dashboard()
            if formato == "csv":
                ReporteInventario.generar_csv(rows, destino, self.usuario_nombre or "")
                accion = "Generar reporte dashboard CSV"
            else:
                ReporteInventario.generar_pdf(rows, stats, destino, self.usuario_nombre or "")
                accion = "Generar reporte dashboard PDF"

            self._audit(accion)
            Notification(
                self.root,
                "Reporte generado",
                f"Se exportó correctamente en:\n{destino}",
                notification_type="success",
                duration=3000
            )
        except Exception as e:
            Notification(self.root, "Error de reporte", str(e),
                         notification_type="error")
        finally:
            self.progress_bar.stop()

    # gestion personas

    def mostrar_gestion_personas(self):
        # delegado a modulo personas.py
        self.personas.mostrar()

    # auditoria
 

    def mostrar_auditoria(self):
        # delegado a modulo audit.py
        self.auditoria.mostrar()

    def mostrar_agregar_pdf(self):
        # delegado a pdf_manager.py
        self.pdf.mostrar_agregar()

    def seleccionar_archivo(self):
        # delegado a pdf_manager.py
        self.pdf.seleccionar_archivo()

    def procesar_agregar_pdf(self, window):
        # delegado a pdf_manager.py
        self.pdf.procesar_agregar(window)

    def ver_pdfs(self):
        # delegado a pdf_manager.py
        self.pdf.ver_todos()

    def buscar_pdfs(self):
        # delegado a pdf_manager.py
        self.pdf.buscar()

    def mostrar_detalles_pdf(self):
        # delegado a pdf_manager.py
        self.pdf.mostrar_detalles()

    def abrir_pdf_doble_click(self):
        # delegado a pdf_manager.py
        self.pdf.abrir_doble_click()

    def abrir_pdf_id(self, pdf_id, window=None):
        # delegado a pdf_manager.py
        self.pdf.abrir_por_id(pdf_id, window)

    def eliminar_pdf(self):
        # delegado a pdf_manager.py
        self.pdf.eliminar()

    def editar_pdf(self):
        # delegado a pdf_manager.py
        self.pdf.editar()

    def exportar_pdf(self):
        # delegado a pdf_manager.py
        self.pdf.exportar()

    def slide_in_frame(self, frame, start_relx=1.0, end_relx=0.0, steps=20, callback=None):
        # animacion slide
        frame.place(relx=start_relx, rely=0.0, relwidth=1.0, relheight=1.0)

        def animate(step=0):
            if step <= steps:
                t = step / steps
                eased = ease_in_out(t)
                new_relx = start_relx - eased * (start_relx - end_relx)
                frame.place(relx=new_relx, rely=0.0, relwidth=1.0, relheight=1.0)
                self.root.after(20, animate, step + 1)
            else:
                if callback:
                    callback()

        animate()

    def cerrar_conexion_y_salir(self):
        # cerrar y salir
        self.cerrar_conexion()
        self.root.destroy()

    def cerrar_conexion(self):
        # cerrar bd
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def on_intro_click(self, event=None):
        # clic en intro
        def _show():
            self.frame_intro.pack_forget()
            self._hide_all_frames()
            self.frame_inicial.pack(expand=True, fill="both")
        self._fade_to(_show)


# PUNTO DE ENTRADA


if __name__ == "__main__":
    root = ctk.CTk()
    app = AppDBPDF(root)
    root.protocol("WM_DELETE_WINDOW", app.cerrar_conexion_y_salir)
    root.mainloop()


# Copyright (c) 2024 DatenJäger. All rights reserved.