#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui_components.py - Módulo de Componentes UI
Contiene widgets reutilizables para la interfaz
Colores adaptados dinámicamente a modo oscuro/claro
"""

import customtkinter as ctk
import os

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PARA OBTENER COLORES DINÁMICOS SEGÚN EL TEMA
# ═══════════════════════════════════════════════════════════════════════════════

def get_dynamic_colors():
    """Retorna colores dinámicos según el tema actual"""
    mode = ctk.get_appearance_mode()
    
    if mode == "Dark":
        return {
            "bg_primary": "#1a1a1a",
            "bg_secondary": "#2c2434",
            "text_primary": "#FFFFFF",
            "text_secondary": "#E0E0E0",
            "accent": "#4CAF50",
            "secondary": "#2196F3",
            "warning": "#FF9800",
            "error": "#F44336",
            "success": "#4CAF50"
        }
    else:  # Light mode
        return {
            "bg_primary": "#F5F5F5",
            "bg_secondary": "#FFFFFF",
            "text_primary": "#004D40",
            "text_secondary": "#333333",
            "accent": "#4CAF50",
            "secondary": "#2196F3",
            "warning": "#FF9800",
            "error": "#F44336",
            "success": "#4CAF50"
        }

# Colores estáticos (no cambian)
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
# CLASE DE NOTIFICACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

class Notification(ctk.CTkToplevel):
    """Notificaciones emergentes tipo toast"""

    COLORS = {
        "success": COLOR_SUCCESS,
        "error": COLOR_ERROR,
        "warning": COLOR_WARNING,
        "info": COLOR_SECONDARY
    }

    def __init__(self, parent, title, message, notification_type="info", duration=3000):
        super().__init__(parent)

        self.title("")
        self.geometry("400x120")
        self.resizable(False, False)

        if os.name == 'nt':
            self.wm_attributes('-topmost', True)

        color = self.COLORS.get(notification_type, self.COLORS["info"])
        self.configure(fg_color=color)

        frame = ctk.CTkFrame(self, fg_color=color)
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(
            frame,
            text=title,
            font=("Arial", 14, "bold"),
            text_color="white"
        ).pack(anchor="w", pady=(0, 5))

        ctk.CTkLabel(
            frame,
            text=message,
            font=("Arial", 11),
            text_color="white",
            wraplength=350,
            justify="left"
        ).pack(anchor="w")

        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = screen_width - 430
        y = screen_height - 160
        self.geometry(f"+{x}+{y}")

        self.after(duration, self.destroy)

# ═══════════════════════════════════════════════════════════════════════════════
# CLASE DE BARRA DE PROGRESO MEJORADA
# ═══════════════════════════════════════════════════════════════════════════════

class ProgressBarModerno:
    """Barra de progreso moderna con porcentaje"""

    def __init__(self, parent, width=600, height=20):
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.parent = parent

        top_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        top_frame.pack(fill="x", padx=20)

        # Obtener colores dinámicos
        colors = get_dynamic_colors()

        self.label_text = ctk.CTkLabel(
            top_frame,
            text="Procesando...",
            text_color=colors["text_primary"],
            font=("Arial", 10, "bold")
        )
        self.label_text.pack(side="left")

        self.label_percent = ctk.CTkLabel(
            top_frame,
            text="0%",
            text_color=COLOR_PRIMARY,
            font=("Arial", 10, "bold")
        )
        self.label_percent.pack(side="right")

        self.progress = ctk.CTkProgressBar(
            self.frame,
            mode="indeterminate",
            indeterminate_speed=1.5,
            fg_color="#E0E0E0",
            progress_color=COLOR_PRIMARY,
            height=height
        )
        self.progress.pack(fill="x", padx=20, pady=(5, 10))

        self.animating = False

    def start(self, text="Procesando..."):
        """Inicia animación"""
        if not self.animating:
            colors = get_dynamic_colors()
            self.label_text.configure(text=text, text_color=colors["text_primary"])
            self.progress.start()
            self.animating = True
            self.frame.pack(fill="x", pady=5)

    def stop(self):
        """Detiene animación"""
        if self.animating:
            self.progress.stop()
            self.animating = False
            self.frame.pack_forget()

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

# ═══════════════════════════════════════════════════════════════════════════════
# CLASE DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

class DashboardWidget:
    """Widget de dashboard con estadísticas"""

    def __init__(self, parent, cursor, usuario_id):
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.cursor = cursor
        self.usuario_id = usuario_id
        self.construir_dashboard()

    def construir_dashboard(self):
        """Construye el dashboard"""
        from database import format_size
        
        colors = get_dynamic_colors()
        
        title = ctk.CTkLabel(
            self.frame,
            text="📊 ESTADÍSTICAS",
            font=("Arial", 14, "bold"),
            text_color=colors["text_primary"]
        )
        title.pack(pady=10)

        stats_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        stats_frame.pack(fill="both", padx=20)

        self.cursor.execute(
            "SELECT COUNT(*), SUM(tamano) FROM PDFs WHERE usuario_id = ?",
            (self.usuario_id,)
        )
        total_pdfs, total_size = self.cursor.fetchone()
        total_pdfs = total_pdfs or 0
        total_size = total_size or 0

        self.cursor.execute(
            "SELECT COUNT(DISTINCT persona_id) FROM PDFs WHERE usuario_id = ?",
            (self.usuario_id,)
        )
        total_personas = self.cursor.fetchone()[0] or 0

        tarjetas = [
            ("📄", f"{total_pdfs}", "PDFs Totales"),
            ("💾", format_size(total_size), "Espacio Usado"),
            ("👥", f"{total_personas}", "Personas"),
            ("🔒", "AES-256", "Encriptación")
        ]

        for icono, valor, label in tarjetas:
            self.crear_tarjeta(stats_frame, icono, valor, label, colors)

    def crear_tarjeta(self, parent, icono, valor, label, colors):
        """Crea una tarjeta de estadística"""
        card = ctk.CTkFrame(parent, fg_color=COLOR_SECONDARY, corner_radius=10)
        card.pack(side="left", padx=10, pady=10, expand=True, fill="both")

        ctk.CTkLabel(
            card,
            text=icono,
            font=("Arial", 24),
            text_color="white"
        ).pack(pady=(10, 5))

        ctk.CTkLabel(
            card,
            text=valor,
            font=("Arial", 18, "bold"),
            text_color="white"
        ).pack(pady=5)

        ctk.CTkLabel(
            card,
            text=label,
            font=("Arial", 10),
            text_color="white"
        ).pack(pady=(5, 10))

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
