#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py - Aplicación Principal
DatenJäger v3.0 FASE 3 - Sistema de Gestión Documental Seguro
Con 2FA (Google Authenticator) + Encriptación AES-256
ACTUALIZADO: Colores dinámicos para modo oscuro/claro
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
import pyotp
import qrcode
from PIL import ImageTk, Image
from io import BytesIO

# Importar módulos locales
from config import Config
from encryption import EncryptionManager
from database import conectar_db, hash_contrasena, format_size, format_date_friendly, ease_in_out
from ui_components import Notification, ProgressBarModerno, DashboardWidget, get_dynamic_colors

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE CUSTOMTKINTER
# ═══════════════════════════════════════════════════════════════════════════════

ctk.set_default_color_theme("blue")

# ═══════════════════════════════════════════════════════════════════════════════
# DEFINICIÓN DE COLORES (estáticos para fondo, dinámicos para texto)
# ═══════════════════════════════════════════════════════════════════════════════

COLOR_BG_LIGHT = "#F5F5F5"
COLOR_BG_DARK = "#2c2434"
COLOR_PRIMARY = "#4CAF50"
COLOR_SECONDARY = "#2196F3"
COLOR_WARNING = "#FF9800"
COLOR_ERROR = "#F44336"
COLOR_SUCCESS = "#4CAF50"
COLOR_TEXT_LIGHT = "#004D40"
COLOR_TEXT_DARK = "#FFFFFF"

# ═══════════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL FASE 3
# ═══════════════════════════════════════════════════════════════════════════════

class AppDBPDF:
    """Aplicación principal FASE 3 con 2FA + Encriptación + Tema Dinámico"""

    def __init__(self, root):
        """Inicializa la aplicación"""
        self.root = root
        self.root.title("DatenJäger - Sistema de Gestion Documental v3.0 FASE 3")
        self.root.geometry("1000x700")

        self.config = Config()
        window_size = self.config.get("window_size", "1000x700")
        self.root.geometry(window_size)

        # Apply saved theme BEFORE building frames so colors are correct
        theme = self.config.get("theme", "System")
        ctk.set_appearance_mode(theme)

        self.conn, self.cursor = conectar_db()
        self._db_lock = threading.Lock()  # Serialises any concurrent DB access
        self.usuario_actual = None
        self.usuario_nombre = None
        self.animating = False
        self._search_timer = None  # For debounced live search

        self._setup_atajos()
        self._crear_frames()
        self._apply_treeview_style()
        self._setup_treeview_sorting()
        self.root.minsize(800, 600)
        self.mostrar_inicial()

        self.root.bind("<F11>", self.toggle_fullscreen)

    def get_colors(self):
        """Obtiene colores dinámicos"""
        return get_dynamic_colors()

    def _setup_atajos(self):
        """Configura atajos de teclado"""
        self.root.bind("<Control-q>", lambda e: self.cerrar_conexion_y_salir())
        self.root.bind("<Control-f>", lambda e: self.entry_busqueda.focus() if hasattr(self, 'entry_busqueda') else None)
        self.root.bind("<Control-n>", lambda e: self.mostrar_agregar_pdf() if self.usuario_actual else None)
        self.root.bind("<Delete>", lambda e: self.eliminar_pdf() if self.usuario_actual else None)

    def toggle_fullscreen(self, event=None):
        """Alterna fullscreen (F11)"""
        try:
            state = self.root.attributes('-zoomed')
            self.root.attributes('-zoomed', not state)
        except:
            pass

    def _crear_frames(self):
        """Crea todos los frames de la aplicación"""
        colors = self.get_colors()
        
        # Frame de intro
        self.frame_intro = ctk.CTkFrame(self.root, fg_color=COLOR_BG_DARK)
        self.frame_intro.pack(expand=True, fill="both")

        self.intro_text = ctk.CTkLabel(
            self.frame_intro,
            text="DatenJäger | Gestor Seguro de PDFs | 🔐",
            font=("Arial", 48, "bold"),
            text_color=COLOR_TEXT_DARK
        )
        self.intro_text.pack(expand=True)
        self.intro_text.bind("<Button-1>", self.on_intro_click)

        self.access_text = ctk.CTkLabel(
            self.frame_intro,
            text="v3.0 FASE 3: 2FA + Encriptación AES-256\nClick para acceder ✨",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 14, "bold")
        )
        self.access_text.pack(pady=20)
        self.access_text.bind("<Button-1>", self.on_intro_click)

        # Frame inicial
        self.frame_inicial = ctk.CTkFrame(self.root, fg_color=COLOR_BG_LIGHT)

        titulo = ctk.CTkLabel(
            self.frame_inicial,
            text="🔐 DatenJäger FASE 3",
            font=("Arial", 24, "bold"),
            text_color=colors["text_primary"]
        )
        titulo.pack(pady=20)

        subtitle = ctk.CTkLabel(
            self.frame_inicial,
            text="Seguridad Empresarial: 2FA + AES-256",
            font=("Arial", 12),
            text_color=COLOR_SECONDARY
        )
        subtitle.pack(pady=5)

        btn_iniciar = ctk.CTkButton(
            self.frame_inicial,
            text="🔓 Iniciar Sesión",
            command=self.mostrar_login,
            fg_color=COLOR_PRIMARY,
            hover_color="#388E3C",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 14, "bold"),
            corner_radius=10,
            width=300,
            height=50
        )
        btn_iniciar.pack(pady=15)

        btn_registrar = ctk.CTkButton(
            self.frame_inicial,
            text="✍️  Crear Usuario",
            command=self.mostrar_registro,
            fg_color=COLOR_SECONDARY,
            hover_color="#1976D2",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 14, "bold"),
            corner_radius=10,
            width=300,
            height=50
        )
        btn_registrar.pack(pady=15)

        # Frame login
        self.frame_login = ctk.CTkFrame(self.root, fg_color=COLOR_BG_LIGHT)

        titulo_login = ctk.CTkLabel(
            self.frame_login,
            text="🔓 Iniciar Sesión",
            font=("Arial", 24, "bold"),
            text_color=colors["text_primary"]
        )
        titulo_login.pack(pady=20)

        ctk.CTkLabel(
            self.frame_login,
            text="Usuario:",
            text_color=colors["text_primary"],
            font=("Arial", 12, "bold")
        ).pack()

        self.entry_usuario_login = ctk.CTkEntry(
            self.frame_login,
            placeholder_text="Tu usuario",
            width=300,
            height=40,
            corner_radius=8,
            border_width=2,
            font=("Arial", 12)
        )
        self.entry_usuario_login.pack(pady=10)

        ctk.CTkLabel(
            self.frame_login,
            text="Contraseña:",
            text_color=colors["text_primary"],
            font=("Arial", 12, "bold")
        ).pack()

        self.entry_contrasena_login = ctk.CTkEntry(
            self.frame_login,
            placeholder_text="Tu contraseña",
            width=300,
            height=40,
            corner_radius=8,
            border_width=2,
            font=("Arial", 12),
            show="●"
        )
        self.entry_contrasena_login.pack(pady=10)

        btn_login = ctk.CTkButton(
            self.frame_login,
            text="✅ Siguiente",
            command=self.login,
            fg_color=COLOR_PRIMARY,
            hover_color="#388E3C",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 12, "bold"),
            corner_radius=8,
            width=200,
            height=40
        )
        btn_login.pack(pady=15)

        btn_volver = ctk.CTkButton(
            self.frame_login,
            text="⬅️  Volver",
            command=self.mostrar_inicial,
            fg_color="#9E9E9E",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 12, "bold"),
            corner_radius=8,
            width=200,
            height=40
        )
        btn_volver.pack(pady=10)

        # Frame 2FA
        self.frame_2fa = ctk.CTkFrame(self.root, fg_color=COLOR_BG_LIGHT)

        titulo_2fa = ctk.CTkLabel(
            self.frame_2fa,
            text="🔐 Verificación 2FA",
            font=("Arial", 24, "bold"),
            text_color=colors["text_primary"]
        )
        titulo_2fa.pack(pady=20)

        ctk.CTkLabel(
            self.frame_2fa,
            text="Ingresa el código de 6 dígitos de tu aplicación autenticadora:",
            text_color=colors["text_primary"],
            font=("Arial", 11)
        ).pack(pady=10)

        self.entry_2fa_code = ctk.CTkEntry(
            self.frame_2fa,
            placeholder_text="000000",
            width=300,
            height=40,
            corner_radius=8,
            border_width=2,
            font=("Arial", 20),
            justify="center"
        )
        self.entry_2fa_code.pack(pady=15)

        btn_verificar = ctk.CTkButton(
            self.frame_2fa,
            text="✅ Verificar",
            command=self.verificar_2fa,
            fg_color=COLOR_PRIMARY,
            hover_color="#388E3C",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 12, "bold"),
            corner_radius=8,
            width=200,
            height=40
        )
        btn_verificar.pack(pady=10)

        ctk.CTkLabel(
            self.frame_2fa,
            text="¿No tienes acceso a tu teléfono? Usa un código de respaldo",
            text_color=COLOR_WARNING,
            font=("Arial", 10)
        ).pack(pady=5)

        btn_backup = ctk.CTkButton(
            self.frame_2fa,
            text="🔄 Código de Respaldo",
            command=self.usar_codigo_respaldo,
            fg_color=COLOR_WARNING,
            hover_color="#F57C00",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 11, "bold"),
            corner_radius=8,
            width=200,
            height=35
        )
        btn_backup.pack(pady=5)

        btn_volver_2fa = ctk.CTkButton(
            self.frame_2fa,
            text="⬅️  Volver",
            command=self.mostrar_login,
            fg_color="#9E9E9E",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 12, "bold"),
            corner_radius=8,
            width=200,
            height=40
        )
        btn_volver_2fa.pack(pady=10)

        # Frame registro
        self.frame_registro = ctk.CTkFrame(self.root, fg_color=COLOR_BG_LIGHT)

        titulo_registro = ctk.CTkLabel(
            self.frame_registro,
            text="✍️  Crear Usuario",
            font=("Arial", 24, "bold"),
            text_color=colors["text_primary"]
        )
        titulo_registro.pack(pady=20)

        ctk.CTkLabel(
            self.frame_registro,
            text="Usuario:",
            text_color=colors["text_primary"],
            font=("Arial", 12, "bold")
        ).pack()

        self.entry_usuario_registro = ctk.CTkEntry(
            self.frame_registro,
            placeholder_text="Tu usuario",
            width=300,
            height=40,
            corner_radius=8,
            border_width=2,
            font=("Arial", 12)
        )
        self.entry_usuario_registro.pack(pady=10)

        ctk.CTkLabel(
            self.frame_registro,
            text="Contraseña:",
            text_color=colors["text_primary"],
            font=("Arial", 12, "bold")
        ).pack()

        self.entry_contrasena_registro = ctk.CTkEntry(
            self.frame_registro,
            placeholder_text="Tu contraseña (mínimo 8 caracteres)",
            width=300,
            height=40,
            corner_radius=8,
            border_width=2,
            font=("Arial", 12),
            show="●"
        )
        self.entry_contrasena_registro.pack(pady=10)

        btn_registrar_form = ctk.CTkButton(
            self.frame_registro,
            text="✅ Registrar",
            command=self.registrarse,
            fg_color=COLOR_SECONDARY,
            hover_color="#1976D2",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 12, "bold"),
            corner_radius=8,
            width=200,
            height=40
        )
        btn_registrar_form.pack(pady=15)

        btn_volver_reg = ctk.CTkButton(
            self.frame_registro,
            text="⬅️  Volver",
            command=self.mostrar_inicial,
            fg_color="#9E9E9E",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 12, "bold"),
            corner_radius=8,
            width=200,
            height=40
        )
        btn_volver_reg.pack(pady=10)

        # Frame setup 2FA
        self.frame_setup_2fa = ctk.CTkFrame(self.root, fg_color=COLOR_BG_LIGHT)

        titulo_setup = ctk.CTkLabel(
            self.frame_setup_2fa,
            text="🔐 Configurar Autenticación 2FA",
            font=("Arial", 24, "bold"),
            text_color=colors["text_primary"]
        )
        titulo_setup.pack(pady=20)

        ctk.CTkLabel(
            self.frame_setup_2fa,
            text="1. Abre Google Authenticator o Microsoft Authenticator",
            text_color=colors["text_primary"],
            font=("Arial", 11)
        ).pack(pady=5)

        ctk.CTkLabel(
            self.frame_setup_2fa,
            text="2. Escanea el código QR:",
            text_color=colors["text_primary"],
            font=("Arial", 11)
        ).pack(pady=5)

        self.label_qr = ctk.CTkLabel(
            self.frame_setup_2fa,
            text="[QR Code]",
            text_color=colors["text_primary"],
            font=("Arial", 11)
        )
        self.label_qr.pack(pady=15)

        ctk.CTkLabel(
            self.frame_setup_2fa,
            text="Clave secreta (cópiala si el QR no funciona):",
            text_color=colors["text_primary"],
            font=("Arial", 11)
        ).pack(pady=5)

        self.label_secret = ctk.CTkLabel(
            self.frame_setup_2fa,
            text="",
            text_color=COLOR_PRIMARY,
            font=("Arial", 12, "bold")
        )
        self.label_secret.pack(pady=10)

        ctk.CTkLabel(
            self.frame_setup_2fa,
            text="3. Ingresa el código de 6 dígitos para confirmar:",
            text_color=colors["text_primary"],
            font=("Arial", 11)
        ).pack(pady=5)

        self.entry_confirm_2fa = ctk.CTkEntry(
            self.frame_setup_2fa,
            placeholder_text="000000",
            width=300,
            height=40,
            corner_radius=8,
            border_width=2,
            font=("Arial", 20),
            justify="center"
        )
        self.entry_confirm_2fa.pack(pady=15)

        btn_confirm_setup = ctk.CTkButton(
            self.frame_setup_2fa,
            text="✅ Confirmar",
            command=self.confirmar_setup_2fa,
            fg_color=COLOR_PRIMARY,
            hover_color="#388E3C",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 12, "bold"),
            corner_radius=8,
            width=200,
            height=40
        )
        btn_confirm_setup.pack(pady=15)

        ctk.CTkLabel(
            self.frame_setup_2fa,
            text="⚠️ Guarda tus códigos de respaldo en lugar seguro",
            text_color=COLOR_WARNING,
            font=("Arial", 10, "bold")
        ).pack(pady=10)

        # Frame principal
        self.frame_principal = ctk.CTkFrame(self.root, fg_color=COLOR_BG_LIGHT)

        # Panel superior
        top_panel = ctk.CTkFrame(self.frame_principal, fg_color=COLOR_BG_LIGHT)
        top_panel.pack(fill="x", padx=20, pady=(10, 5))

        def toggle_theme():
            current_mode = ctk.get_appearance_mode()
            new_mode = "Light" if current_mode == "Dark" else "Dark"
            ctk.set_appearance_mode(new_mode)
            self.config.set("theme", new_mode)
            btn_theme.configure(
                text="☀️  Claro" if new_mode == "Dark" else "🌙 Oscuro"
            )
            # Actualizar colores en toda la interfaz
            self.actualizar_colores_dinamicos()

        current_theme = ctk.get_appearance_mode()
        btn_theme = ctk.CTkButton(
            top_panel,
            text="☀️  Claro" if current_theme == "Dark" else "🌙 Oscuro",
            command=toggle_theme,
            width=150,
            height=35,
            fg_color="#404040",
            hover_color="#505050",
            corner_radius=8,
            font=("Arial", 10, "bold")
        )
        btn_theme.pack(side="right", padx=5)

        btn_info = ctk.CTkButton(
            top_panel,
            text="ℹ️  v3.0 FASE 3",
            command=lambda: Notification(
                self.root,
                "ℹ️ DatenJäger v3.0 FASE 3",
                "🔒 2FA (Google Authenticator)\n🔐 Encriptación AES-256\nSeguridad Empresarial",
                notification_type="info",
                duration=4000
            ),
            width=150,
            height=35,
            fg_color="#404040",
            hover_color="#505050",
            corner_radius=8,
            font=("Arial", 10, "bold")
        )
        btn_info.pack(side="right", padx=5)

        # Barra de progreso
        self.progress_bar = ProgressBarModerno(self.frame_principal)
        self.progress_bar.pack(fill="x", pady=5)

        # Dashboard
        self.dashboard_container = ctk.CTkFrame(self.frame_principal, fg_color="transparent")
        self.dashboard_container.pack(fill="x", padx=20)

        # Barra de búsqueda
        search_frame = ctk.CTkFrame(self.frame_principal, fg_color=COLOR_BG_LIGHT)
        search_frame.pack(pady=10, fill="x", padx=20)

        ctk.CTkLabel(
            search_frame,
            text="🔍 Buscar:",
            text_color=colors["text_primary"],
            font=("Arial", 12, "bold")
        ).pack(side="left", padx=5)

        self.entry_busqueda = ctk.CTkEntry(
            search_frame,
            placeholder_text="Buscar PDF...",
            width=300,
            height=35,
            corner_radius=8,
            border_width=2,
            font=("Arial", 11)
        )
        self.entry_busqueda.pack(side="left", padx=5)
        self.entry_busqueda.bind("<Return>", lambda e: self.buscar_pdfs())
        self.entry_busqueda.bind("<KeyRelease>", self._debounced_search)

        btn_buscar = ctk.CTkButton(
            search_frame,
            text="🔎 Buscar",
            command=self.buscar_pdfs,
            fg_color=COLOR_SECONDARY,
            hover_color="#1976D2",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 11, "bold"),
            corner_radius=8,
            width=100,
            height=35
        )
        btn_buscar.pack(side="left", padx=5)

        # Botones de acciones
        btn_frame = ctk.CTkFrame(self.frame_principal, fg_color=COLOR_BG_LIGHT)
        btn_frame.pack(pady=10, fill="x", padx=20)

        btn_agregar = ctk.CTkButton(
            btn_frame,
            text="➕ Agregar PDF",
            command=self.mostrar_agregar_pdf,
            fg_color=COLOR_PRIMARY,
            hover_color="#388E3C",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 11, "bold"),
            corner_radius=8,
            width=150,
            height=40
        )
        btn_agregar.pack(side="left", padx=5)

        btn_ver = ctk.CTkButton(
            btn_frame,
            text="👁️  Ver PDFs",
            command=self.ver_pdfs,
            fg_color=COLOR_SECONDARY,
            hover_color="#1976D2",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 11, "bold"),
            corner_radius=8,
            width=150,
            height=40
        )
        btn_ver.pack(side="left", padx=5)

        btn_detalles = ctk.CTkButton(
            btn_frame,
            text="ℹ️  Detalles",
            command=self.mostrar_detalles_pdf,
            fg_color=COLOR_WARNING,
            hover_color="#F57C00",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 11, "bold"),
            corner_radius=8,
            width=150,
            height=40
        )
        btn_detalles.pack(side="left", padx=5)

        btn_eliminar = ctk.CTkButton(
            btn_frame,
            text="🗑️  Eliminar",
            command=self.eliminar_pdf,
            fg_color=COLOR_ERROR,
            hover_color="#D32F2F",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 11, "bold"),
            corner_radius=8,
            width=150,
            height=40
        )
        btn_eliminar.pack(side="left", padx=5)

        btn_salir = ctk.CTkButton(
            btn_frame,
            text="🚪 Salir",
            command=self.cerrar_conexion_y_salir,
            fg_color="#9E9E9E",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 11, "bold"),
            corner_radius=8,
            width=150,
            height=40
        )
        btn_salir.pack(side="left", padx=5)

        # TreeView
        tree_frame = ctk.CTkFrame(self.frame_principal, fg_color=COLOR_BG_LIGHT)
        tree_frame.pack(pady=10, fill="both", expand=True, padx=20)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("ID", "Nombre", "Descripción", "Tamaño", "Fecha", "Cédula", "Nombres"),
            show="headings",
            height=12
        )

        self.tree.heading("ID", text="ID")
        self.tree.heading("Nombre", text="Nombre del PDF")
        self.tree.heading("Descripción", text="Descripción")
        self.tree.heading("Tamaño", text="Tamaño")
        self.tree.heading("Fecha", text="Fecha Subida")
        self.tree.heading("Cédula", text="Cédula")
        self.tree.heading("Nombres", text="Nombres")

        self.tree.column("ID", width=50)
        self.tree.column("Nombre", width=150)
        self.tree.column("Descripción", width=200)
        self.tree.column("Tamaño", width=100)
        self.tree.column("Fecha", width=130)
        self.tree.column("Cédula", width=100)
        self.tree.column("Nombres", width=150)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda e: self.abrir_pdf_doble_click())

        # Barra de estado
        self.status = ctk.CTkLabel(
            self.frame_principal,
            text="✅ Listo",
            text_color=colors["text_primary"],
            font=("Arial", 10, "bold"),
            anchor="w"
        )
        self.status.pack(side="bottom", fill="x", padx=20, pady=10)

    def actualizar_colores_dinamicos(self):
        """Actualiza los colores dinámicos cuando cambia el tema"""
        mode = ctk.get_appearance_mode()
        bg = COLOR_BG_DARK if mode == "Dark" else COLOR_BG_LIGHT
        colors = self.get_colors()

        # Update all frame backgrounds
        for frame in [self.frame_principal, self.frame_inicial, self.frame_login,
                      self.frame_2fa, self.frame_setup_2fa, self.frame_registro]:
            frame.configure(fg_color=bg)

        # Update status bar text color
        self.status.configure(text_color=colors["text_primary"])

        # Re-apply TreeView styling and refresh alternating row colors
        self._apply_treeview_style()
        if self.usuario_actual:
            self.ver_pdfs()

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS: NAVIGATION
    # ═══════════════════════════════════════════════════════════════════════════

    def _hide_all_frames(self):
        """Hides every top-level frame and resets the layout"""
        for f in [self.frame_intro, self.frame_inicial, self.frame_login,
                  self.frame_2fa, self.frame_setup_2fa, self.frame_principal,
                  self.frame_registro]:
            f.pack_forget()
        self.root.update()

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS: TREEVIEW STYLING & SORTING
    # ═══════════════════════════════════════════════════════════════════════════

    def _apply_treeview_style(self):
        """Applies a dynamic ttk style to the TreeView to match the active theme"""
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
        """Enables click-to-sort on every TreeView column header"""
        for col in ("ID", "Nombre", "Descripción", "Tamaño", "Fecha", "Cédula", "Nombres"):
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_column(c, False))

    def _sort_column(self, col, reverse):
        """Sorts the TreeView rows by the given column"""
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try:
            # Try numeric sort for ID column; fall back to string for everything else
            if col == "ID":
                data.sort(key=lambda x: int(x[0]), reverse=reverse)
            else:
                data.sort(key=lambda x: x[0].lower(), reverse=reverse)
        except (ValueError, AttributeError):
            data.sort(key=lambda x: x[0], reverse=reverse)

        for index, (_, k) in enumerate(data):
            self.tree.move(k, '', index)
            self.tree.item(k, tags=('evenrow' if index % 2 == 0 else 'oddrow',))

        # Toggle sort direction on next click
        self.tree.heading(col, command=lambda: self._sort_column(col, not reverse))

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS: TREEVIEW DATA
    # ═══════════════════════════════════════════════════════════════════════════

    def _format_pdf_row(self, row):
        """Formats a DB row tuple for display in the TreeView"""
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
        """Clears the TreeView and inserts formatted rows with alternating colors"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, row in enumerate(rows):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.tree.insert('', 'end', values=self._format_pdf_row(row), tags=(tag,))

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS: SEARCH DEBOUNCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _debounced_search(self, event=None):
        """Triggers a search 400 ms after the user stops typing"""
        if self._search_timer:
            self.root.after_cancel(self._search_timer)
        self._search_timer = self.root.after(400, self.buscar_pdfs)

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS: PDF OPERATIONS (thread callbacks + temp-file cleanup)
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_pdf_to_db(self, datos_enc, tamano, nombre, descripcion,
                        cedula, nombres, usuario_actual, window):
        """Saves the already-encrypted PDF blob to the DB (runs on main thread)"""
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
                ("Agregar PDF (Encriptado AES-256)", pdf_id, usuario_actual,
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
        """Called on main thread after a PDF is saved successfully"""
        colors = self.get_colors()
        self.status.configure(
            text=f"✅ PDF {nombre} agregado y encriptado",
            text_color=colors["text_primary"]
        )
        Notification(self.root, "✅ Éxito",
                     f"PDF {nombre} agregado\nEncriptado con AES-256",
                     notification_type="success")
        window.destroy()
        self.cargar_dashboard()
        self.ver_pdfs()

    def _on_pdf_add_error(self, error):
        """Called on main thread when adding a PDF fails"""
        Notification(self.root, "❌ Error", str(error), notification_type="error")
        colors = self.get_colors()
        self.status.configure(text="❌ Error al agregar PDF",
                              text_color=colors["text_primary"])

    def _on_pdf_opened(self, nombre, temp_file, window):
        """Called on main thread after a PDF is decrypted and written to temp dir"""
        if os.name == 'nt':
            os.startfile(temp_file)
        else:
            webbrowser.open(temp_file)

        colors = self.get_colors()
        self.status.configure(
            text=f"✅ Abriendo PDF {nombre} (Desencriptado)",
            text_color=colors["text_primary"]
        )
        Notification(self.root, "✅ PDF abierto",
                     f"Abriendo {nombre}...\n(Desencriptado con AES-256)",
                     notification_type="success", duration=2000)
        if window:
            window.destroy()
        # Schedule temp file cleanup (give the PDF reader time to open the file)
        self.root.after(30000, lambda: self._cleanup_temp_file(temp_file))

    def _cleanup_temp_file(self, filepath):
        """Silently removes a temporary file if it still exists"""
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
        except Exception:
            pass  # File may still be open in the PDF reader

    def mostrar_inicial(self):
        """Muestra la pantalla inicial"""
        self._hide_all_frames()
        self.slide_in_frame(self.frame_inicial,
                            callback=lambda: self.frame_inicial.pack(expand=True, fill="both"))

    def mostrar_login(self):
        """Muestra la pantalla de login"""
        self._hide_all_frames()
        self.entry_usuario_login.delete(0, tk.END)
        self.entry_contrasena_login.delete(0, tk.END)
        self.slide_in_frame(self.frame_login,
                            callback=lambda: self.frame_login.pack(expand=True, fill="both"))

    def mostrar_registro(self):
        """Muestra la pantalla de registro"""
        self._hide_all_frames()
        self.entry_usuario_registro.delete(0, tk.END)
        self.entry_contrasena_registro.delete(0, tk.END)
        self.slide_in_frame(self.frame_registro,
                            callback=lambda: self.frame_registro.pack(expand=True, fill="both"))

    def registrarse(self):
        """Registra un nuevo usuario"""
        nombre = self.entry_usuario_registro.get().strip()
        contrasena = self.entry_contrasena_registro.get().strip()

        if not nombre or not contrasena:
            Notification(
                self.root,
                "❌ Error",
                "Ingresa nombre de usuario y contraseña",
                notification_type="error"
            )
            return

        if len(contrasena) < 8:
            Notification(
                self.root,
                "❌ Error",
                "La contraseña debe tener mínimo 8 caracteres",
                notification_type="error"
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
                self.root,
                "✅ Éxito",
                f"Usuario {nombre} registrado\nConfigurando 2FA...",
                notification_type="success"
            )
        except Exception as e:
            Notification(
                self.root,
                "❌ Error",
                str(e),
                notification_type="error"
            )

    def login(self):
        """Inicia sesión (paso 1: validar usuario/contraseña)"""
        nombre = self.entry_usuario_login.get().strip()
        contrasena = self.entry_contrasena_login.get().strip()

        if not nombre or not contrasena:
            Notification(
                self.root,
                "❌ Error",
                "Ingresa nombre de usuario y contraseña",
                notification_type="error"
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
                if hash_contrasena(contrasena) == hash_stored:
                    self.usuario_actual = usuario_id
                    self.usuario_nombre = nombre

                    if totp_enabled:
                        self.frame_login.pack_forget()
                        self.entry_2fa_code.delete(0, tk.END)
                        self.frame_2fa.pack(expand=True, fill="both")
                        self.entry_2fa_code.focus()
                    else:
                        self.completar_login()
                else:
                    Notification(
                        self.root,
                        "❌ Error",
                        "Contraseña incorrecta",
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

    def mostrar_setup_2fa(self):
        """Muestra pantalla para configurar 2FA"""
        self.totp_secret = pyotp.random_base32()
        totp = pyotp.totp.TOTP(self.totp_secret)
        totp_uri = totp.provisioning_uri(
            name=self.usuario_nombre,
            issuer_name='DatenJäger'
        )

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((250, 250))

        photo = ImageTk.PhotoImage(img)
        self.label_qr.configure(image=photo, text="")
        self.label_qr.image = photo

        self.label_secret.configure(text=self.totp_secret)

        self.frame_registro.pack_forget()
        self.frame_setup_2fa.pack(expand=True, fill="both")
        self.entry_confirm_2fa.focus()

    def confirmar_setup_2fa(self):
        """Confirma y guarda la configuración 2FA"""
        codigo = self.entry_confirm_2fa.get().strip()

        if not codigo or len(codigo) != 6:
            Notification(
                self.root,
                "❌ Error",
                "Ingresa un código válido de 6 dígitos",
                notification_type="error"
            )
            return

        try:
            totp = pyotp.TOTP(self.totp_secret)

            if totp.verify(codigo):
                backup_codes = [f"{random.randint(100000, 999999)}" for _ in range(5)]
                backup_codes_str = ",".join(backup_codes)

                self.cursor.execute(
                    "UPDATE Usuarios SET totp_secret = ?, totp_enabled = 1, backup_codes = ? WHERE nombre = ?",
                    (self.totp_secret, backup_codes_str, self.usuario_nombre)
                )
                self.conn.commit()

                backup_text = "\n".join([f"• {code}" for code in backup_codes])
                messagebox.showwarning(
                    "⚠️ Códigos de Respaldo",
                    f"Guarda estos códigos en lugar seguro:\n\n{backup_text}\n\nSi pierdes tu teléfono, necesitarás estos códigos.",
                    parent=self.root
                )

                Notification(
                    self.root,
                    "✅ 2FA Configurado",
                    "Autenticación 2FA activada correctamente",
                    notification_type="success"
                )

                self.mostrar_login()
            else:
                Notification(
                    self.root,
                    "❌ Error",
                    "El código es incorrecto o ha expirado",
                    notification_type="error"
                )
        except Exception as e:
            Notification(
                self.root,
                "❌ Error",
                str(e),
                notification_type="error"
            )

    def verificar_2fa(self):
        """Verifica código 2FA en login"""
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
                totp_secret = result[0]
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
        """Usa un código de respaldo"""
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
                backup_codes = result[0].split(",")

                if codigo in backup_codes:
                    backup_codes.remove(codigo)
                    backup_codes_str = ",".join(backup_codes)

                    self.cursor.execute(
                        "UPDATE Usuarios SET backup_codes = ? WHERE id = ?",
                        (backup_codes_str, self.usuario_actual)
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
        """Completa el proceso de login"""
        self.frame_2fa.pack_forget()
        self.frame_principal.pack(expand=True, fill="both")
        colors = self.get_colors()
        self.status.configure(text=f"✅ Bienvenido, {self.usuario_nombre}!", text_color=colors["text_primary"])
        Notification(
            self.root,
            "✅ Sesión Iniciada",
            "Acceso verificado - 2FA Exitoso",
            notification_type="success",
            duration=2000
        )
        self.cargar_dashboard()
        self.ver_pdfs()

    def cargar_dashboard(self):
        """Carga el dashboard"""
        for widget in self.dashboard_container.winfo_children():
            widget.destroy()

        dashboard = DashboardWidget(self.dashboard_container, self.cursor, self.usuario_actual)
        dashboard.pack(fill="both", padx=20)

    def mostrar_agregar_pdf(self):
        """Muestra ventana para agregar PDF"""
        if not self.usuario_actual:
            Notification(
                self.root,
                "❌ Error",
                "No hay usuario autenticado",
                notification_type="error"
            )
            return

        add_window = ctk.CTkToplevel(self.root)
        add_window.title("Agregar PDF")
        add_window.geometry("600x500")
        colors = self.get_colors()
        add_window.configure(fg_color=COLOR_BG_LIGHT)

        ctk.CTkLabel(
            add_window,
            text="➕ Agregar Nuevo PDF",
            font=("Arial", 18, "bold"),
            text_color=colors["text_primary"]
        ).pack(pady=15)

        self.selected_file = None

        btn_buscar = ctk.CTkButton(
            add_window,
            text="📁 Buscar Archivo PDF",
            command=self.seleccionar_archivo,
            fg_color=COLOR_PRIMARY,
            hover_color="#388E3C",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 12, "bold"),
            corner_radius=8,
            width=250,
            height=40
        )
        btn_buscar.pack(pady=15)

        self.label_file = ctk.CTkLabel(
            add_window,
            text="📄 Ningún archivo seleccionado",
            text_color=colors["text_primary"],
            font=("Arial", 10)
        )
        self.label_file.pack(pady=10)

        ctk.CTkLabel(
            add_window,
            text="Descripción:",
            text_color=colors["text_primary"],
            font=("Arial", 11, "bold")
        ).pack()

        self.entry_descripcion = ctk.CTkEntry(
            add_window,
            placeholder_text="Descripción del PDF",
            width=300,
            height=35,
            corner_radius=8,
            border_width=2,
            font=("Arial", 11)
        )
        self.entry_descripcion.pack(pady=10)

        ctk.CTkLabel(
            add_window,
            text="Cédula:",
            text_color=colors["text_primary"],
            font=("Arial", 11, "bold")
        ).pack()

        self.entry_cedula = ctk.CTkEntry(
            add_window,
            placeholder_text="Cédula",
            width=300,
            height=35,
            corner_radius=8,
            border_width=2,
            font=("Arial", 11)
        )
        self.entry_cedula.pack(pady=10)

        ctk.CTkLabel(
            add_window,
            text="Nombres:",
            text_color=colors["text_primary"],
            font=("Arial", 11, "bold")
        ).pack()

        self.entry_nombres = ctk.CTkEntry(
            add_window,
            placeholder_text="Nombres",
            width=300,
            height=35,
            corner_radius=8,
            border_width=2,
            font=("Arial", 11)
        )
        self.entry_nombres.pack(pady=10)

        btn_agregar = ctk.CTkButton(
            add_window,
            text="✅ Agregar (Encriptado)",
            command=lambda: self.procesar_agregar_pdf(add_window),
            fg_color=COLOR_SECONDARY,
            hover_color="#1976D2",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 12, "bold"),
            corner_radius=8,
            width=250,
            height=40
        )
        btn_agregar.pack(pady=15)

    def seleccionar_archivo(self):
        """Selecciona un archivo PDF"""
        self.selected_file = filedialog.askopenfilename(
            filetypes=[("PDF files", "*.pdf")]
        )
        if self.selected_file:
            self.label_file.configure(text=f"📄 {os.path.basename(self.selected_file)}")

    def procesar_agregar_pdf(self, window):
        """Procesa la adición de un PDF: encripta en segundo plano, guarda en BD en hilo principal"""
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

        # Capture state for the background thread to avoid closure over attrs
        # that might change while the thread runs.
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
                # Hand off DB write to the main thread
                self.root.after(0, lambda: self._save_pdf_to_db(
                    datos_enc, tamano, nombre, descripcion,
                    cedula, nombres, usuario_actual, window
                ))
            except Exception as e:
                self.root.after(0, lambda err=e: self._on_pdf_add_error(err))
                self.root.after(0, self.progress_bar.stop)

        threading.Thread(target=encrypt_task, daemon=True).start()

    def ver_pdfs(self):
        """Muestra todos los PDFs"""
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
        """Busca PDFs según término"""
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
        """Muestra detalles de un PDF"""
        selected = self.tree.selection()

        if not selected:
            Notification(
                self.root,
                "⚠️ Advertencia",
                "Selecciona un PDF de la lista",
                notification_type="warning"
            )
            return

        values = self.tree.item(selected[0])['values']
        pdf_id, pdf_nombre, descripcion, tamano, fecha, cedula, nombres = values

        details_window = ctk.CTkToplevel(self.root)
        details_window.title("Detalles del PDF")
        details_window.geometry("500x400")
        colors = self.get_colors()
        details_window.configure(fg_color=COLOR_BG_LIGHT)

        ctk.CTkLabel(
            details_window,
            text="ℹ️  Detalles del PDF",
            font=("Arial", 18, "bold"),
            text_color=colors["text_primary"]
        ).pack(pady=15)

        info_text = f"""
ID: {pdf_id}
Nombre: {pdf_nombre}
Descripción: {descripcion}
Tamaño: {tamano}
Fecha: {fecha}
Cédula: {cedula}
Nombres: {nombres}

🔒 Estado: Encriptado con AES-256
        """

        ctk.CTkLabel(
            details_window,
            text=info_text,
            text_color=colors["text_primary"],
            font=("Arial", 11),
            justify="left"
        ).pack(pady=10, padx=20)

        btn_abrir = ctk.CTkButton(
            details_window,
            text="📂 Desencriptar y Abrir",
            command=lambda: self.abrir_pdf_id(pdf_id, details_window),
            fg_color=COLOR_SECONDARY,
            hover_color="#1976D2",
            text_color=COLOR_TEXT_DARK,
            font=("Arial", 11, "bold"),
            corner_radius=8,
            width=200,
            height=40
        )
        btn_abrir.pack(pady=10)

    def abrir_pdf_doble_click(self):
        """Abre un PDF con doble click"""
        selected = self.tree.selection()

        if not selected:
            return

        values = self.tree.item(selected[0])['values']
        pdf_id = values[0]
        self.abrir_pdf_id(pdf_id)

    def abrir_pdf_id(self, pdf_id, window=None):
        """Abre un PDF: consulta BD en hilo principal, desencripta en segundo plano"""
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
                # bytes() ensures we have a real bytes object regardless of
                # whether SQLite returned bytes or a memoryview buffer.
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
        """Elimina un PDF seleccionado"""
        selected = self.tree.selection()

        if not selected:
            Notification(
                self.root,
                "⚠️ Advertencia",
                "Selecciona un PDF de la lista",
                notification_type="warning"
            )
            return

        pdf_id = self.tree.item(selected[0])['values'][0]

        if messagebox.askyesno("Confirmación", "¿Estás seguro de que deseas eliminar este PDF?", parent=self.root):
            self.progress_bar.start("Eliminando PDF...")

            try:
                self.cursor.execute(
                    "DELETE FROM PDFs WHERE id = ? AND usuario_id = ?",
                    (pdf_id, self.usuario_actual)
                )

                if self.cursor.rowcount == 0:
                    Notification(
                        self.root,
                        "❌ Error",
                        "PDF no encontrado",
                        notification_type="error"
                    )
                    return

                self.cursor.execute(
                    "INSERT INTO Auditoria (accion, pdf_id, usuario_id, fecha) VALUES (?, ?, ?, ?)",
                    ("Eliminar PDF", pdf_id, self.usuario_actual, datetime.now().isoformat())
                )

                self.conn.commit()
                Notification(
                    self.root,
                    "✅ Éxito",
                    "PDF eliminado correctamente",
                    notification_type="success"
                )
                self.cargar_dashboard()
                self.ver_pdfs()
            except Exception as e:
                self.conn.rollback()
                Notification(
                    self.root,
                    "❌ Error",
                    str(e),
                    notification_type="error"
                )
            finally:
                self.progress_bar.stop()

    def slide_in_frame(self, frame, start_relx=1.0, end_relx=0.0, steps=20, callback=None):
        """Anima el deslizamiento de un frame"""
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
        """Cierra la conexión y sale"""
        self.cerrar_conexion()
        self.root.destroy()

    def cerrar_conexion(self):
        """Cierra la conexión a la BD"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def on_intro_click(self, event):
        """Evento al hacer clic en intro"""
        self.frame_intro.pack_forget()
        self.mostrar_inicial()

# ═══════════════════════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = ctk.CTk()
    app = AppDBPDF(root)
    root.protocol("WM_DELETE_WINDOW", app.cerrar_conexion_y_salir)
    root.mainloop()
