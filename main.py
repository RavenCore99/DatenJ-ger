

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
import tempfile
import webbrowser
from datetime import datetime
import hashlib
import random
import threading
import subprocess
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
                      reset_failed_attempts, password_strength)
from ui_components import (Notification, ProgressBarModerno, DashboardWidget,
                           GradientBackground, PasswordStrengthBar, ConfirmDialog,
                           get_dynamic_colors)



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
        self.usuario_contrasena = None
        self.animating = False
        self._search_timer = None                   # busqueda con debounce
        self._configure_timer = None                    # guarda con debounce

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
            columns=("ID", "Nombre", "Descripción", "Tamaño", "Fecha", "Cédula", "Nombres"),
            show="headings",
            height=14
        )

        for col, width in [("ID", 46), ("Nombre", 160), ("Descripción", 200),
                           ("Tamaño", 90), ("Fecha", 120), ("Cédula", 100), ("Nombres", 160)]:
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
        for col in ("ID", "Nombre", "Descripción", "Tamaño", "Fecha", "Cédula", "Nombres"):
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
            row[6] or ""
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
        pdf_id, pdf_nombre, descripcion, tamano, fecha, cedula, nombres = values
        colors = self.get_colors()
        self._preview_name.configure(text=pdf_nombre)
        info = (
            f"📄 {pdf_nombre}\n\n"
            f"📝 {descripcion or '—'}\n\n"
            f"💾 {tamano}\n"
            f"📅 {fecha}\n"
            f"🪪 Cédula: {cedula or '—'}\n"
            f"👤 {nombres or '—'}\n\n"
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
                        cedula, nombres, usuario_actual, window):
        # guarda el blob PDF ya cifrado en la base de datos 
        try:
            self.cursor.execute("SELECT id FROM Personas WHERE cedula = ?", (cedula,))
            result = self.cursor.fetchone()
            if result:
                persona_id = result[0]
                self.cursor.execute(
                    "UPDATE Personas SET nombres = ? WHERE id = ?",
                    (nombres, persona_id)
                )
            else:
                self.cursor.execute(
                    "INSERT INTO Personas (cedula, nombres) VALUES (?, ?)",
                    (cedula, nombres)
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

    def _on_pdf_opened(self, nombre, temp_file, window):
        # descifrado completo: muestra diálogo 'Abrir con' para que el usuario elija la aplicación

        if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
            Notification(self.root, "❌ Error",
                         "El archivo descifrado está vacío o no se pudo escribir",
                         notification_type="error")
            return

        if window:
            window.destroy()

        colors = self.get_colors()
        self.status.configure(
            text=f"✅ PDF descifrado: {nombre} — elige cómo abrirlo",
            text_color=colors["text_primary"]
        )

        #  Dialogo "Abrir con" 
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Abrir PDF con...")
        dialog.geometry("420x300")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.configure(fg_color=colors["bg_secondary"])
        dialog.withdraw()

        def _lanzar(app_cmd):
            # lanza la aplicacion con el archivo y cierra el dialogo
            try:
                if isinstance(app_cmd, list):
                    cmd = app_cmd + [temp_file]
                else:
                    cmd = [app_cmd, temp_file]
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                dialog.destroy()
                Notification(self.root, "✅ PDF abierto",
                             f"{nombre} abierto con éxito",
                             notification_type="success", duration=3000)
            except Exception as e:
                Notification(dialog, "❌ Error", f"No se pudo abrir: {e}",
                             notification_type="error")

        def _abrir_predeterminado():
            if os.name == 'nt':
                os.startfile(temp_file)
                dialog.destroy()
            else:
                _lanzar(['xdg-open'])

        def _elegir_aplicacion():
            from tkinter import filedialog
            exe = filedialog.askopenfilename(
                parent=dialog,
                title="Seleccionar aplicación",
                initialdir="/usr/bin",
            )
            if exe:
                _lanzar([exe])

        def _build():
            ctk.CTkLabel(
                dialog, text="📄 PDF Descifrado — AES-256-GCM",
                font=("Arial", 14, "bold"),
                text_color=colors["text_primary"]
            ).pack(pady=(22, 4))

            ctk.CTkLabel(
                dialog, text=nombre,
                font=("Arial", 11),
                text_color=COLOR_SECONDARY,
                wraplength=360
            ).pack(pady=(0, 18))

            ctk.CTkButton(
                dialog,
                text="🌐  Abrir con aplicación predeterminada",
                command=_abrir_predeterminado,
                fg_color=COLOR_PRIMARY, hover_color="#388E3C",
                text_color="white", font=("Arial", 12, "bold"),
                corner_radius=8, width=320, height=42
            ).pack(pady=6)

            ctk.CTkButton(
                dialog,
                text="🔍  Elegir aplicación...",
                command=_elegir_aplicacion,
                fg_color=COLOR_SECONDARY, hover_color="#1565c0",
                text_color="white", font=("Arial", 12, "bold"),
                corner_radius=8, width=320, height=42
            ).pack(pady=6)

            ctk.CTkButton(
                dialog,
                text="Cancelar",
                command=dialog.destroy,
                fg_color="#9E9E9E", hover_color="#757575",
                text_color="white", font=("Arial", 11),
                corner_radius=8, width=320, height=34
            ).pack(pady=(6, 20))

            dialog.update_idletasks()
            dialog.deiconify()
            dialog.lift()
            dialog.focus_force()
            dialog.grab_set()

        dialog.after(250, _build)
        # limpiar el archivo temporal a los 5 minutos 
        self.root.after(300000, lambda: self._cleanup_temp_file(temp_file))

    def _cleanup_temp_file(self, filepath):
        # elimina silenciosamente un archivo temporal si aún existe
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
        except Exception:
            pass  # es posible que el archivo aun este abierto en el lector de PDF.

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

            self.usuario_nombre = nombre
            self.usuario_contrasena = contrasena
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

                    self.usuario_actual = usuario_id
                    self.usuario_nombre = nombre
                    self.usuario_contrasena = contrasena

                    if totp_enabled:
                        self._hide_all_frames()
                        self.entry_2fa_code.delete(0, tk.END)
                        self.frame_2fa.pack(expand=True, fill="both")
                        self.entry_2fa_code.focus()
                    else:
                        self.completar_login()
                else:
                    record_failed_attempt(self.cursor, self.conn, nombre)
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

                # cifrar totp_secret y backup_codes antes de guardar en la DB
                secret_enc   = EncryptionManager.encrypt_str(self.totp_secret,  self.usuario_contrasena)
                backups_enc  = EncryptionManager.encrypt_str(backup_codes_str, self.usuario_contrasena)

                self.cursor.execute(
                    "UPDATE Usuarios SET totp_secret = ?, totp_enabled = 1, backup_codes = ? WHERE nombre = ?",
                    (secret_enc, backups_enc, self.usuario_nombre)
                )
                self.conn.commit()

                # mostrar coSdigos de respaldo y esperar a que el usuario cierre la ventana
                self._mostrar_codigos_respaldo(backup_codes)

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
            win.deiconify()   # mostrar con todo el contenido ya renderizado
            win.lift()
            win.focus_force()
            win.grab_set()

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
                # descifrar el secret (soporta legacy en texto plano si el usuario no ha re-configurado 2FA)
                totp_secret = EncryptionManager.decrypt_str(result[0], self.usuario_contrasena)
                totp = pyotp.TOTP(totp_secret)

                if totp.verify(codigo):
                    self.completar_login()
                else:
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
                # descifrar backup_codes (soporta legacy en texto plano)
                codes_raw    = EncryptionManager.decrypt_str(result[0], self.usuario_contrasena)
                backup_codes = codes_raw.split(",")

                if codigo in backup_codes:
                    backup_codes.remove(codigo)
                    backup_codes_str = ",".join(backup_codes)

                    # recifrar la lista actualizada antes de guardar
                    backups_enc = EncryptionManager.encrypt_str(backup_codes_str, self.usuario_contrasena)
                    self.cursor.execute(
                        "UPDATE Usuarios SET backup_codes = ? WHERE id = ?",
                        (backups_enc, self.usuario_actual)
                    )
                    self.conn.commit()

                    Notification(
                        self.root,
                        "✅ Código Aceptado",
                        "Login completado con código de respaldo",
                        notification_type="success"
                    )

                    self.completar_login()
                else:
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
        self.cargar_dashboard()
        self.ver_pdfs()

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
            self.usuario_actual = None
            self.usuario_nombre = None
            self.usuario_contrasena = None
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
        add_window.geometry("500x580")
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

        add_window.after(250, lambda w=add_window: (
            w.deiconify(), w.lift(), w.focus_force(), w.grab_set()
        ) if w.winfo_exists() else None)

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
                    cedula, nombres, usuario_actual, window
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
                       p.fecha_subida, pe.cedula, pe.nombres
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
                       p.fecha_subida, pe.cedula, pe.nombres
                FROM PDFs p
                LEFT JOIN Personas pe ON p.persona_id = pe.id
                WHERE p.usuario_id = ? AND (
                    p.nombre LIKE ? OR p.descripcion LIKE ?
                    OR pe.cedula LIKE ? OR pe.nombres LIKE ?
                )
            """, (self.usuario_actual,
                  f"%{term}%", f"%{term}%", f"%{term}%", f"%{term}%"))

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
        pdf_id, pdf_nombre, descripcion, tamano, fecha, cedula, nombres = values

        colors = self.get_colors()
        details_window = ctk.CTkToplevel(self.root)
        details_window.title("ℹ️ Detalles del PDF")
        details_window.geometry("460x440")
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

        details_window.after(250, lambda w=details_window: (
            w.deiconify(), w.lift(), w.focus_force(), w.grab_set()
        ) if w.winfo_exists() else None)

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
        usuario_nombre = self.usuario_nombre

        def decrypt_task():
            try:
                datos = (EncryptionManager.decrypt_data(bytes(datos_enc), usuario_nombre)
                         if encriptado else bytes(datos_enc))
                temp_file = os.path.join(tempfile.gettempdir(), nombre)
                with open(temp_file, 'wb') as f:
                    f.write(datos)
                self.root.after(0, lambda: self._on_pdf_opened(nombre, temp_file, window))
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
        pdf_id, pdf_nombre, descripcion, tamano, fecha, cedula, nombres = values

        colors = self.get_colors()
        edit_win = ctk.CTkToplevel(self.root)
        edit_win.title("✏️ Editar Metadatos del PDF")
        edit_win.geometry("480x460")
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

        e_nombre = add_field("Nombre del archivo:", pdf_nombre)
        e_desc   = add_field("Descripción:", descripcion or "", "Sin descripción")
        e_cedula = add_field("Cédula:", cedula or "")
        e_nombres = add_field("Nombres:", nombres or "")

        def guardar():
            nuevo_nombre = e_nombre.get().strip()
            nueva_desc   = e_desc.get().strip()
            nueva_cedula = e_cedula.get().strip()
            nuevos_nombres = e_nombres.get().strip()

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
                        """UPDATE Personas SET nombres = ? 
                           WHERE id = (SELECT persona_id FROM PDFs WHERE id = ?)""",
                        (nuevos_nombres, pdf_id)
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

        edit_win.after(250, lambda w=edit_win: (
            w.deiconify(), w.lift(), w.focus_force(), w.grab_set()
        ) if w.winfo_exists() else None)

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