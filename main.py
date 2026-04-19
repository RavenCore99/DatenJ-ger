

# Copyright (c) 2024 DatenJäger. All rights reserved.
# Prototipo de sistema de gestion documental seguro | 2FA | encriptacion AES-256-GCM | UI actualizada|
 # --.-.-.-.-.-.-.-.-.-.-.--.-.-.-.-.-.
"""
main.py - aplicacion Principal
DatenJäger v.2.0. - Sistema de Gestion Documental

"""

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

#  módulos locales
from config import Config
from encryption import EncryptionManager
from database import (conectar_db, hash_contrasena, verify_contrasena,
                      format_size, format_date_friendly, ease_in_out,
                      check_account_locked, record_failed_attempt,
                      reset_failed_attempts, password_strength,
                      set_trust_token, check_trust_token, clear_trust_token)
from ui_components import (Notification, ProgressBarModerno, DashboardWidget,
                           GradientBackground, PasswordStrengthBar, ConfirmDialog,
                           PDFViewerWindow, get_dynamic_colors)
from reporter import ReporteInventario



# Config global de CustomTkinter


ctk.set_default_color_theme("blue")


# Colores definidos

COLOR_BG_LIGHT   = "#f0f4ff"
COLOR_BG_DARK    = "#1a1a2e"
COLOR_PRIMARY    = "#4CAF50"
COLOR_SECONDARY  = "#2196F3"
COLOR_WARNING    = "#FF9800"
COLOR_ERROR      = "#F44336"
COLOR_SUCCESS    = "#4CAF50"
COLOR_TEXT_LIGHT = "#1a237e"
COLOR_TEXT_DARK  = "#e0e0e0"


# clase principal actualizada  |V.2.0


class AppDBPDF:
    """v.2.0 con 2FA + Encriptación + UI Moderna"""

    def __init__(self, root):
        """inicializa la aplicacion"""
        self.root = root
        self.root.title("DatenJäger v.2.0 – Gestión Documental Segura")
        self.root.geometry("1100x760")

        self.config = Config()
        window_size = self.config.get("window_size", "1100x760")
        self.root.geometry(window_size)

        # Verifica si los colorees dinamicos estan guardadosa
        theme = self.config.get("theme", "System")
        ctk.set_appearance_mode(theme)

        self.conn, self.cursor = conectar_db()
        self._db_lock = threading.Lock()  
        self.usuario_actual = None
        self.usuario_nombre = None
        self._session_key   = None   # clave AES-256 derivada en login; nunca la contraseña plana
        self.animating = False
        self._search_timer = None                   # busqueda con debounce
        self._configure_timer = None                    # guarda con debounce
        self._idle_timer = None                     # logout automático por inactividad
        self._idle_warning_timer = None             # advertencia previa al logout
        self._idle_bind_ids = []                    # IDs de bindings de actividad

        self._setup_atajos()
        self._crear_frames()
        self._apply_treeview_style()
        self._setup_treeview_sorting()
        self.root.minsize(900, 650)
        self.mostrar_inicial()

        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Configure>", self._on_window_configure)

        # restaura el estado inicial de la ventana (maximizada o tamaño guardado)
        if self.config.get("window_maximized", False):
            self.root.after(100, self._maximize_window)

    def get_colors(self):
        """colores dinmicos"""
        return get_dynamic_colors()

    def _show_modal_window(self, window, delay_ms=0):
        """Muestra una ventana y aplica grab de forma segura sin lanzar TclError."""
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
                # Si el gestor de ventanas aún no la muestra, se abre sin modal.
                pass

        window.after(delay_ms, _activate)

    def _setup_atajos(self):
                #"""Configura atajos de teclado"""
        self.root.bind("<Control-q>", lambda e: self.cerrar_conexion_y_salir())
        self.root.bind("<Control-f>", lambda e: self.entry_busqueda.focus() if hasattr(self, 'entry_busqueda') else None)
        self.root.bind("<Control-n>", lambda e: self.mostrar_agregar_pdf() if self.usuario_actual else None)
        self.root.bind("<Delete>", lambda e: self.eliminar_pdf() if self.usuario_actual else None)

    def toggle_fullscreen(self, event=None):
                        # alterna fullscreen  (F11) de forma multiplataforma
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
                                        # maximiza la ventana de forma multiplataforma"""
        try:
            if os.name == 'nt':
                self.root.state('zoomed')
            else:
                self.root.attributes('-zoomed', True)
        except Exception:
            pass

    def _on_window_configure(self, event=None):
                        # Persiste el tamaño/estado de ventana cuando cambia | con debounce
        if event is None or event.widget is not self.root:
            return
                        # cancela cualquier guardado pendiente para evitar múltiples escrituras rápidas
        if self._configure_timer:
            self.root.after_cancel(self._configure_timer)
        self._configure_timer = self.root.after(500, self._save_window_state)

    def _save_window_state(self):
                        # guarda el tamaño y el estado maximizado de la ventana             
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
                    # Crea todos los frames de la aplicación
        colors = self.get_colors()

        # ── INTRO ─ # por ajustar
        self.frame_intro = ctk.CTkFrame(self.root, fg_color=COLOR_BG_DARK)
        self.frame_intro.pack(expand=True, fill="both")

        # Gradient animated background
        self._intro_bg = GradientBackground(self.frame_intro)
        self._intro_bg.place(relx=0, rely=0, relwidth=1, relheight=1)

        intro_card = ctk.CTkFrame(
            self.frame_intro, fg_color=("#e8eeff", "#1a1a3e"),
            corner_radius=20
        )
        intro_card.place(relx=0.5, rely=0.5, anchor="center")

        self.intro_text = ctk.CTkLabel(
            intro_card,
            text="🔐 DatenJäger",
            font=("Arial", 52, "bold"),
            text_color="white"
        )
        self.intro_text.pack(padx=60, pady=(40, 10))
        self.intro_text.bind("<Button-1>", self.on_intro_click)

        self.access_text = ctk.CTkLabel(
            intro_card,
            text="Sistema de Gestión Documental Seguro\nAES-256-GCM · 2FA · PBKDF2",
            text_color="#c8d8ff",
            font=("Arial", 14)
        )
        self.access_text.pack(pady=(0, 10))
        self.access_text.bind("<Button-1>", self.on_intro_click)

        ctk.CTkButton(
            intro_card,
            text="✨  Acceder al Sistema",
            command=self.on_intro_click,
            fg_color=COLOR_PRIMARY,
            hover_color="#388E3C",
            font=("Arial", 13, "bold"),
            corner_radius=10,
            width=260, height=46
        ).pack(pady=(10, 40))

        # ─ INICIAL ─
        self.frame_inicial = ctk.CTkFrame(self.root, fg_color=COLOR_BG_DARK)

        _bg_inicial = GradientBackground(
            self.frame_inicial,
            colors_dark=[("#1a1a2e", "#16213e"), ("#16213e", "#0f3460")],
            colors_light=[("#e3f2fd", "#bbdefb"), ("#bbdefb", "#e8f5e9")]
        )
        _bg_inicial.place(relx=0, rely=0, relwidth=1, relheight=1)

        card_inicial = ctk.CTkFrame(
            self.frame_inicial, fg_color=("#f5f7ff", "#1e2a4a"),
            corner_radius=20
        )
        card_inicial.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            card_inicial,
            text="🔐 DatenJäger",
            font=("Arial", 28, "bold"),
            text_color=colors["text_primary"]
        ).pack(pady=(30, 4))

        ctk.CTkLabel(
            card_inicial,
            text="Seguridad · Privacidad · Control",
            font=("Arial", 11),
            text_color=COLOR_SECONDARY
        ).pack(pady=(0, 24))

        ctk.CTkButton(
            card_inicial,
            text="🔓  Iniciar Sesión",
            command=self.mostrar_login,
            fg_color=COLOR_PRIMARY,
            hover_color="#388E3C",
            text_color="white",
            font=("Arial", 13, "bold"),
            corner_radius=10,
            width=280, height=48
        ).pack(pady=8)

        ctk.CTkButton(
            card_inicial,
            text="✍️   Crear Usuario",
            command=self.mostrar_registro,
            fg_color=COLOR_SECONDARY,
            hover_color="#1976D2",
            text_color="white",
            font=("Arial", 13, "bold"),
            corner_radius=10,
            width=280, height=48
        ).pack(pady=8)

        ctk.CTkLabel(
            card_inicial,
            text="v.2.0 – AES-256-GCM + PBKDF2 + 2FA",
            font=("Arial", 9),
            text_color=("#9E9E9E", "#666666")
        ).pack(pady=(16, 28))

        # ── LOGIN ───
        self.frame_login = ctk.CTkFrame(self.root, fg_color=COLOR_BG_DARK)

        _bg_login = GradientBackground(
            self.frame_login,
            colors_dark=[("#1a1a2e", "#0d47a1"), ("#0d47a1", "#1a1a2e")],
            colors_light=[("#e8f5e9", "#c8e6c9"), ("#c8e6c9", "#e8f5e9")]
        )
        _bg_login.place(relx=0, rely=0, relwidth=1, relheight=1)

        card_login = ctk.CTkFrame(
            self.frame_login, fg_color=("#f5f7ff", "#1e2a4a"),
            corner_radius=20
        )
        card_login.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            card_login,
            text="🔓 Iniciar Sesión  🔓",
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
            pw_row_login, text="👁", width=38, height=42,
            fg_color=COLOR_SECONDARY, hover_color="#1565c0",
            corner_radius=8, font=("Arial", 13),
            command=lambda: self._toggle_pw(
                self.entry_contrasena_login, "_show_pw_login")
        ).pack(side="left", padx=(4, 0))

        self.entry_contrasena_login.bind("<Return>", lambda e: self.login())

        ctk.CTkButton(
            card_login, text="✅  Siguiente  ✅",
            command=self.login,
            fg_color=COLOR_PRIMARY, hover_color="#388E3C",
            text_color="white", font=("Arial", 12, "bold"),
            corner_radius=8, width=320, height=44
        ).pack(pady=(16, 8))

        ctk.CTkButton(
            card_login, text="⬅️   Volver  ⬅️",
            command=self.mostrar_inicial,
            fg_color="#9E9E9E", hover_color="#757575",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=320, height=38
        ).pack(pady=(0, 28))

                         # ── 2FA ───
        self.frame_2fa = ctk.CTkFrame(self.root, fg_color=COLOR_BG_DARK)

        _bg_2fa = GradientBackground(
            self.frame_2fa,
            colors_dark=[("#1a1a2e", "#4a0072"), ("#4a0072", "#1a1a2e")],
            colors_light=[("#f3e5f5", "#e1bee7"), ("#e1bee7", "#f3e5f5")]
        )
        _bg_2fa.place(relx=0, rely=0, relwidth=1, relheight=1)

        card_2fa = ctk.CTkFrame(
            self.frame_2fa, fg_color=("#f5f0ff", "#1e1a2e"),
            corner_radius=20
        )
        card_2fa.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            card_2fa, text="🔐 Verificación 2FA 🔐",
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

                     # TOTP countdown ring 
        self._totp_timer_label = ctk.CTkLabel(
            card_2fa, text="⏳ 30s", font=("Arial", 10),
            text_color=colors["text_secondary"]
        )
        self._totp_timer_label.pack()
        self._start_totp_timer()

        ctk.CTkButton(
            card_2fa, text="✅  Verificar",
            command=self.verificar_2fa,
            fg_color=COLOR_PRIMARY, hover_color="#388E3C",
            text_color="white", font=("Arial", 12, "bold"),
            corner_radius=8, width=280, height=44
        ).pack(pady=(12, 6))

        ctk.CTkLabel(
            card_2fa,
            text="¿Sin acceso al teléfono? Usa un código de respaldo",
            text_color=COLOR_WARNING, font=("Arial", 10)
        ).pack(pady=(4, 0))

        ctk.CTkButton(
            card_2fa, text="🔄  Código de Respaldo  🔄 ",
            command=self.usar_codigo_respaldo,
            fg_color=COLOR_WARNING, hover_color="#F57C00",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=280, height=36
        ).pack(pady=6)

        ctk.CTkButton(
            card_2fa, text="⬅️   Volver   ⬅️ ",
            command=self.mostrar_login,
            fg_color="#9E9E9E", hover_color="#757575",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=280, height=36
        ).pack(pady=(0, 28))

        # REGISTER --_-
        self.frame_registro = ctk.CTkFrame(self.root, fg_color=COLOR_BG_DARK)

        _bg_reg = GradientBackground(
            self.frame_registro,
            colors_dark=[("#1a2e1a", "#0d3b2e"), ("#0d3b2e", "#1a2e1a")],
            colors_light=[("#e8f5e9", "#c8e6c9"), ("#c8e6c9", "#a5d6a7")]
        )
        _bg_reg.place(relx=0, rely=0, relwidth=1, relheight=1)

        card_reg = ctk.CTkFrame(
            self.frame_registro, fg_color=("#f0fff4", "#142e1e"),
            corner_radius=20
        )
        card_reg.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            card_reg, text="  Crear Usuario",
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
            pw_row_reg, text="👁", width=38, height=42,
            fg_color=COLOR_SECONDARY, hover_color="#1565c0",
            corner_radius=8, font=("Arial", 13),
            command=lambda: self._toggle_pw(
                self.entry_contrasena_registro, "_show_pw_reg")
        ).pack(side="left", padx=(4, 0))

        # password strength bar
        self._pw_strength_bar = PasswordStrengthBar(card_reg)
        self._pw_strength_bar.pack(fill="x", padx=40, pady=(4, 8))
        self.entry_contrasena_registro.bind(
            "<KeyRelease>",
            lambda e: self._pw_strength_bar.update(
                self.entry_contrasena_registro.get())
        )

        ctk.CTkButton(
            card_reg, text="✅  Registrar",
            command=self.registrarse,
            fg_color=COLOR_SECONDARY, hover_color="#1976D2",
            text_color="white", font=("Arial", 12, "bold"),
            corner_radius=8, width=340, height=44
        ).pack(pady=(8, 8))

        ctk.CTkButton(
            card_reg, text="⬅️   Volver",
            command=self.mostrar_inicial,
            fg_color="#9E9E9E", hover_color="#757575",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=340, height=36
        ).pack(pady=(0, 28))

        # ── SETUP 2FA ──
        self.frame_setup_2fa = ctk.CTkFrame(self.root, fg_color=COLOR_BG_DARK)

        _bg_s2fa = GradientBackground(
            self.frame_setup_2fa,
            colors_dark=[("#2e1a00", "#5d2d00"), ("#5d2d00", "#2e1a00")],
            colors_light=[("#fff8e1", "#ffe082"), ("#ffe082", "#fff8e1")]
        )
        _bg_s2fa.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Scrollable to fit QR + instructions
        self._setup2fa_scroll = ctk.CTkScrollableFrame(
            self.frame_setup_2fa,
            fg_color=("#fffde7", "#1e1600"),
            corner_radius=20, width=460, height=520
        )
        self._setup2fa_scroll.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            self._setup2fa_scroll,
            text="🔐 Configurar Autenticación 2FA  🔐",
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

        # se muestra el QR con card y espacio reservado | se actualizara con el QR real al generar el secret TOTP
        qr_card = ctk.CTkFrame(
            self._setup2fa_scroll, fg_color="white", corner_radius=12
        )
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
        ctk.CTkButton(
            secret_row, text="📋 Copiar",
            width=90, height=30,
            fg_color=COLOR_SECONDARY, hover_color="#1565c0",
            font=("Arial", 10, "bold"), corner_radius=6,
            command=self._copy_totp_secret
        ).pack(side="left")

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

        ctk.CTkButton(
            self._setup2fa_scroll, text="✅  Confirmar y Activar 2FA",
            command=self.confirmar_setup_2fa,
            fg_color=COLOR_PRIMARY, hover_color="#388E3C",
            text_color="white", font=("Arial", 12, "bold"),
            corner_radius=8, width=320, height=44
        ).pack(pady=(10, 6))

        ctk.CTkLabel(
            self._setup2fa_scroll,
            text="⚠️ Guarda tus códigos de respaldo en un lugar seguro",
            text_color=COLOR_WARNING, font=("Arial", 10, "bold")
        ).pack(pady=(4, 16))

        # ── PANEL PRINCIPAL | DASHBOARD ──
        #   tuple en CTk automaticamente cambia entre el primer color para modo claro y el segundo para modo oscuro
        self.frame_principal = ctk.CTkFrame(self.root, fg_color=(COLOR_BG_LIGHT, COLOR_BG_DARK))

        # -- Top navbar --
        navbar = ctk.CTkFrame(
            self.frame_principal,
            fg_color=("#1a237e", "#0d1b3e"),
            height=56, corner_radius=0
        )
        navbar.pack(fill="x")
        navbar.pack_propagate(False)

        ctk.CTkLabel(
            navbar, text="🔐 DatenJäger",
            font=("Arial", 18, "bold"), text_color="white"
        ).pack(side="left", padx=16, pady=10)

        # User badge
        self._user_badge = ctk.CTkLabel(
            navbar, text="",
            font=("Arial", 11), text_color="#90caf9",
            fg_color=("#1e3a8a", "#0a1929"),
            corner_radius=8
        )
        self._user_badge.pack(side="left", padx=8)

                    # Right-side navbar buttons
        def _make_nav_btn(text, command, color="#2e3f8a", hover="#3a4faa"):
            return ctk.CTkButton(
                navbar, text=text, command=command,
                width=110, height=34,
                fg_color=color, hover_color=hover,
                corner_radius=7, font=("Arial", 10, "bold")
            )

        _make_nav_btn("🚪 Cerrar Sesión", self._logout,
                      "#C62828", "#B71C1C").pack(side="right", padx=6, pady=10)

        def toggle_theme():
            current_mode = ctk.get_appearance_mode()
            new_mode = "Light" if current_mode == "Dark" else "Dark"
            ctk.set_appearance_mode(new_mode)
            self.config.set("theme", new_mode)
            btn_theme.configure(
                text="☀️  Claro" if new_mode == "Dark" else "🌙 Oscuro"
            )
            self.actualizar_colores_dinamicos()

        current_theme = ctk.get_appearance_mode()
        btn_theme = _make_nav_btn(
            "☀️  Claro" if current_theme == "Dark" else "🌙 Oscuro",
            toggle_theme
        )
        btn_theme.pack(side="right", padx=4, pady=10)

        _make_nav_btn(
            "👤  Mi Cuenta",
            self.abrir_configuracion_cuenta,
            color="#1565c0", hover="#0d47a1"
        ).pack(side="right", padx=4, pady=10)

        _make_nav_btn(
            "📋 Auditoría",
            self.mostrar_auditoria,
            color="#37474f", hover="#455a64"
        ).pack(side="right", padx=4, pady=10)

        _make_nav_btn(
            "👥 Personas",
            self.mostrar_gestion_personas,
            color="#6A1B9A", hover="#4A148C"
        ).pack(side="right", padx=4, pady=10)

        _make_nav_btn(
            "📑 Reporte",
            lambda: self.exportar_reporte_dashboard("pdf"),
            color="#00695c", hover="#004d40"
        ).pack(side="right", padx=4, pady=10)

        _make_nav_btn(
            "ℹ️  Acerca de",
            lambda: Notification(
                self.root,
                "🔐 DatenJäger v.2.0",
                "Encriptación AES-256-GCM · PBKDF2 · 2FA\nSeguridad Empresarial Moderna",
                notification_type="info", duration=4000
            )
        ).pack(side="right", padx=4, pady=10)

                # -- Progress bar --
        self.progress_bar = ProgressBarModerno(self.frame_principal)
        self.progress_bar.pack(fill="x", pady=0)

                    # -- Dashboard --
        self.dashboard_container = ctk.CTkFrame(
            self.frame_principal, fg_color="transparent"
        )
        self.dashboard_container.pack(fill="x", padx=14)

            # -- Toolbar (search row + action buttons row) --
        toolbar_container = ctk.CTkFrame(self.frame_principal, fg_color="transparent")
        toolbar_container.pack(fill="x", padx=14, pady=(6, 0))

                    # Row 1: Search bar
        search_row = ctk.CTkFrame(toolbar_container, fg_color="transparent")
        search_row.pack(fill="x", pady=(0, 4))

                        # Search
        search_card = ctk.CTkFrame(search_row, fg_color=("#e8f0fe", "#1e2a4a"), corner_radius=10)
        search_card.pack(side="left")

        ctk.CTkLabel(
            search_card, text="🔍",
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

                    # Row 2: botones de accion
        actions_row = ctk.CTkFrame(toolbar_container, fg_color="transparent")
        actions_row.pack(fill="x", pady=(0, 2))

                        # botones de accion
        actions = [
            ("➕ Agregar",  self.mostrar_agregar_pdf,   COLOR_PRIMARY,   "#388E3C"),
            ("👁 Ver Todos", self.ver_pdfs,               COLOR_SECONDARY, "#1565c0"),
            ("ℹ️ Detalles",  self.mostrar_detalles_pdf,   COLOR_WARNING,   "#E65100"),
            ("✏️ Editar",    self.editar_pdf,             "#7B1FA2",       "#6A1B9A"),
            ("⬇️ Exportar",  self.exportar_pdf,           "#00897B",       "#00695C"),
            ("🗑️ Eliminar",  self.eliminar_pdf,           COLOR_ERROR,     "#B71C1C"),
        ]
        for text, cmd, fg, hover in actions:
            ctk.CTkButton(
                actions_row, text=text, command=cmd,
                fg_color=fg, hover_color=hover,
                text_color="white", font=("Arial", 10, "bold"),
                corner_radius=7, height=36, width=108
            ).pack(side="left", padx=4)

                         # -- TreeView + Preview side panel --
        content_area = ctk.CTkFrame(self.frame_principal, fg_color="transparent")
        content_area.pack(fill="both", expand=True, padx=14, pady=8)

                              # Treeview frame
        tree_frame = ctk.CTkFrame(content_area, fg_color=("#ffffff", "#1e2a4a"), corner_radius=10)
        tree_frame.pack(side="left", fill="both", expand=True)

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

                        # Right-click context menu
        self._ctx_menu = tk.Menu(self.root, tearoff=0)
        self._ctx_menu.add_command(label="📂 Abrir / Desencriptar", command=self.abrir_pdf_doble_click)
        self._ctx_menu.add_command(label="ℹ️  Ver Detalles",         command=self.mostrar_detalles_pdf)
        self._ctx_menu.add_command(label="✏️  Editar Metadatos",     command=self.editar_pdf)
        self._ctx_menu.add_command(label="⬇️  Exportar PDF",         command=self.exportar_pdf)
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="🗑️  Eliminar",             command=self.eliminar_pdf)

                        # Preview / detail sidebar
        self._preview_panel = ctk.CTkFrame(
            content_area, fg_color=("#e8f0fe", "#1a2540"),
            corner_radius=10, width=230
        )
        self._preview_panel.pack(side="right", fill="y", padx=(8, 0))
        self._preview_panel.pack_propagate(False)

        ctk.CTkLabel(
            self._preview_panel, text="📋 Detalle del Documento",
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
            text="📂 Abrir",
            command=self.abrir_pdf_doble_click,
            fg_color=COLOR_SECONDARY, hover_color="#1565c0",
            font=("Arial", 10, "bold"),
            corner_radius=7, width=160, height=34
        ).pack(pady=(10, 4))

        ctk.CTkButton(
            self._preview_panel,
            text="⬇️ Exportar",
            command=self.exportar_pdf,
            fg_color="#00897B", hover_color="#00695C",
            font=("Arial", 10, "bold"),
            corner_radius=7, width=160, height=34
        ).pack(pady=4)

        ctk.CTkButton(
            self._preview_panel,
            text="✏️ Editar",
            command=self.editar_pdf,
            fg_color="#7B1FA2", hover_color="#6A1B9A",
            font=("Arial", 10, "bold"),
            corner_radius=7, width=160, height=34
        ).pack(pady=4)

        ctk.CTkButton(
            self._preview_panel,
            text="🗑️ Eliminar",
            command=self.eliminar_pdf,
            fg_color=COLOR_ERROR, hover_color="#B71C1C",
            font=("Arial", 10, "bold"),
            corner_radius=7, width=160, height=34
        ).pack(pady=4)

                            # -- Status bar --
        self.status = ctk.CTkLabel(
            self.frame_principal,
            text="✅ Listo",
            text_color=colors["text_primary"],
            font=("Arial", 10),
            anchor="w"
        )
        self.status.pack(side="bottom", fill="x", padx=16, pady=(2, 6))

    def actualizar_colores_dinamicos(self):
        # actualiza los colores dinasmicos cuando cambia el tema
        colors = self.get_colors()

        # frame_principal
        #  usa (light, dark) tuple asi CTk lo actualiza automaticamente;
        # actualiza los colores de la barra de estado aqui.
        self.status.configure(text_color=colors["text_primary"])

        # re aplica TreeView stilos y actualiza alternando los row colors
        self._apply_treeview_style()
        if self.usuario_actual:
            self.ver_pdfs()

    
    # HELPERS: NAVIGATION
  

    def _hide_all_frames(self):
         #oculta todos los marcos de nivel superior y restablece el diseño
        for f in [self.frame_intro, self.frame_inicial, self.frame_login,
                  self.frame_2fa, self.frame_setup_2fa, self.frame_principal,
                  self.frame_registro]:
            f.pack_forget()
            f.place_forget()
        self.root.update()

    
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
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, row in enumerate(rows):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.tree.insert('', 'end', values=self._format_pdf_row(row), tags=(tag,))

    
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
            Notification(self.root, "📋 Copiado",
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
                    text=f"⏳ Código válido: {remaining}s",
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
            f"📄 {pdf_nombre}\n\n"
            f"📝 {descripcion or '—'}\n\n"
            f"💾 {tamano}\n"
            f"📅 {fecha}\n"
            f"🪪 Cédula: {cedula or '—'}\n"
            f"👤 {nombres or '—'}\n"
            f"🏢 {empresa or '—'}\n\n"
            f"🔒 AES-256-GCM Encriptado"
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
        # guarda el blob PDF ya cifrado en la base de datos
        try:
            self.cursor.execute("SELECT id FROM Personas WHERE cedula = ?", (cedula,))
            result = self.cursor.fetchone()
            if result:
                persona_id = result[0]
                self.cursor.execute(
                    "UPDATE Personas SET nombres = ?, empresa = ? WHERE id = ?",
                    (nombres, empresa, persona_id)
                )
            else:
                self.cursor.execute(
                    "INSERT INTO Personas (cedula, nombres, empresa) VALUES (?, ?, ?)",
                    (cedula, nombres, empresa)
                )
                persona_id = self.cursor.lastrowid

            self.cursor.execute(
                "INSERT INTO PDFs (nombre, descripcion, datos, datos_encriptados, "
                "tamano, fecha_subida, usuario_id, persona_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (nombre, descripcion, datos_enc, 1, tamano,
                 datetime.now().isoformat(), usuario_actual, persona_id)
            )
            pdf_id = self.cursor.lastrowid

            self.cursor.execute(
                "INSERT INTO Auditoria (accion, pdf_id, usuario_id, fecha) VALUES (?, ?, ?, ?)",
                ("Agregar PDF (Encriptado AES-256-GCM)", pdf_id, usuario_actual,
                 datetime.now().isoformat())
            )
            self.conn.commit()
            self._on_pdf_added(nombre, window)
        except Exception as e:
            self.conn.rollback()
            self._on_pdf_add_error(e)
        finally:
            self.progress_bar.stop()

    def _on_pdf_added(self, nombre, window):
        # se llama al hilo principal despues de que se guarda correctamente un PDF
        colors = self.get_colors()
        self.status.configure(
            text=f"✅ PDF {nombre} agregado y encriptado",
            text_color=colors["text_primary"]
        )
        Notification(self.root, "✅ Éxito",
                     f"PDF {nombre} agregado\nEncriptado con AES-256-GCM",
                     notification_type="success")
        window.destroy()
        self.cargar_dashboard()
        self.ver_pdfs()

    def _on_pdf_add_error(self, error):
        # se llama al hilo principal cuando falla la adición de un PDF
        Notification(self.root, "❌ Error", str(error), notification_type="error")
        colors = self.get_colors()
        self.status.configure(text="❌ Error al agregar PDF",
                              text_color=colors["text_primary"])

    def _abrir_visor_pdf(self, pdf_bytes: bytes, nombre: str, window=None):
        # abre el visor PDF inline con los bytes descifrados — sin escribir al disco
        if window:
            window.destroy()
        colors = self.get_colors()
        self.status.configure(
            text=f"✅ PDF cargado: {nombre}",
            text_color=colors["text_primary"]
        )
        PDFViewerWindow(self.root, pdf_bytes, nombre)

    def mostrar_inicial(self):
        # muestra la pantalla inicial
        self._hide_all_frames()
        self.frame_inicial.pack(expand=True, fill="both")

    def mostrar_login(self):
        # muestra la pantalla de login
        self._hide_all_frames()
        self.entry_usuario_login.delete(0, tk.END)
        self.entry_contrasena_login.delete(0, tk.END)
        self.frame_login.pack(expand=True, fill="both")

    def mostrar_registro(self):
        # muestra la pantalla de registro
        self._hide_all_frames()
        self.entry_usuario_registro.delete(0, tk.END)
        self.entry_contrasena_registro.delete(0, tk.END)
        self.frame_registro.pack(expand=True, fill="both")

    def registrarse(self):
        # registra un nuevo usuario
        nombre = self.entry_usuario_registro.get().strip()
        contrasena = self.entry_contrasena_registro.get().strip()

        if not nombre or not contrasena:
            Notification(
                self.root, "❌ Error",
                "Ingresa nombre de usuario y contraseña",
                notification_type="error"
            )
            return

        if len(nombre) < 3:
            Notification(
                self.root, "❌ Error",
                "El nombre de usuario debe tener al menos 3 caracteres",
                notification_type="error"
            )
            return

        if len(contrasena) < 8:
            Notification(
                self.root, "❌ Error",
                "La contraseña debe tener mínimo 8 caracteres",
                notification_type="error"
            )
            return

        score, label, _ = password_strength(contrasena)
        if score < 2:
            Notification(
                self.root, "⚠️ Contraseña insegura",
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
                self.root, "✅ Éxito",
                f"Usuario {nombre} registrado\nConfigurando 2FA…",
                notification_type="success"
            )
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                Notification(
                    self.root, "❌ Error",
                    f"El usuario '{nombre}' ya existe",
                    notification_type="error"
                )
            else:
                Notification(self.root, "❌ Error", str(e), notification_type="error")

    def login(self):
        # inicia sesion (paso 1: validar usuario/contraseña)
        nombre = self.entry_usuario_login.get().strip()
        contrasena = self.entry_contrasena_login.get().strip()

        if not nombre or not contrasena:
            Notification(
                self.root, "❌ Error",
                "Ingresa nombre de usuario y contraseña",
                notification_type="error"
            )
            return

        # consultar bloqueo de cuenta
        locked, secs = check_account_locked(self.cursor, nombre)
        if locked:
            mins = secs // 60 + 1
            Notification(
                self.root, "🔒 Cuenta bloqueada 🔒",
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
                    # recalcular la contraseña SHA-256 heredada en el primer inicio de sesión exitoso.
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

                    # derivar session key AES-256 desde el salt del hash almacenado.
                    # si el hash acaba de migrarse usamos new_hash (ya tiene formato pbkdf2:).
                    ref_hash = new_hash if new_hash else hash_stored
                    ref_parts = ref_hash.split(":") if ref_hash.startswith("pbkdf2:") else []
                    user_salt = ref_parts[1] if len(ref_parts) == 3 else nombre
                    session_key = EncryptionManager.derive_session_key(contrasena, user_salt)

                    # migración automática ENC: → ENCK: (datos cifrados con contraseña plana en #1).
                    # se hace aquí porque es el único momento donde contraseña y session key coexisten.
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

                    # guardar solo la clave derivada; la contraseña original no se retiene
                    self._session_key   = session_key
                    self.usuario_actual = usuario_id
                    self.usuario_nombre = nombre

                    if totp_enabled:
                        # verificar si el dispositivo tiene un token de confianza vigente
                        trust_hours = self.config.get("2fa_trust_hours", 0)
                        if trust_hours > 0:
                            local_tokens = self.config.get("trust_tokens", {})
                            local_token  = local_tokens.get(nombre)
                            if local_token and check_trust_token(
                                self.cursor, usuario_id, local_token
                            ):
                                # dispositivo de confianza → omitir pantalla 2FA
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
                            self.root, "🔒 Cuenta bloqueada",
                            "Se bloqueó tu cuenta por múltiples intentos fallidos.\n"
                            f"Espera {secs2 // 60 + 1} min.",
                            notification_type="error", duration=5000
                        )
                    else:
                        Notification(
                            self.root, "❌ Error",
                            "Contraseña incorrecta",
                            notification_type="error"
                        )
            else:
                Notification(
                    self.root, "❌ Error",
                    "Usuario no encontrado",
                    notification_type="error"
                )
        except Exception as e:
            Notification(self.root, "❌ Error", str(e), notification_type="error")

    def mostrar_setup_2fa(self):
        # muestra pantalla para configurar 2FA
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
        # confirma y guarda la configuracion
        codigo = self.entry_confirm_2fa.get().strip()

        if not codigo or len(codigo) != 6:
            Notification(
                self.root, "❌ Error",
                "Ingresa un código válido de 6 dígitos",
                notification_type="error"
            )
            return

        try:
            totp = pyotp.TOTP(self.totp_secret)

            if totp.verify(codigo):
                backup_codes = [f"{random.randint(100000, 999999)}" for _ in range(5)]
                backup_codes_str = ",".join(backup_codes)

                # cifrar totp_secret y backup_codes con la session key (nunca con la contraseña plana)
                secret_enc   = EncryptionManager.encrypt_str_with_key(self.totp_secret,  self._session_key)
                backups_enc  = EncryptionManager.encrypt_str_with_key(backup_codes_str, self._session_key)

                self.cursor.execute(
                    "UPDATE Usuarios SET totp_secret = ?, totp_enabled = 1, backup_codes = ? WHERE nombre = ?",
                    (secret_enc, backups_enc, self.usuario_nombre)
                )
                self.conn.commit()

                # mostrar coSdigos de respaldo y esperar a que el usuario cierre la ventana
                self._mostrar_codigos_respaldo(backup_codes)
                self._audit("Configuración 2FA completada")

                # La notificacion y la navegación ocurren despues de que el usuario cierra el diálogo
                Notification(
                    self.root, "✅ 2FA Configurado",
                    "Autenticación 2FA activada correctamente",
                    notification_type="success"
                )

                self.mostrar_login()
            else:
                Notification(
                    self.root, "❌ Error",
                    "El código es incorrecto o ha expirado",
                    notification_type="error"
                )
        except Exception as e:
            Notification(self.root, "❌ Error", str(e), notification_type="error")

    def _mostrar_codigos_respaldo(self, backup_codes):
            # muestra los códigos de respaldo en una ventana modal, con opción para copiar al portapapeles
        colors = self.get_colors()
        win = ctk.CTkToplevel(self.root)
        win.title("⚠️ Códigos de Respaldo")
        win.geometry("440x420")
        win.resizable(False, False)
        win.transient(self.root)
        win.configure(fg_color=colors["bg_secondary"])
        win.withdraw()  # ocultar hasta que el contenido esté listo

        def _build():
            ctk.CTkLabel(
                win, text="⚠️ Guarda tus Códigos de Respaldo",
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

            codes_frame = ctk.CTkFrame(win, fg_color=("#f5f5f5", "#1e1e1e"), corner_radius=10)
            codes_frame.pack(padx=30, pady=12, fill="x")

            for code in backup_codes:
                ctk.CTkLabel(
                    codes_frame, text=f"  🔑  {code}",
                    font=("Arial", 15, "bold"),
                    text_color=COLOR_WARNING
                ).pack(pady=4)

            def copiar_todos():
                texto = "\n".join(backup_codes)
                win.clipboard_clear()
                win.clipboard_append(texto)
                Notification(win, "📋 Copiado", "Códigos copiados al portapapeles",
                             notification_type="success", duration=2000)

            ctk.CTkButton(
                win, text="📋 Copiar todos",
                command=copiar_todos,
                fg_color=COLOR_SECONDARY, hover_color="#1565c0",
                text_color="white", font=("Arial", 11, "bold"),
                corner_radius=8, width=200, height=36
            ).pack(pady=8)

            ctk.CTkButton(
                win, text="✅ Entendido",
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
        # verifica codigo 2FA en login
        codigo = self.entry_2fa_code.get().strip()

        if not codigo or len(codigo) != 6:
            Notification(
                self.root,
                "❌ Error",
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
                # descifrar el secret con la session key (ENCK:) o devolver tal cual si es legacy plaintext
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
                        "❌ Error",
                        "El código es incorrecto o ha expirado",
                        notification_type="error"
                    )
            else:
                Notification(
                    self.root,
                    "❌ Error",
                    "Usuario no encontrado",
                    notification_type="error"
                )
        except Exception as e:
            Notification(
                self.root,
                "❌ Error",
                str(e),
                notification_type="error"
            )

    def usar_codigo_respaldo(self):
        # usa un codigo de respaldo
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
                # descifrar backup_codes con la session key (ENCK:) o plaintext legacy
                codes_raw    = EncryptionManager.decrypt_str_with_key(result[0], self._session_key)
                backup_codes = codes_raw.split(",")

                if codigo in backup_codes:
                    backup_codes.remove(codigo)
                    backup_codes_str = ",".join(backup_codes)

                    # recifrar la lista actualizada con la session key
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
                        "✅ Código Aceptado",
                        "Login completado con código de respaldo",
                        notification_type="success"
                    )

                    self.completar_login()
                else:
                    self._audit("Código de respaldo inválido")
                    Notification(
                        self.root,
                        "❌ Error",
                        "El código de respaldo es inválido",
                        notification_type="error"
                    )
        except Exception as e:
            Notification(
                self.root,
                "❌ Error",
                str(e),
                notification_type="error"
            )

    # ══════════════════════════════════════════════════════════════
    # PANEL DE CONFIGURACIÓN DE CUENTA
    # ══════════════════════════════════════════════════════════════

    def abrir_configuracion_cuenta(self):
        """Abre el panel de configuración de cuenta con tres secciones."""
        if not self.usuario_actual:
            return

        colors = self.get_colors()
        win = ctk.CTkToplevel(self.root)
        win.title("👤 Configuración de Cuenta")
        win.geometry("520x560")
        win.resizable(False, False)
        win.transient(self.root)
        win.configure(fg_color=colors["bg_secondary"])
        win.withdraw()

        def _build():
            ctk.CTkLabel(
                win, text=f"👤  {self.usuario_nombre}",
                font=("Arial", 17, "bold"),
                text_color=colors["text_primary"]
            ).pack(pady=(20, 4))

            ctk.CTkLabel(
                win, text="Configuración de Cuenta",
                font=("Arial", 11), text_color=colors["text_secondary"]
            ).pack(pady=(0, 14))

            tabs = ctk.CTkTabview(win, width=480, height=440, corner_radius=12)
            tabs.pack(padx=18, pady=(0, 18), fill="both", expand=True)

            tabs.add("🔑 Contraseña")
            tabs.add("🔐 Códigos 2FA")
            tabs.add("🛡️ Confianza")

            self._build_tab_contrasena(tabs.tab("🔑 Contraseña"), win, colors)
            self._build_tab_codigos(tabs.tab("🔐 Códigos 2FA"), colors)
            self._build_tab_confianza(tabs.tab("🛡️ Confianza"), colors)

            win.update_idletasks()
            win.deiconify()
            win.lift()
            win.focus_force()

        win.after(200, _build)

    def _build_tab_contrasena(self, parent, win, colors):
        """Tab: cambio de contraseña con verificación TOTP."""
        ctk.CTkLabel(
            parent, text="Cambiar Contraseña",
            font=("Arial", 13, "bold"), text_color=colors["text_primary"]
        ).pack(pady=(14, 10))

        # Contraseña actual
        ctk.CTkLabel(parent, text="Contraseña actual",
                     font=("Arial", 10, "bold"), text_color=colors["text_secondary"]
                     ).pack(anchor="w", padx=24)
        entry_actual = ctk.CTkEntry(
            parent, placeholder_text="Tu contraseña actual",
            width=360, height=38, show="●", font=("Arial", 11), corner_radius=8
        )
        entry_actual.pack(pady=(2, 8))

        # Nueva contraseña
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

        # Confirmar nueva
        ctk.CTkLabel(parent, text="Confirmar nueva contraseña",
                     font=("Arial", 10, "bold"), text_color=colors["text_secondary"]
                     ).pack(anchor="w", padx=24)
        entry_confirm = ctk.CTkEntry(
            parent, placeholder_text="Repite la nueva contraseña",
            width=360, height=38, show="●", font=("Arial", 11), corner_radius=8
        )
        entry_confirm.pack(pady=(2, 8))

        # Código TOTP del autenticador
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

            # validaciones básicas
            if not all([pw_actual, pw_nueva, pw_confirm, totp_code]):
                Notification(win, "⚠️ Campos incompletos",
                             "Completa todos los campos", notification_type="warning")
                return
            if pw_nueva != pw_confirm:
                Notification(win, "❌ Error", "Las nuevas contraseñas no coinciden",
                             notification_type="error")
                return
            score, label, _ = password_strength(pw_nueva)
            if score < 2:
                Notification(win, "⚠️ Contraseña débil",
                             f"Fortaleza: {label}. Usa mayúsculas, números y símbolos.",
                             notification_type="warning")
                return

            try:
                # 1. verificar contraseña actual
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
                    Notification(win, "❌ Error", "Contraseña actual incorrecta",
                                 notification_type="error")
                    return

                # 2. verificar código TOTP del autenticador
                if not totp_enabled or not totp_enc:
                    Notification(win, "❌ Error",
                                 "El 2FA no está configurado. Configúralo primero.",
                                 notification_type="error")
                    return
                totp_secret = EncryptionManager.decrypt_str_with_key(
                    totp_enc, self._session_key
                )
                if not pyotp.TOTP(totp_secret).verify(totp_code):
                    Notification(win, "❌ Código inválido",
                                 "El código del autenticador es incorrecto o expiró",
                                 notification_type="error")
                    return

                # 3. re-hashear contraseña y derivar nueva session key
                new_hash  = hash_contrasena(pw_nueva)
                parts     = new_hash.split(":")
                new_salt  = parts[1] if len(parts) == 3 else self.usuario_nombre
                new_key   = EncryptionManager.derive_session_key(pw_nueva, new_salt)

                # 4. re-cifrar TOTP secret y backup codes con la nueva clave
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

                # 5. guardar todo en DB e invalidar token de confianza
                self.cursor.execute(
                    "UPDATE Usuarios SET contrasena = ?, totp_secret = ?, backup_codes = ? "
                    "WHERE id = ?",
                    (new_hash, new_totp_enc, new_backup_enc, self.usuario_actual)
                )
                clear_trust_token(self.cursor, self.conn, self.usuario_actual)
                self.conn.commit()

                # limpiar token local del config
                tokens = self.config.get("trust_tokens", {})
                tokens.pop(self.usuario_nombre, None)
                self.config.set("trust_tokens", tokens)

                # 6. actualizar session key en memoria
                self._session_key = new_key
                self._audit("Cambio de contraseña")

                Notification(self.root, "✅ Contraseña cambiada",
                             "Tu contraseña fue actualizada correctamente.\n"
                             "El token de confianza fue invalidado.",
                             notification_type="success", duration=4000)
                win.destroy()

            except Exception as e:
                Notification(win, "❌ Error", str(e), notification_type="error")

        ctk.CTkButton(
            parent, text="✅  Cambiar Contraseña",
            command=aplicar,
            fg_color=COLOR_PRIMARY, hover_color="#388E3C",
            text_color="white", font=("Arial", 12, "bold"),
            width=360, height=42, corner_radius=8
        ).pack(pady=4)

    def _build_tab_codigos(self, parent, colors):
        """Tab: visualización y regeneración de códigos de respaldo 2FA."""
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
                    Notification(parent, "📋 Copiado", "Códigos copiados al portapapeles",
                                 notification_type="success", duration=2000)
            except Exception as e:
                Notification(parent, "❌ Error", str(e), notification_type="error")

        def regenerar():
            dlg = ConfirmDialog(
                parent, "🔄 Regenerar Códigos",
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
                Notification(parent, "✅ Códigos regenerados",
                             "Guarda los nuevos códigos en un lugar seguro.",
                             notification_type="success")
            except Exception as e:
                Notification(parent, "❌ Error", str(e), notification_type="error")

        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(pady=14)
        ctk.CTkButton(btn_row, text="📋 Copiar todos", command=copiar,
                      fg_color=COLOR_SECONDARY, hover_color="#1565c0",
                      text_color="white", font=("Arial", 11, "bold"),
                      width=166, height=36, corner_radius=8).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="🔄 Regenerar", command=regenerar,
                      fg_color=COLOR_WARNING, hover_color="#F57C00",
                      text_color="white", font=("Arial", 11, "bold"),
                      width=166, height=36, corner_radius=8).pack(side="left", padx=6)

    def _refresh_backup_codes_display(self, codes_frame, colors):
        """Refresca la lista de códigos de respaldo en el frame dado."""
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
                        codes_frame, text=f"  🔑  {c}",
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
        """Tab: configuración del período de confianza de dispositivo 2FA."""
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
                # invalidar token activo si se desactiva la confianza
                clear_trust_token(self.cursor, self.conn, self.usuario_actual)
                tokens = self.config.get("trust_tokens", {})
                tokens.pop(self.usuario_nombre, None)
                self.config.set("trust_tokens", tokens)
                info_label.configure(text="✅ Siempre se solicitará el código 2FA.")
            else:
                info_label.configure(
                    text=f"✅ Guardado. El código 2FA no se pedirá durante {elegido} "
                         "tras la próxima verificación exitosa."
                )

        ctk.CTkButton(
            parent, text="💾  Guardar preferencia",
            command=guardar_trust,
            fg_color=COLOR_PRIMARY, hover_color="#388E3C",
            text_color="white", font=("Arial", 12, "bold"),
            width=280, height=42, corner_radius=8
        ).pack(pady=6)

        ctk.CTkLabel(
            parent,
            text="⚠️ Cambiar la contraseña invalida\nautomáticamente el token de confianza.",
            font=("Arial", 9), text_color=COLOR_WARNING, justify="center"
        ).pack(pady=(14, 0))

    def _save_trust_token(self):
        """Genera y guarda un token de confianza si el usuario configuró un período."""
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
        # registra una acción en la tabla Auditoria.
        # usa self.usuario_actual por defecto; acepta usuario_id explícito para eventos pre-login.
        # silencia errores para no interrumpir flujos críticos de UI.
        try:
            uid = usuario_id if usuario_id is not None else self.usuario_actual
            self.cursor.execute(
                "INSERT INTO Auditoria (accion, pdf_id, usuario_id, fecha) VALUES (?, ?, ?, ?)",
                (accion, pdf_id, uid, datetime.now().isoformat())
            )
            self.conn.commit()
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────
    # TIMEOUT de sesion por inactividad (#7) improvement 
    #     # ──────────────────────────────────────────────────────────────

    def _start_idle_tracking(self):
        """Inicia el seguimiento de inactividad; reinicia si ya estaba activo."""
        self._stop_idle_tracking()
        timeout_s = self.config.get("session_timeout_minutes", 10) * 60
        self._idle_timeout_ms  = int(timeout_s * 1000)
        self._idle_warning_ms  = int(max(timeout_s - 30, 5) * 1000)
        # bind con add="+" para no pisar otros bindings existentes
        for event in ("<Motion>", "<KeyPress>", "<ButtonPress>"):
            bid = self.root.bind(event, self._reset_idle_timer, add="+")
            self._idle_bind_ids.append((event, bid))
        self._schedule_idle_timers()

    def _stop_idle_tracking(self):
        """Cancela timers y desvincula eventos de actividad."""
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
        """(Re)programa advertencia y logout automático."""
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
        """Reinicia el contador de inactividad ante cualquier actividad."""
        if not self.usuario_actual:
            return
        self._schedule_idle_timers()

    def _idle_warning(self):
        """Muestra advertencia de cierre de sesión inminente (30 s antes)."""
        if not self.usuario_actual:
            return
        Notification(
            self.root,
            "⚠️ Sesión por expirar",
            "Sin actividad detectada.\nLa sesión se cerrará en 30 segundos.",
            notification_type="warning",
            duration=28000
        )

    def _idle_logout(self):
        """Cierra la sesión automáticamente por inactividad (sin diálogo de confirmación)."""
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
            self.root, "🔒 Sesión expirada",
            f"La sesión de {nombre} se cerró automáticamente\npor inactividad.",
            notification_type="warning", duration=5000
        )

    def completar_login(self):
         # completa el proceso de login
        self._hide_all_frames()
        self.frame_principal.pack(expand=True, fill="both")
        colors = self.get_colors()
        self.status.configure(text=f"✅ Sesión activa: {self.usuario_nombre}",
                              text_color=colors["text_primary"])
        # update user badge in navbar
        if hasattr(self, '_user_badge'):
            self._user_badge.configure(text=f" 👤 {self.usuario_nombre} ")
        Notification(
            self.root,
            "✅ Sesión Iniciada",
            f"Bienvenido, {self.usuario_nombre}!\n2FA verificado – AES-256-GCM activo",
            notification_type="success",
            duration=3000
        )
        self._audit("Login exitoso")
        self.cargar_dashboard()
        self.ver_pdfs()
        self._start_idle_tracking()

    def _logout(self):
            # cierra la sesion del usuario actual
        dlg = ConfirmDialog(
            self.root,
            "🚪 Cerrar Sesión",
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
            # Clear treeview
            for item in self.tree.get_children():
                self.tree.delete(item)
            self._reset_preview_panel()
            self.mostrar_inicial()
            Notification(
                self.root, "👋 Sesión cerrada",
                "Has cerrado sesión correctamente",
                notification_type="info", duration=2500
            )

    def cargar_dashboard(self):
         # carga el dashboard
        for widget in self.dashboard_container.winfo_children():
            widget.destroy()

        dashboard = DashboardWidget(self.dashboard_container, self.cursor, self.usuario_actual)
        dashboard.pack(fill="both", padx=20)

    def _obtener_datos_reporte_dashboard(self):
        """obtiene filas y estadisticas del inventario para reporter.py."""
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
        """Exporta reporte del dashboard usando reporter.py."""
        if not self.usuario_actual:
            Notification(self.root, "❌ Error", "No hay sesión activa.",
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
                "✅ Reporte generado",
                f"Se exportó correctamente en:\n{destino}",
                notification_type="success",
                duration=3000
            )
        except Exception as e:
            Notification(self.root, "❌ Error de reporte", str(e),
                         notification_type="error")
        finally:
            self.progress_bar.stop()

    # ──────────────────────────────────────────────────────────────
    # GESTION DE PERSONAS  — improvement #10
    # ──────────────────────────────────────────────────────────────

    def mostrar_gestion_personas(self):
        """Panel independiente para CRUD de personas (cédula, nombres, empresa)."""
        if not self.usuario_actual:
            Notification(self.root, "❌ Error", "No hay sesión activa.",
                         notification_type="error")
            return

        win = ctk.CTkToplevel(self.root)
        win.title("👥 Gestión de Personas — DatenJäger")
        win.geometry("960x620")
        win.minsize(760, 480)
        win.transient(self.root)
        win.withdraw()

        _auto_refresh_id = [None]   # mutable para cancelar el after
        _last_hash = [None]        # hash de datos para detectar cambios

        def _close_win():
            if _auto_refresh_id[0] is not None:
                try:
                    win.after_cancel(_auto_refresh_id[0])
                except Exception:
                    pass
            try:
                win.grab_release()
            except tk.TclError:
                pass
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", _close_win)
        self._show_modal_window(win)
        colors = self.get_colors()

        # ── Header ────────────────────────────────────────────────
        header = ctk.CTkFrame(win, fg_color=("#6A1B9A", "#311B92"),
                               height=52, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text="👥 Gestión de Personas",
            font=("Arial", 16, "bold"), text_color="white"
        ).pack(side="left", padx=16, pady=14)
        ctk.CTkLabel(
            header, text="Administración de titulares de documentos",
            font=("Arial", 10), text_color="#ce93d8"
        ).pack(side="left", padx=4)

        # ── Barra de búsqueda + botones de acción ─────────────────
        action_bar = ctk.CTkFrame(win, fg_color=("#f3e5f5", "#1e1533"),
                                   corner_radius=10)
        action_bar.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(action_bar, text="🔍",
                     font=("Arial", 14)).pack(side="left", padx=(14, 4), pady=8)
        entry_buscar = ctk.CTkEntry(action_bar,
                                     placeholder_text="Buscar por cédula, nombre o empresa…",
                                     width=300, height=30, corner_radius=6)
        entry_buscar.pack(side="left", padx=(0, 10), pady=8)

        lbl_count = ctk.CTkLabel(action_bar, text="",
                                  font=("Arial", 10),
                                  text_color=colors["text_secondary"])
        lbl_count.pack(side="right", padx=14)

        # ── Treeview con personas ─────────────────────────────────
        tree_wrapper = ctk.CTkFrame(win, fg_color=("#ffffff", "#1e2a4a"),
                                     corner_radius=10)
        tree_wrapper.pack(fill="both", expand=True, padx=14, pady=(4, 6))

        style = ttk.Style()
        style.configure("Persona.Treeview",
                         rowheight=28, font=("Arial", 10),
                         background="#1e2a4a" if ctk.get_appearance_mode() == "Dark" else "#ffffff",
                         foreground="#e0e0e0" if ctk.get_appearance_mode() == "Dark" else "#1a237e",
                         fieldbackground="#1e2a4a" if ctk.get_appearance_mode() == "Dark" else "#ffffff")
        style.configure("Persona.Treeview.Heading",
                         font=("Arial", 10, "bold"),
                         background="#6A1B9A", foreground="white")
        style.map("Persona.Treeview", background=[("selected", "#9C27B0")])

        cols = ("ID", "Cédula", "Nombres", "Empresa", "Documentos")
        tree = ttk.Treeview(tree_wrapper, columns=cols, show="headings",
                             style="Persona.Treeview")

        col_widths = {"ID": 50, "Cédula": 130, "Nombres": 260,
                      "Empresa": 220, "Documentos": 100}
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=col_widths[col], anchor="w" if col != "Documentos" else "center")

        vsb = ttk.Scrollbar(tree_wrapper, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        vsb.pack(side="right", fill="y", pady=4)

        tree.tag_configure("odd",  background="#1e1533" if ctk.get_appearance_mode() == "Dark" else "#f3e5f5")
        tree.tag_configure("even", background="#16213e" if ctk.get_appearance_mode() == "Dark" else "#ffffff")

        # ── Carga de datos con detección de cambios ─────────────
        def _fetch_rows(filtro=""):
            """Ejecuta la query y devuelve las filas."""
            query = (
                "SELECT pe.id, pe.cedula, pe.nombres, "
                "       COALESCE(pe.empresa, '—'), "
                "       COUNT(p.id) AS total_docs "
                "FROM Personas pe "
                "LEFT JOIN PDFs p ON p.persona_id = pe.id "
                "WHERE 1=1 "
            )
            params = []
            if filtro.strip():
                query += (
                    "AND (pe.cedula LIKE ? OR pe.nombres LIKE ? "
                    "     OR pe.empresa LIKE ?) "
                )
                like = f"%{filtro.strip()}%"
                params.extend([like, like, like])
            query += "GROUP BY pe.id ORDER BY pe.nombres ASC"
            with self._db_lock:
                self.cursor.execute(query, params)
                return self.cursor.fetchall()

        def _rows_hash(rows):
            """Hash rápido para detectar cambios en los datos."""
            import hashlib
            return hashlib.md5(str(rows).encode()).hexdigest()

        def _cargar(filtro="", force=False):
            try:
                rows = _fetch_rows(filtro)
                new_hash = _rows_hash(rows)
                if not force and new_hash == _last_hash[0]:
                    return  # sin cambios, no redibujar
                _last_hash[0] = new_hash

                for row in tree.get_children():
                    tree.delete(row)
                for i, (pid, cedula, nombres, empresa, docs) in enumerate(rows):
                    tag = "odd" if i % 2 == 0 else "even"
                    tree.insert("", "end",
                                values=(pid, cedula, nombres, empresa, docs),
                                tags=(tag,))
                lbl_count.configure(
                    text=f"{len(rows)} persona{'s' if len(rows) != 1 else ''}"
                )
            except Exception as e:
                Notification(self.root, "❌ Error al cargar personas",
                             str(e), notification_type="error")

        def _filtrar(*_args):
            _cargar(entry_buscar.get(), force=True)

        entry_buscar.bind("<KeyRelease>", _filtrar)

        # ── Auto-refresh cada 10 segundos ─────────────────────────
        def _auto_refresh():
            try:
                if win.winfo_exists():
                    _cargar(entry_buscar.get())
                    _auto_refresh_id[0] = win.after(10000, _auto_refresh)
            except tk.TclError:
                pass  # ventana ya destruida

        _auto_refresh_id[0] = win.after(10000, _auto_refresh)

        # ── Formulario flotante para Agregar / Editar ─────────────
        def _abrir_formulario(modo="agregar", datos=None):
            """Abre sub-ventana para agregar o editar una persona.
            modo: 'agregar' | 'editar'
            datos: (id, cedula, nombres, empresa) cuando modo='editar'
            """
            form = ctk.CTkToplevel(win)
            titulo = "➕ Agregar Persona" if modo == "agregar" else "✏️ Editar Persona"
            form.title(titulo)
            form.geometry("440x380")
            form.resizable(False, False)
            form.transient(win)
            form.configure(fg_color=colors["bg_secondary"])
            form.withdraw()

            ctk.CTkLabel(
                form, text=titulo,
                font=("Arial", 16, "bold"),
                text_color=colors["text_primary"]
            ).pack(pady=(18, 4))

            sep = ctk.CTkFrame(form, height=1, fg_color="#9C27B0")
            sep.pack(fill="x", padx=40, pady=(0, 12))

            def _add_field(parent, label, placeholder, value="", state="normal"):
                ctk.CTkLabel(parent, text=label,
                             text_color=colors["text_primary"],
                             font=("Arial", 11, "bold")).pack(anchor="w", padx=50)
                e = ctk.CTkEntry(parent, placeholder_text=placeholder,
                                 width=340, height=36, corner_radius=8,
                                 border_width=2, font=("Arial", 11),
                                 state=state)
                e.pack(pady=(2, 8))
                if value:
                    if state == "disabled":
                        e.configure(state="normal")
                    e.insert(0, value)
                    if state == "disabled":
                        e.configure(state="disabled")
                return e

            if modo == "editar" and datos:
                e_cedula  = _add_field(form, "Cédula:", "Número de cédula",
                                        value=str(datos[1]), state="disabled")
                e_nombres = _add_field(form, "Nombres:", "Nombres completos",
                                        value=str(datos[2]))
                e_empresa = _add_field(form, "Empresa:", "Nombre de la empresa",
                                        value=str(datos[3]) if datos[3] and datos[3] != "—" else "")
            else:
                e_cedula  = _add_field(form, "Cédula:", "Número de cédula")
                e_nombres = _add_field(form, "Nombres:", "Nombres completos")
                e_empresa = _add_field(form, "Empresa:", "Nombre de la empresa")

            def _guardar():
                cedula  = e_cedula.get().strip()
                nombres = e_nombres.get().strip()
                empresa = e_empresa.get().strip() or None

                if not cedula or not nombres:
                    Notification(form, "❌ Error",
                                 "Cédula y nombres son obligatorios.",
                                 notification_type="error")
                    return

                try:
                    with self._db_lock:
                        if modo == "agregar":
                            self.cursor.execute(
                                "SELECT id FROM Personas WHERE cedula = ?",
                                (cedula,)
                            )
                            if self.cursor.fetchone():
                                Notification(form, "⚠️ Duplicado",
                                             f"Ya existe una persona con cédula {cedula}.",
                                             notification_type="warning")
                                return
                            self.cursor.execute(
                                "INSERT INTO Personas (cedula, nombres, empresa) "
                                "VALUES (?, ?, ?)",
                                (cedula, nombres, empresa)
                            )
                            self._audit("Agregar persona (Panel Personas)")
                            msg = f"Persona '{nombres}' registrada."
                        else:
                            self.cursor.execute(
                                "UPDATE Personas SET nombres = ?, empresa = ? "
                                "WHERE id = ?",
                                (nombres, empresa, datos[0])
                            )
                            self._audit("Editar persona (Panel Personas)")
                            msg = f"Persona '{nombres}' actualizada."
                        self.conn.commit()

                    Notification(self.root, "✅ Guardado", msg,
                                 notification_type="success", duration=2500)
                    form.destroy()
                    _cargar(entry_buscar.get())
                except Exception as exc:
                    self.conn.rollback()
                    Notification(form, "❌ Error", str(exc),
                                 notification_type="error")

            btn_row = ctk.CTkFrame(form, fg_color="transparent")
            btn_row.pack(pady=14)

            ctk.CTkButton(
                btn_row, text="Cancelar",
                command=form.destroy,
                fg_color="#9E9E9E", hover_color="#757575",
                text_color="white", font=("Arial", 11, "bold"),
                corner_radius=8, width=150, height=38
            ).pack(side="left", padx=6)

            ctk.CTkButton(
                btn_row,
                text="💾 Guardar" if modo == "editar" else "➕ Agregar",
                command=_guardar,
                fg_color="#6A1B9A" if modo == "agregar" else COLOR_PRIMARY,
                hover_color="#4A148C" if modo == "agregar" else "#388E3C",
                text_color="white", font=("Arial", 11, "bold"),
                corner_radius=8, width=150, height=38
            ).pack(side="left", padx=6)

            # mostrar la ventana del formulario
            form.after(200, lambda: (
                form.update_idletasks(),
                form.deiconify(),
                form.lift(),
                form.focus_force(),
                form.grab_set()
            ))
            form.wait_window()

        # ── Acciones: Agregar / Editar / Eliminar ─────────────────
        def _agregar():
            _abrir_formulario("agregar")

        def _editar():
            sel = tree.selection()
            if not sel:
                Notification(win, "⚠️ Selecciona una persona",
                             "Haz clic en una persona de la lista para editarla.",
                             notification_type="warning")
                return
            vals = tree.item(sel[0])["values"]
            # vals: (id, cédula, nombres, empresa, docs)
            _abrir_formulario("editar", datos=(vals[0], vals[1], vals[2], vals[3]))

        def _eliminar():
            sel = tree.selection()
            if not sel:
                Notification(win, "⚠️ Selecciona una persona",
                             "Haz clic en una persona de la lista para eliminarla.",
                             notification_type="warning")
                return
            vals = tree.item(sel[0])["values"]
            pid, cedula, nombres, empresa, docs = vals

            if int(docs) > 0:
                msg = (f"'{nombres}' tiene {docs} documento(s) vinculado(s).\n"
                       "Si la eliminas, los documentos quedarán sin titular.\n"
                       "¿Continuar?")
            else:
                msg = f"¿Eliminar a '{nombres}' (cédula {cedula})?"

            dlg = ConfirmDialog(
                win, "🗑️ Eliminar Persona", msg,
                confirm_text="Eliminar", danger=True
            )
            if not dlg.result:
                return
            try:
                with self._db_lock:
                    self.cursor.execute(
                        "DELETE FROM Personas WHERE id = ?", (pid,)
                    )
                    self._audit("Eliminar persona (Panel Personas)")
                    self.conn.commit()
                Notification(self.root, "✅ Eliminada",
                             f"Persona '{nombres}' eliminada correctamente.",
                             notification_type="success", duration=2500)
                _cargar(entry_buscar.get())
            except Exception as exc:
                self.conn.rollback()
                Notification(win, "❌ Error", str(exc),
                             notification_type="error")

        # ── Barra inferior de botones ─────────────────────────────
        bottom_bar = ctk.CTkFrame(win, fg_color="transparent")
        bottom_bar.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkButton(
            bottom_bar, text="➕ Agregar Persona",
            command=_agregar,
            fg_color="#6A1B9A", hover_color="#4A148C",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=160, height=38
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            bottom_bar, text="✏️ Editar",
            command=_editar,
            fg_color=COLOR_SECONDARY, hover_color="#1565c0",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=120, height=38
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            bottom_bar, text="🗑️ Eliminar",
            command=_eliminar,
            fg_color=COLOR_ERROR, hover_color="#C62828",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=120, height=38
        ).pack(side="left", padx=6)

        lbl_refresh = ctk.CTkLabel(
            bottom_bar, text="", font=("Arial", 9),
            text_color=colors["text_secondary"]
        )
        lbl_refresh.pack(side="right", padx=(0, 6))

        def _manual_refresh():
            _cargar(entry_buscar.get(), force=True)
            from datetime import datetime as _dt
            lbl_refresh.configure(text=f"Última: {_dt.now().strftime('%H:%M:%S')}")

        ctk.CTkButton(
            bottom_bar, text="🔄 Refrescar",
            command=_manual_refresh,
            fg_color=("#78909c", "#546e7a"), hover_color="#455a64",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=120, height=38
        ).pack(side="right", padx=6)

        # doble clic para editar
        tree.bind("<Double-1>", lambda _e: _editar())

        # carga inicial
        _cargar(force=True)

    # LOG para auditoria — UI imrpovement
 

    def mostrar_auditoria(self):
        """abre ventana con el visor de log de auditoria con filtros."""
        if not self.usuario_actual:
            Notification(self.root, "❌ Error", "No hay sesión activa.",
                         notification_type="error")
            return

        win = ctk.CTkToplevel(self.root)
        win.title("📋 Log de Auditoría — DatenJäger")
        win.geometry("960x600")
        win.minsize(760, 460)
        win.transient(self.root)
        win.withdraw()

        def _close_audit_win():
            try:
                win.grab_release()
            except tk.TclError:
                pass
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", _close_audit_win)
        self._show_modal_window(win)
        colors = self.get_colors()

        # ── Header 
        header = ctk.CTkFrame(win, fg_color=("#1a237e", "#0d1b3e"),
                               height=52, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text="📋 Log de Auditoría",
            font=("Arial", 16, "bold"), text_color="white"
        ).pack(side="left", padx=16, pady=14)
        ctk.CTkLabel(
            header, text="Historial de acciones del sistema",
            font=("Arial", 10), text_color="#90caf9"
        ).pack(side="left", padx=4)

        # ── Filtros 
        filter_card = ctk.CTkFrame(win, fg_color=("#e8f0fe", "#1e2a4a"),
                                    corner_radius=10)
        filter_card.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(filter_card, text="Desde:",
                     font=("Arial", 11), text_color=colors["text_secondary"]
                     ).pack(side="left", padx=(14, 2), pady=8)
        entry_desde = ctk.CTkEntry(filter_card, placeholder_text="YYYY-MM-DD",
                                    width=110, height=30, corner_radius=6)
        entry_desde.pack(side="left", padx=(0, 10), pady=8)

        ctk.CTkLabel(filter_card, text="Hasta:",
                     font=("Arial", 11), text_color=colors["text_secondary"]
                     ).pack(side="left", padx=(0, 2))
        entry_hasta = ctk.CTkEntry(filter_card, placeholder_text="YYYY-MM-DD",
                                    width=110, height=30, corner_radius=6)
        entry_hasta.pack(side="left", padx=(0, 10), pady=8)

        ctk.CTkLabel(filter_card, text="Acción:",
                     font=("Arial", 11), text_color=colors["text_secondary"]
                     ).pack(side="left", padx=(0, 2))
        entry_accion = ctk.CTkEntry(filter_card, placeholder_text="Buscar acción…",
                                     width=200, height=30, corner_radius=6)
        entry_accion.pack(side="left", padx=(0, 10), pady=8)

        # contador de registros (se actualiza al cargar)
        lbl_count = ctk.CTkLabel(filter_card, text="",
                                  font=("Arial", 10), text_color=colors["text_secondary"])
        lbl_count.pack(side="right", padx=14)

        # ── Treeview 
        tree_wrapper = ctk.CTkFrame(win, fg_color=("#ffffff", "#1e2a4a"),
                                     corner_radius=10)
        tree_wrapper.pack(fill="both", expand=True, padx=14, pady=(4, 6))

        style = ttk.Style()
        style.configure("Audit.Treeview",
                         rowheight=26, font=("Arial", 10),
                         background="#1e2a4a" if ctk.get_appearance_mode() == "Dark" else "#ffffff",
                         foreground="#e0e0e0" if ctk.get_appearance_mode() == "Dark" else "#1a237e",
                         fieldbackground="#1e2a4a" if ctk.get_appearance_mode() == "Dark" else "#ffffff")
        style.configure("Audit.Treeview.Heading",
                         font=("Arial", 10, "bold"),
                         background="#1a237e", foreground="white")
        style.map("Audit.Treeview", background=[("selected", "#2196F3")])

        cols = ("Fecha", "Acción", "PDF_ID", "Usuario")
        tree = ttk.Treeview(tree_wrapper, columns=cols, show="headings",
                             style="Audit.Treeview")

        col_widths = {"Fecha": 150, "Acción": 380, "PDF_ID": 80, "Usuario": 160}
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=col_widths[col], anchor="w")

        vsb = ttk.Scrollbar(tree_wrapper, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        vsb.pack(side="right", fill="y", pady=4)

        # filas alternas de color
        tree.tag_configure("odd",  background="#1e2a4a" if ctk.get_appearance_mode() == "Dark" else "#f5f7ff")
        tree.tag_configure("even", background="#16213e" if ctk.get_appearance_mode() == "Dark" else "#ffffff")

        # ── Carga de datos (TODO el sistema, sin filtro de usuario) ──
        def _cargar(desde="", hasta="", accion_txt=""):
            for row in tree.get_children():
                tree.delete(row)
            try:
                query = (
                    "SELECT a.fecha, a.accion, COALESCE(a.pdf_id,'—'), "
                    "       COALESCE(u.nombre,'—') "
                    "FROM Auditoria a "
                    "LEFT JOIN Usuarios u ON a.usuario_id = u.id "
                    "WHERE 1=1 "
                )
                params = []
                if desde.strip():
                    query += "AND a.fecha >= ? "
                    params.append(desde.strip())
                if hasta.strip():
                    query += "AND a.fecha <= ? "
                    params.append(hasta.strip() + "T23:59:59")
                if accion_txt.strip():
                    query += "AND a.accion LIKE ? "
                    params.append(f"%{accion_txt.strip()}%")
                query += "ORDER BY a.fecha DESC LIMIT 5000"

                with self._db_lock:
                    self.cursor.execute(query, params)
                    rows = self.cursor.fetchall()

                for i, (fecha, accion, pdf_id, usuario) in enumerate(rows):
                    fecha_fmt = fecha[:19].replace("T", "  ") if fecha else "—"
                    tag = "odd" if i % 2 == 0 else "even"
                    tree.insert("", "end",
                                values=(fecha_fmt, accion, pdf_id, usuario),
                                tags=(tag,))
                lbl_count.configure(
                    text=f"{len(rows)} registro{'s' if len(rows) != 1 else ''}"
                )
            except Exception as e:
                Notification(self.root, "❌ Error al cargar auditoría",
                             str(e), notification_type="error")

        def _aplicar_filtros():
            _cargar(entry_desde.get(), entry_hasta.get(), entry_accion.get())

        def _limpiar_filtros():
            entry_desde.delete(0, tk.END)
            entry_hasta.delete(0, tk.END)
            entry_accion.delete(0, tk.END)
            _cargar()

        # ── Visor de Log del Backend (archivo) ────────────────────
        def _ver_log_backend():
            """Abre una sub-ventana con el contenido raw del log del sistema."""
            import glob
            log_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "datenjager.log"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.log"),
            ]
            # buscar también logs rotados
            log_paths += glob.glob(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "*.log")
            )

            log_content = ""
            found_log = None
            for lp in log_paths:
                if os.path.isfile(lp):
                    try:
                        with open(lp, "r", encoding="utf-8", errors="replace") as f:
                            log_content = f.read()
                        found_log = lp
                        break
                    except Exception:
                        continue

            # si no hay archivo de log, generar uno ahora con info del sistema
            if not found_log:
                import sys
                import platform
                log_content = (
                    "═══ DatenJäger — Información del Sistema ═══\n\n"
                    f"Python:     {sys.version}\n"
                    f"Plataforma: {platform.platform()}\n"
                    f"SQLite:     {__import__('sqlite3').sqlite_version}\n\n"
                    "═══ Log de Auditoría exportado ═══\n\n"
                )
                try:
                    with self._db_lock:
                        self.cursor.execute(
                            "SELECT a.fecha, a.accion, COALESCE(a.pdf_id,'—'), "
                            "COALESCE(u.nombre,'—') FROM Auditoria a "
                            "LEFT JOIN Usuarios u ON a.usuario_id = u.id "
                            "ORDER BY a.fecha DESC LIMIT 500"
                        )
                        for r in self.cursor.fetchall():
                            fecha_f = r[0][:19].replace('T', ' ') if r[0] else '—'
                            log_content += f"[{fecha_f}] {r[1]} | PDF={r[2]} | User={r[3]}\n"
                except Exception as ex:
                    log_content += f"Error leyendo BD: {ex}\n"
                found_log = "(generado en memoria)"

            log_win = ctk.CTkToplevel(win)
            log_win.title("📜 Log del Sistema — Backend")
            log_win.geometry("820x540")
            log_win.transient(win)
            log_win.configure(fg_color=("#1b1b2f", "#0d0d1a"))
            log_win.withdraw()

            hdr = ctk.CTkFrame(log_win, fg_color=("#263238", "#1a1a2e"),
                                height=42, corner_radius=0)
            hdr.pack(fill="x")
            hdr.pack_propagate(False)
            ctk.CTkLabel(
                hdr, text="📜 Log del Sistema",
                font=("Arial", 14, "bold"), text_color="#4fc3f7"
            ).pack(side="left", padx=14, pady=10)
            ctk.CTkLabel(
                hdr, text=os.path.basename(found_log) if found_log else "",
                font=("Arial", 9), text_color="#78909c"
            ).pack(side="left", padx=6)

            txt = ctk.CTkTextbox(
                log_win, font=("Courier", 10),
                fg_color=("#0d1117", "#0d0d1a"),
                text_color="#c9d1d9",
                corner_radius=0,
                wrap="none"
            )
            txt.pack(fill="both", expand=True, padx=0, pady=0)
            txt.insert("1.0", log_content)
            txt.configure(state="disabled")
            # scroll al final
            txt.see("end")

            btn_bar = ctk.CTkFrame(log_win, fg_color="transparent")
            btn_bar.pack(fill="x", padx=10, pady=6)

            ctk.CTkButton(
                btn_bar, text="Cerrar", command=log_win.destroy,
                fg_color="#546e7a", hover_color="#455a64",
                corner_radius=8, width=100, height=32,
                font=("Arial", 10, "bold")
            ).pack(side="right")

            log_win.after(200, lambda: (
                log_win.update_idletasks(),
                log_win.deiconify(),
                log_win.lift(),
                log_win.focus_force()
            ))

        # botones de acción en filter_card (se agregan después de definir _cargar)
        ctk.CTkButton(
            filter_card, text="🔍 Filtrar",
            command=_aplicar_filtros,
            fg_color=COLOR_SECONDARY, hover_color="#1565c0",
            font=("Arial", 10, "bold"), corner_radius=7,
            width=86, height=30
        ).pack(side="left", padx=(0, 4), pady=8)

        ctk.CTkButton(
            filter_card, text="✖ Limpiar",
            command=_limpiar_filtros,
            fg_color=("#78909c", "#546e7a"), hover_color="#455a64",
            font=("Arial", 10, "bold"), corner_radius=7,
            width=80, height=30
        ).pack(side="left", pady=8)

        # ── Barra inferior con botón de Log del Sistema ───────────
        bottom_bar = ctk.CTkFrame(win, fg_color="transparent")
        bottom_bar.pack(fill="x", padx=14, pady=(0, 8))

        ctk.CTkButton(
            bottom_bar, text="📜 Log del Sistema",
            command=_ver_log_backend,
            fg_color="#263238", hover_color="#37474f",
            text_color="#4fc3f7", font=("Arial", 10, "bold"),
            corner_radius=8, width=160, height=34
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            bottom_bar, text="🔄 Refrescar",
            command=_aplicar_filtros,
            fg_color=("#78909c", "#546e7a"), hover_color="#455a64",
            font=("Arial", 10, "bold"), corner_radius=8,
            width=110, height=34
        ).pack(side="right", padx=4)

        # Enter en cualquier filtro aplica búsqueda
        for e in (entry_desde, entry_hasta, entry_accion):
            e.bind("<Return>", lambda _ev: _aplicar_filtros())

        # carga inicial completa (todo el log)
        _cargar()

    def mostrar_agregar_pdf(self):
        """Muestra ventana para agregar PDF"""
        if not self.usuario_actual:
            Notification(
                self.root, "❌ Error",
                "No hay usuario autenticado",
                notification_type="error"
            )
            return

        colors = self.get_colors()
        add_window = ctk.CTkToplevel(self.root)
        add_window.title("➕ Agregar PDF")
        add_window.geometry("500x640")
        add_window.resizable(False, False)
        add_window.transient(self.root)
        add_window.configure(fg_color=colors["bg_secondary"])
        add_window.withdraw()

        ctk.CTkLabel(
            add_window,
            text="➕ Agregar Nuevo PDF",
            font=("Arial", 20, "bold"),
            text_color=colors["text_primary"]
        ).pack(pady=(20, 4))

        ctk.CTkLabel(
            add_window,
            text="El archivo se encriptará con AES-256-GCM antes de guardarse",
            font=("Arial", 10),
            text_color=COLOR_SECONDARY
        ).pack(pady=(0, 12))

        self.selected_file = None

        btn_buscar = ctk.CTkButton(
            add_window,
            text="📁 Seleccionar Archivo PDF",
            command=self.seleccionar_archivo,
            fg_color=COLOR_PRIMARY,
            hover_color="#388E3C",
            text_color="white",
            font=("Arial", 12, "bold"),
            corner_radius=8,
            width=300, height=44
        )
        btn_buscar.pack(pady=8)

        self.label_file = ctk.CTkLabel(
            add_window,
            text="📄 Ningún archivo seleccionado",
            text_color=colors["text_secondary"],
            font=("Arial", 10)
        )
        self.label_file.pack(pady=4)

        sep = ctk.CTkFrame(add_window, height=1, fg_color=("#cccccc", "#3a3a3a"))
        sep.pack(fill="x", padx=40, pady=8)

        def add_labeled_entry(parent, label, placeholder, width=360):
            ctk.CTkLabel(parent, text=label,
                         text_color=colors["text_primary"],
                         font=("Arial", 11, "bold")).pack(anchor="w", padx=60)
            e = ctk.CTkEntry(parent, placeholder_text=placeholder,
                             width=width, height=38, corner_radius=8,
                             border_width=2, font=("Arial", 11))
            e.pack(pady=(4, 8))
            return e

        self.entry_descripcion = add_labeled_entry(add_window, "Descripción:", "Descripción del documento")
        self.entry_cedula       = add_labeled_entry(add_window, "Cédula:", "Número de cédula")
        self.entry_nombres      = add_labeled_entry(add_window, "Nombres completos:", "Nombres del titular")
        self.entry_empresa      = add_labeled_entry(add_window, "Empresa:", "Nombre de la empresa")

        ctk.CTkButton(
            add_window,
            text="✅  Agregar y Encriptar (AES-256-GCM)",
            command=lambda: self.procesar_agregar_pdf(add_window),
            fg_color=COLOR_SECONDARY,
            hover_color="#1565c0",
            text_color="white",
            font=("Arial", 12, "bold"),
            corner_radius=8,
            width=340, height=44
        ).pack(pady=10)

        ctk.CTkButton(
            add_window, text="Cancelar",
            command=add_window.destroy,
            fg_color="#9E9E9E", hover_color="#757575",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=180, height=34
        ).pack(pady=(0, 16))

        self._show_modal_window(add_window, delay_ms=250)

    def seleccionar_archivo(self):
         # selecciona un archivo PDF
        self.selected_file = filedialog.askopenfilename(
            filetypes=[("PDF files", "*.pdf")]
        )
        if self.selected_file:
            self.label_file.configure(text=f"📄 {os.path.basename(self.selected_file)}")

    def procesar_agregar_pdf(self, window):
        # procesa la adicion de un PDF: encripta en segundo plano, guarda en BD en hilo principal
        if not self.selected_file:
            Notification(self.root, "❌ Error", "Selecciona un archivo PDF",
                         notification_type="error")
            return

        descripcion = self.entry_descripcion.get().strip()
        cedula      = self.entry_cedula.get().strip()
        nombres     = self.entry_nombres.get().strip()
        empresa     = self.entry_empresa.get().strip()

        if not cedula or not nombres:
            Notification(self.root, "❌ Error", "Cédula y nombres son requeridos",
                         notification_type="error")
            return

        self.progress_bar.start("Encriptando y agregando PDF...")

        # capturar el estado para el hilo en segundo plano para evitar el cierre de atributos

        # esto podría cambiar mientras el hilo se ejecuta 
        selected_file  = self.selected_file
        usuario_nombre = self.usuario_nombre
        usuario_actual = self.usuario_actual

        def encrypt_task():
            try:
                with open(selected_file, 'rb') as f:
                    datos_originales = f.read()
                datos_enc = EncryptionManager.encrypt_data(datos_originales, usuario_nombre)
                tamano    = len(datos_originales)
                nombre    = os.path.basename(selected_file)
                # transferir la escritura de la base de datos al hilo principal
                self.root.after(0, lambda: self._save_pdf_to_db(
                    datos_enc, tamano, nombre, descripcion,
                    cedula, nombres, empresa, usuario_actual, window
                ))
            except Exception as e:
                self.root.after(0, lambda err=e: self._on_pdf_add_error(err))
                self.root.after(0, self.progress_bar.stop)

        threading.Thread(target=encrypt_task, daemon=True).start()

    def ver_pdfs(self):
        # muestra todos los PDFs
        if not self.usuario_actual:
            return

        self.progress_bar.start("Cargando PDFs...")

        try:
            self.cursor.execute("""
                SELECT p.id, p.nombre, p.descripcion, p.tamano,
                       p.fecha_subida, pe.cedula, pe.nombres, pe.empresa
                FROM PDFs p
                LEFT JOIN Personas pe ON p.persona_id = pe.id
                WHERE p.usuario_id = ?
                ORDER BY p.fecha_subida DESC
            """, (self.usuario_actual,))

            rows = self.cursor.fetchall()
            self._populate_treeview(rows)

            colors = self.get_colors()
            self.status.configure(
                text=f"✅ Se muestran {len(rows)} PDFs (Encriptados)",
                text_color=colors["text_primary"]
            )
        except Exception as e:
            Notification(self.root, "❌ Error", str(e), notification_type="error")
        finally:
            self.progress_bar.stop()

    def buscar_pdfs(self):
        # busca PDFs según termino
        term = self.entry_busqueda.get().strip()

        if not term:
            self.ver_pdfs()
            return

        self.progress_bar.start(f"Buscando '{term}'...")

        try:
            self.cursor.execute("""
                SELECT p.id, p.nombre, p.descripcion, p.tamano,
                       p.fecha_subida, pe.cedula, pe.nombres, pe.empresa
                FROM PDFs p
                LEFT JOIN Personas pe ON p.persona_id = pe.id
                WHERE p.usuario_id = ? AND (
                    p.nombre LIKE ? OR p.descripcion LIKE ?
                    OR pe.cedula LIKE ? OR pe.nombres LIKE ?
                    OR pe.empresa LIKE ?
                )
            """, (self.usuario_actual,
                  f"%{term}%", f"%{term}%", f"%{term}%", f"%{term}%", f"%{term}%"))

            rows = self.cursor.fetchall()
            self._populate_treeview(rows)

            colors = self.get_colors()
            self.status.configure(
                text=f"✅ Se muestran {len(rows)} resultados",
                text_color=colors["text_primary"]
            )
            Notification(
                self.root,
                "✅ Búsqueda completada",
                f"Se encontraron {len(rows)} PDF(s) encriptados",
                notification_type="success",
                duration=2000
            )
        except Exception as e:
            Notification(self.root, "❌ Error", str(e), notification_type="error")
        finally:
            self.progress_bar.stop()

    def mostrar_detalles_pdf(self):
        # muestra detalles de un PDF
        selected = self.tree.selection()

        if not selected:
            Notification(
                self.root, "⚠️ Advertencia",
                "Selecciona un PDF de la lista",
                notification_type="warning"
            )
            return

        values = self.tree.item(selected[0])['values']
        pdf_id, pdf_nombre, descripcion, tamano, fecha, cedula, nombres, empresa = values

        colors = self.get_colors()
        details_window = ctk.CTkToplevel(self.root)
        details_window.title("ℹ️ Detalles del PDF")
        details_window.geometry("460x680")
        details_window.resizable(False, False)
        details_window.transient(self.root)
        details_window.configure(fg_color=colors["bg_secondary"])
        details_window.withdraw()

        ctk.CTkLabel(
            details_window, text="📋 Detalles del Documento",
            font=("Arial", 18, "bold"),
            text_color=colors["text_primary"]
        ).pack(pady=(20, 4))

        sep = ctk.CTkFrame(details_window, height=1, fg_color=COLOR_SECONDARY)
        sep.pack(fill="x", padx=30)

        info_frame = ctk.CTkFrame(
            details_window, fg_color=("#f0f4ff", "#1a2540"),
            corner_radius=10
        )
        info_frame.pack(padx=30, pady=14, fill="x")

        def info_row(label, value):
            row = ctk.CTkFrame(info_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(
                row, text=label, font=("Arial", 11, "bold"),
                text_color=colors["text_secondary"], width=120, anchor="w"
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=str(value) if value else "—",
                font=("Arial", 11),
                text_color=colors["text_primary"],
                wraplength=250, anchor="w"
            ).pack(side="left")

        info_row("🆔  ID:", pdf_id)
        info_row("📄  Nombre:", pdf_nombre)
        info_row("📝  Descripción:", descripcion)
        info_row("💾  Tamaño:", tamano)
        info_row("📅  Fecha:", fecha)
        info_row("🪪  Cédula:", cedula)
        info_row("👤  Nombres:", nombres)
        info_row("🏢  Empresa:", empresa)
        info_row("🔒  Encriptación:", "AES-256-GCM")

        btn_row = ctk.CTkFrame(details_window, fg_color="transparent")
        btn_row.pack(pady=14)

        ctk.CTkButton(
            btn_row, text="📂 Abrir",
            command=lambda: self.abrir_pdf_id(pdf_id, details_window),
            fg_color=COLOR_SECONDARY, hover_color="#1565c0",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=150, height=40
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            btn_row, text="⬇️ Exportar",
            command=lambda: (details_window.destroy(), self.exportar_pdf()),
            fg_color="#00897B", hover_color="#00695C",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=150, height=40
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            details_window, text="Cerrar",
            command=details_window.destroy,
            fg_color="#9E9E9E", hover_color="#757575",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=200, height=36
        ).pack(pady=(0, 16))

        self._show_modal_window(details_window, delay_ms=250)

    def abrir_pdf_doble_click(self):
        # abre un PDF con doble click
        selected = self.tree.selection()

        if not selected:
            return

        values = self.tree.item(selected[0])['values']
        pdf_id = values[0]
        self.abrir_pdf_id(pdf_id)

    def abrir_pdf_id(self, pdf_id, window=None):
        # abre un PDF: consulta BD en hilo principal, desencripta en segundo plano
        self.progress_bar.start("Desencriptando PDF...")

        try:
            self.cursor.execute(
                "SELECT datos, nombre, datos_encriptados FROM PDFs WHERE id = ? AND usuario_id = ?",
                (pdf_id, self.usuario_actual)
            )
            result = self.cursor.fetchone()
        except Exception as e:
            self.progress_bar.stop()
            Notification(self.root, "❌ Error", str(e), notification_type="error")
            return

        if not result:
            self.progress_bar.stop()
            Notification(self.root, "❌ Error", "PDF no encontrado", notification_type="error")
            return

        datos_enc, nombre, encriptado = result
        self._audit("Abrir / Descifrar PDF", pdf_id=pdf_id)
        usuario_nombre = self.usuario_nombre

        def decrypt_task():
            try:
                datos = (EncryptionManager.decrypt_data(bytes(datos_enc), usuario_nombre)
                         if encriptado else bytes(datos_enc))
                # pasar bytes directamente al visor — el PDF descifrado nunca toca el disco
                self.root.after(0, lambda d=datos: self._abrir_visor_pdf(d, nombre, window))
            except Exception as e:
                self.root.after(
                    0,
                    lambda err=e: Notification(
                        self.root, "❌ Error",
                        f"No se pudo abrir el PDF: {err}",
                        notification_type="error"
                    )
                )
            finally:
                self.root.after(0, self.progress_bar.stop)

        threading.Thread(target=decrypt_task, daemon=True).start()

    def eliminar_pdf(self):
         # Elimina un PDF seleccionado usando el dialogo 
        selected = self.tree.selection()

        if not selected:
            Notification(
                self.root, "⚠️ Advertencia",
                "Selecciona un PDF de la lista",
                notification_type="warning"
            )
            return

        pdf_id = self.tree.item(selected[0])['values'][0]
        pdf_nombre = self.tree.item(selected[0])['values'][1]

        dlg = ConfirmDialog(
            self.root,
            "🗑️  Eliminar PDF",
            f"¿Eliminar permanentemente\n\"{pdf_nombre}\"?\n\nEsta acción no se puede deshacer.",
            confirm_text="Sí, eliminar",
            cancel_text="Cancelar",
            danger=True
        )
        if not dlg.result:
            return

        self.progress_bar.start("Eliminando PDF…")

        try:
            self.cursor.execute(
                "DELETE FROM PDFs WHERE id = ? AND usuario_id = ?",
                (pdf_id, self.usuario_actual)
            )

            if self.cursor.rowcount == 0:
                Notification(self.root, "❌ Error", "PDF no encontrado",
                             notification_type="error")
                return

            self.cursor.execute(
                "INSERT INTO Auditoria (accion, pdf_id, usuario_id, fecha) VALUES (?, ?, ?, ?)",
                ("Eliminar PDF", pdf_id, self.usuario_actual, datetime.now().isoformat())
            )

            self.conn.commit()
            self._reset_preview_panel()
            Notification(self.root, "✅ Eliminado",
                         f"'{pdf_nombre}' eliminado correctamente",
                         notification_type="success")
            self.cargar_dashboard()
            self.ver_pdfs()
        except Exception as e:
            self.conn.rollback()
            Notification(self.root, "❌ Error", str(e), notification_type="error")
        finally:
            self.progress_bar.stop()

    def editar_pdf(self):
        # abre dialogo para editar los metadatos de un PDF
        selected = self.tree.selection()

        if not selected:
            Notification(
                self.root, "⚠️ Advertencia",
                "Selecciona un PDF de la lista",
                notification_type="warning"
            )
            return

        values = self.tree.item(selected[0])['values']
        pdf_id, pdf_nombre, descripcion, tamano, fecha, cedula, nombres, empresa = values

        colors = self.get_colors()
        edit_win = ctk.CTkToplevel(self.root)
        edit_win.title("✏️ Editar Metadatos del PDF")
        edit_win.geometry("480x520")
        edit_win.resizable(False, False)
        edit_win.transient(self.root)
        edit_win.configure(fg_color=colors["bg_secondary"])
        edit_win.withdraw()

        ctk.CTkLabel(
            edit_win, text="✏️ Editar Metadatos",
            font=("Arial", 18, "bold"),
            text_color=colors["text_primary"]
        ).pack(pady=(20, 4))

        ctk.CTkLabel(
            edit_win, text=f"Editando: {pdf_nombre}",
            font=("Arial", 10), text_color=COLOR_SECONDARY
        ).pack(pady=(0, 16))

        def add_field(label, current, placeholder=""):
            ctk.CTkLabel(
                edit_win, text=label,
                text_color=colors["text_primary"],
                font=("Arial", 11, "bold")
            ).pack(anchor="w", padx=40)
            e = ctk.CTkEntry(
                edit_win, width=380, height=40,
                corner_radius=8, border_width=2,
                font=("Arial", 11),
                placeholder_text=placeholder
            )
            e.insert(0, str(current) if current else "")
            e.pack(pady=(4, 10))
            return e

        e_nombre  = add_field("Nombre del archivo:", pdf_nombre)
        e_desc    = add_field("Descripción:", descripcion or "", "Sin descripción")
        e_cedula  = add_field("Cédula:", cedula or "")
        e_nombres = add_field("Nombres:", nombres or "")
        e_empresa = add_field("Empresa:", empresa or "", "Nombre de la empresa")

        def guardar():
            nuevo_nombre   = e_nombre.get().strip()
            nueva_desc     = e_desc.get().strip()
            nueva_cedula   = e_cedula.get().strip()
            nuevos_nombres = e_nombres.get().strip()
            nueva_empresa  = e_empresa.get().strip()

            if not nuevo_nombre:
                Notification(edit_win, "❌ Error", "El nombre no puede estar vacío",
                             notification_type="error")
                return

            try:
                self.cursor.execute(
                    "UPDATE PDFs SET nombre = ?, descripcion = ? WHERE id = ? AND usuario_id = ?",
                    (nuevo_nombre, nueva_desc, pdf_id, self.usuario_actual)
                )
                if nueva_cedula:
                    self.cursor.execute(
                        """UPDATE Personas SET nombres = ?, empresa = ?
                           WHERE id = (SELECT persona_id FROM PDFs WHERE id = ?)""",
                        (nuevos_nombres, nueva_empresa, pdf_id)
                    )
                self.cursor.execute(
                    "INSERT INTO Auditoria (accion, pdf_id, usuario_id, fecha) VALUES (?,?,?,?)",
                    ("Editar metadatos PDF", pdf_id, self.usuario_actual, datetime.now().isoformat())
                )
                self.conn.commit()
                Notification(self.root, "✅ Guardado",
                             "Metadatos actualizados correctamente",
                             notification_type="success")
                edit_win.destroy()
                self.ver_pdfs()
                self._reset_preview_panel()
            except Exception as exc:
                self.conn.rollback()
                Notification(edit_win, "❌ Error", str(exc), notification_type="error")

        ctk.CTkButton(
            edit_win, text="💾 Guardar Cambios",
            command=guardar,
            fg_color=COLOR_PRIMARY, hover_color="#388E3C",
            text_color="white", font=("Arial", 12, "bold"),
            corner_radius=8, width=260, height=42
        ).pack(pady=(8, 4))

        ctk.CTkButton(
            edit_win, text="Cancelar",
            command=edit_win.destroy,
            fg_color="#9E9E9E", hover_color="#757575",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=260, height=36
        ).pack(pady=(0, 20))

        self._show_modal_window(edit_win, delay_ms=250)

    def exportar_pdf(self):
         # exporta (guarda) el PDF desencriptado a una ruta elegida por el usuario
        selected = self.tree.selection()

        if not selected:
            Notification(
                self.root, "⚠️ Advertencia",
                "Selecciona un PDF de la lista",
                notification_type="warning"
            )
            return

        values = self.tree.item(selected[0])['values']
        pdf_id = values[0]
        pdf_nombre = values[1]

        dest = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=pdf_nombre,
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if not dest:
            return

        self.progress_bar.start("Desencriptando y exportando…")

        try:
            self.cursor.execute(
                "SELECT datos, datos_encriptados FROM PDFs WHERE id = ? AND usuario_id = ?",
                (pdf_id, self.usuario_actual)
            )
            result = self.cursor.fetchone()
        except Exception as e:
            self.progress_bar.stop()
            Notification(self.root, "❌ Error", str(e), notification_type="error")
            return

        if not result:
            self.progress_bar.stop()
            Notification(self.root, "❌ Error", "PDF no encontrado", notification_type="error")
            return

        datos_enc, encriptado = result
        usuario_nombre = self.usuario_nombre

        def export_task():
            try:
                datos = (EncryptionManager.decrypt_data(bytes(datos_enc), usuario_nombre)
                         if encriptado else bytes(datos_enc))
                with open(dest, 'wb') as f:
                    f.write(datos)
                self.root.after(0, lambda: Notification(
                    self.root, "✅ Exportado",
                    f"PDF exportado a:\n{dest}",
                    notification_type="success", duration=4000
                ))
                self.cursor.execute(
                    "INSERT INTO Auditoria (accion, pdf_id, usuario_id, fecha) VALUES (?,?,?,?)",
                    ("Exportar PDF", pdf_id, self.usuario_actual, datetime.now().isoformat())
                )
                self.conn.commit()
            except Exception as e:
                self.root.after(0, lambda err=e: Notification(
                    self.root, "❌ Error",
                    f"Error al exportar: {err}",
                    notification_type="error"
                ))
            finally:
                self.root.after(0, self.progress_bar.stop)

        threading.Thread(target=export_task, daemon=True).start()

    def slide_in_frame(self, frame, start_relx=1.0, end_relx=0.0, steps=20, callback=None):
         # anima el deslizamiento de un frame
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
         # c ierra la conexion y sale
        self.cerrar_conexion()
        self.root.destroy()

    def cerrar_conexion(self):
        # cierra la conexion a la BD
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def on_intro_click(self, event=None):
        # evento al hacer clic en intro
        self.frame_intro.pack_forget()
        self.mostrar_inicial()


# PUNTO DE ENTRADA


if __name__ == "__main__":
    root = ctk.CTk()
    app = AppDBPDF(root)
    root.protocol("WM_DELETE_WINDOW", app.cerrar_conexion_y_salir)
    root.mainloop()


# Copyright (c) 2024 DatenJäger. All rights reserved.