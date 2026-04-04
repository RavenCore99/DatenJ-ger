#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui_components.py - Módulo de Componentes UI
Contiene widgets reutilizables para la interfaz
Colores adaptados dinámicamente a modo oscuro/claro
"""

import customtkinter as ctk
import tkinter as tk
import os
import math

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PARA OBTENER COLORES DINÁMICOS SEGÚN EL TEMA
# ═══════════════════════════════════════════════════════════════════════════════

def get_dynamic_colors():
    """Retorna colores dinámicos según el tema actual.
    Los colores del modo oscuro son más vívidos y saturados para mayor
    contraste visual. Los del modo claro son más cálidos y definidos.
    """
    mode = ctk.get_appearance_mode()

    # ┌──────────────────────────────────────────────────────────────────────┐
    # │  [AJUSTE VISUAL] - Paleta de colores globales                        │
    # │  Cambia estos valores hexadecimales para ajustar la paleta de        │
    # │  colores de toda la aplicación de una sola vez.                      │
    # │  Modo oscuro: fondos azul-marino profundo, acentos vibrantes         │
    # │  Modo claro:  fondos azul-hielo suaves, textos azul índigo           │
    # └──────────────────────────────────────────────────────────────────────┘
    if mode == "Dark":
        return {
            "bg_primary":      "#0d0f1a",   # fondo principal — muy oscuro
            "bg_secondary":    "#141628",   # fondo de tarjetas/ventanas
            "bg_card":         "#1a2050",   # fondo de cards secundarias
            "text_primary":    "#ffffff",   # texto principal — blanco puro
            "text_secondary":  "#b0c4de",   # texto secundario — azul pálido
            "accent":          "#00e676",   # verde eléctrico vívido
            "secondary":       "#40c4ff",   # azul cyan eléctrico
            "warning":         "#ffab40",   # naranja cálido
            "error":           "#ff5252",   # rojo coral vívido
            "success":         "#00e676",   # verde eléctrico vívido
            "gradient_start":  "#0d0f1a",
            "gradient_end":    "#1a2050",
        }
    else:  # Light mode
        return {
            "bg_primary":      "#eef2ff",   # fondo principal — azul muy claro
            "bg_secondary":    "#ffffff",   # blanco puro
            "bg_card":         "#dde6ff",   # azul claro para cards
            "text_primary":    "#1a237e",   # azul índigo oscuro
            "text_secondary":  "#37474f",   # gris azulado
            "accent":          "#2e7d32",   # verde bosque intenso
            "secondary":       "#1565c0",   # azul rey intenso
            "warning":         "#e65100",   # naranja quemado
            "error":           "#c62828",   # rojo oscuro
            "success":         "#2e7d32",   # verde bosque intenso
            "gradient_start":  "#dde6ff",
            "gradient_end":    "#b3ccff",
        }

# Colores estáticos (no cambian con el tema)
# [AJUSTE VISUAL] - Ajusta estos valores para cambiar los colores de botones
#                  y elementos de acción globalmente.
COLOR_BG_LIGHT   = "#eef2ff"
COLOR_BG_DARK    = "#0d0f1a"
COLOR_PRIMARY    = "#2e7d32"   # botones de acción principal (verde)
COLOR_SECONDARY  = "#1565c0"   # botones secundarios (azul)
COLOR_WARNING    = "#e65100"   # advertencias (naranja)
COLOR_ERROR      = "#c62828"   # errores/eliminaciones (rojo)
COLOR_SUCCESS    = "#2e7d32"   # éxito (verde)
COLOR_TEXT_LIGHT = "#1a237e"
COLOR_TEXT_DARK  = "#ffffff"

# ═══════════════════════════════════════════════════════════════════════════════
# CLASE DE NOTIFICACIÓN APILABLE
# ═══════════════════════════════════════════════════════════════════════════════

# Registro global de notificaciones activas para apilarlas
_active_notifications = []


class Notification(ctk.CTkToplevel):
    """Notificaciones emergentes tipo toast con apilamiento automático"""

    COLORS = {
        "success": ("#1b5e20", "#2e7d32"),
        "error":   ("#b71c1c", "#c62828"),
        "warning": ("#bf360c", "#d84315"),
        "info":    ("#0d47a1", "#1565c0"),
    }
    ICONS = {
        "success": "✅",
        "error":   "❌",
        "warning": "⚠️",
        "info":    "ℹ️",
    }

    def __init__(self, parent, title, message, notification_type="info", duration=3000):
        super().__init__(parent)

        self.title("")
        self.resizable(False, False)
        self.overrideredirect(True)

        if os.name == 'nt':
            self.wm_attributes('-topmost', True)
        else:
            self.attributes('-topmost', True)

        colors = self.COLORS.get(notification_type, self.COLORS["info"])
        icon = self.ICONS.get(notification_type, "ℹ️")
        self.configure(fg_color=colors[0])

        # Rounded outer frame
        outer = ctk.CTkFrame(self, fg_color=colors[1], corner_radius=12)
        outer.pack(fill="both", expand=True, padx=2, pady=2)

        content = ctk.CTkFrame(outer, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=10)

        # Icon + title row
        top_row = ctk.CTkFrame(content, fg_color="transparent")
        top_row.pack(fill="x")

        ctk.CTkLabel(
            top_row,
            text=icon,
            font=("Arial", 18),
            text_color="white"
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            top_row,
            text=title,
            font=("Arial", 13, "bold"),
            text_color="white"
        ).pack(side="left", anchor="w")

        # Close button
        close_btn = ctk.CTkButton(
            top_row,
            text="✕",
            width=22,
            height=22,
            fg_color="transparent",
            hover_color=colors[0],
            text_color="white",
            font=("Arial", 11, "bold"),
            command=self._close
        )
        close_btn.pack(side="right")

        # Message
        ctk.CTkLabel(
            content,
            text=message,
            font=("Arial", 11),
            text_color="#f0f0f0",
            wraplength=320,
            justify="left"
        ).pack(anchor="w", pady=(4, 0))

        # Thin progress bar at bottom to indicate duration
        self._progress = ctk.CTkProgressBar(
            content, height=3,
            fg_color=colors[0],
            progress_color="white",
            corner_radius=0
        )
        self._progress.set(1.0)
        self._progress.pack(fill="x", pady=(6, 0))

        self.update_idletasks()

        _active_notifications.append(self)
        self._reposition_all()
        self._animate_progress(duration)
        self.after(duration, self._close)

    @staticmethod
    def _reposition_all():
        """Repositions all active notifications in a stack at the bottom-right."""
        screen_w = _active_notifications[0].winfo_screenwidth() if _active_notifications else 1920
        screen_h = _active_notifications[0].winfo_screenheight() if _active_notifications else 1080
        notif_w = 380
        notif_h = 120
        margin = 14
        x = screen_w - notif_w - 20
        for i, n in enumerate(reversed(_active_notifications)):
            y = screen_h - (notif_h + margin) * (i + 1) - 40
            n.geometry(f"{notif_w}x{notif_h}+{x}+{y}")

    def _animate_progress(self, duration):
        steps = 40
        interval = duration // steps

        def tick(step=steps):
            if step > 0 and self.winfo_exists():
                self._progress.set(step / steps)
                self.after(interval, tick, step - 1)

        tick()

    def _close(self):
        if self in _active_notifications:
            _active_notifications.remove(self)
        if self.winfo_exists():
            self.destroy()
        if _active_notifications:
            Notification._reposition_all()


# ═══════════════════════════════════════════════════════════════════════════════
# WIDGET INDICADOR DE FORTALEZA DE CONTRASEÑA
# ═══════════════════════════════════════════════════════════════════════════════

class PasswordStrengthBar:
    """Indicador visual de fortaleza de contraseña"""

    def __init__(self, parent):
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")

        self.bars_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.bars_frame.pack(fill="x")

        self._bars = []
        for _ in range(4):
            bar = ctk.CTkFrame(self.bars_frame, height=5, fg_color="#444444", corner_radius=3)
            bar.pack(side="left", expand=True, fill="x", padx=2)
            self._bars.append(bar)

        self.label = ctk.CTkLabel(
            self.frame,
            text="",
            font=("Arial", 9),
            text_color="#888888"
        )
        self.label.pack(pady=(2, 0))

    def update(self, password: str):
        from database import password_strength
        score, label, color = password_strength(password)
        inactive = "#3a3a3a" if ctk.get_appearance_mode() == "Dark" else "#cccccc"
        for i, bar in enumerate(self._bars):
            bar.configure(fg_color=color if i < score else inactive)
        self.label.configure(text=label, text_color=color)

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# FONDO CON GRADIENTE ANIMADO
# ═══════════════════════════════════════════════════════════════════════════════

class GradientBackground(tk.Canvas):
    """Canvas que pinta un gradiente vertical animado que oscila suavemente.
    Los colores son más vívidos y saturados comparados con la versión anterior.
    """

    def __init__(self, parent, colors_dark=None, colors_light=None, **kwargs):
        super().__init__(parent, highlightthickness=0, **kwargs)
        self._phase = 0.0
        # [AJUSTE VISUAL] - Paletas de gradiente: cada par (inicio, fin) define
        # el gradiente de la pantalla. Cambia los hex para ajustar los fondos.
        self._colors_dark  = colors_dark  or [
            ("#050714", "#1a2050"),
            ("#1a2050", "#0a1535")
        ]
        self._colors_light = colors_light or [
            ("#c5d5ff", "#8ab4ff"),
            ("#8ab4ff", "#dde8ff")
        ]
        # [AJUSTE VISUAL] - Velocidad de la animación del gradiente:
        # Valores más altos = animación más rápida (rango recomendado: 0.008–0.025)
        self._speed = 0.018
        self.bind("<Configure>", self._on_resize)
        self.bind("<Map>", self._on_resize)
        self._animate()

    def _lerp_color(self, c1, c2, t):
        """Interpola entre dos colores hex"""
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _draw(self):
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 2 or h < 2:
            return
        self.delete("all")
        mode = ctk.get_appearance_mode()
        palette = self._colors_dark if mode == "Dark" else self._colors_light

        # Pick the two gradient pairs to blend between
        t_cycle = (math.sin(self._phase) + 1) / 2  # 0..1
        c1a, c1b = palette[0]
        c2a, c2b = palette[1]
        top_color    = self._lerp_color(c1a, c2a, t_cycle)
        bottom_color = self._lerp_color(c1b, c2b, t_cycle)

        steps = max(h // 2, 20)
        for i in range(steps):
            t = i / steps
            color = self._lerp_color(top_color, bottom_color, t)
            y0 = int(i * h / steps)
            y1 = int((i + 1) * h / steps) + 1
            self.create_rectangle(0, y0, w, y1, fill=color, outline="")

    def _animate(self):
        self._phase += self._speed
        self._draw()
        self.after(60, self._animate)

    def _on_resize(self, event):
        self._draw()


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
            text="",
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
    """Widget de dashboard con estadísticas y animación de entrada"""

    # ┌──────────────────────────────────────────────────────────────────────┐
    # │  [AJUSTE VISUAL] - Colores de las tarjetas de estadísticas           │
    # │  Cada tupla contiene: (icono, valor, etiqueta, color_fondo)          │
    # │  Cambia el color_fondo hex para personalizar cada tarjeta.           │
    # └──────────────────────────────────────────────────────────────────────┘
    CARD_COLORS = {
        "pdfs":       "#0d47a1",   # azul marino vívido
        "espacio":    "#6a1b9a",   # morado eléctrico
        "personas":   "#00695c",   # teal profundo
        "cifrado":    "#1b5e20",   # verde bosque oscuro
    }
    # [AJUSTE VISUAL] - Retardo entre la aparición escalonada de cada tarjeta (ms)
    CARD_ANIMATION_DELAY_MS: int = 160
    # [AJUSTE VISUAL] - Factor de oscurecimiento inicial de las tarjetas (0.0–1.0)
    FADE_DIM_FACTOR: float = 0.10

    def __init__(self, parent, cursor, usuario_id):
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.cursor = cursor
        self.usuario_id = usuario_id
        self._tarjeta_refs = []   # guarda (card_frame, color_objetivo)
        self.construir_dashboard()

    def construir_dashboard(self):
        """Construye el dashboard"""
        from database import format_size

        colors = get_dynamic_colors()

        # [AJUSTE VISUAL] - Tamaño y fuente del título del dashboard
        title = ctk.CTkLabel(
            self.frame,
            text="📊 ESTADÍSTICAS DEL REPOSITORIO",
            font=("Arial", 13, "bold"),
            text_color=colors["text_secondary"]
        )
        title.pack(pady=(8, 4))
        self._title_label = title

        stats_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        stats_frame.pack(fill="both", padx=10)

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
            ("📄", f"{total_pdfs}", "PDFs Totales",  self.CARD_COLORS["pdfs"]),
            ("💾", format_size(total_size), "Espacio Usado", self.CARD_COLORS["espacio"]),
            ("👥", f"{total_personas}", "Personas",    self.CARD_COLORS["personas"]),
            ("🔒", "AES-256", "Cifrado",              self.CARD_COLORS["cifrado"]),
        ]

        for icono, valor, label, color in tarjetas:
            card = self.crear_tarjeta(stats_frame, icono, valor, label, color)
            self._tarjeta_refs.append((card, color))

    def crear_tarjeta(self, parent, icono, valor, label, color):
        """Crea una tarjeta de estadística.
        [AJUSTE VISUAL] - corner_radius: redondeo de esquinas (0-20)
                          padx/pady: espaciado interior de la tarjeta
        """
        card = ctk.CTkFrame(parent, fg_color=color, corner_radius=14)
        card.pack(side="left", padx=8, pady=6, expand=True, fill="both")

        # [AJUSTE VISUAL] - Tamaño del ícono de la tarjeta
        ctk.CTkLabel(
            card,
            text=icono,
            font=("Arial", 24),
            text_color="white"
        ).pack(pady=(10, 2))

        # [AJUSTE VISUAL] - Tamaño del valor numérico principal
        ctk.CTkLabel(
            card,
            text=valor,
            font=("Arial", 18, "bold"),
            text_color="white"
        ).pack(pady=2)

        # [AJUSTE VISUAL] - Tamaño de la etiqueta descriptiva de la tarjeta
        ctk.CTkLabel(
            card,
            text=label,
            font=("Arial", 9),
            text_color="#dddddd"
        ).pack(pady=(2, 10))

        return card

    # ── Animación de entrada ────────────────────────────────────────────────

    def animar_entrada(self, delay_base: int = 0):
        """Lanza la animación de fade-in para cada tarjeta con retraso escalonado.

        :param delay_base: milisegundos de espera antes de iniciar la secuencia.
        [AJUSTE VISUAL] - Modifica CARD_ANIMATION_DELAY_MS en la clase para
                          acelerar/ralentizar la aparición escalonada entre tarjetas.
        """
        for i, (card, target_color) in enumerate(self._tarjeta_refs):
            delay = delay_base + i * self.CARD_ANIMATION_DELAY_MS
            self.frame.after(delay, lambda c=card, tc=target_color: self._fade_card(c, tc))

        # Animar título del dashboard también
        if hasattr(self, '_title_label') and self._title_label.winfo_exists():
            colors = get_dynamic_colors()
            dim = self._dim_color(colors["text_secondary"], 0.1)
            target = colors["text_secondary"]
            self.frame.after(delay_base, lambda: self._fade_label(
                self._title_label, dim, target))

    def _fade_card(self, card: ctk.CTkFrame, target_color: str,
                   steps: int = 18, interval: int = 20):
        """Anima el color de fondo de una tarjeta desde oscuro hasta su color objetivo.
        [AJUSTE VISUAL] - steps: cuántos pasos tiene la animación (más = más suave)
                          interval: ms entre pasos (más bajo = más rápido)
        """
        start_color = self._dim_color(target_color, self.FADE_DIM_FACTOR)

        def tick(step: int = 0):
            if not card.winfo_exists():
                return
            if step > steps:
                card.configure(fg_color=target_color)
                return
            t = self._ease_in_out(step / steps)
            color = self._lerp_hex(start_color, target_color, t)
            card.configure(fg_color=color)
            card.after(interval, tick, step + 1)

        tick()

    def _fade_label(self, label: ctk.CTkLabel, start_color: str, end_color: str,
                    steps: int = 16, interval: int = 25):
        """Anima el color del texto de un label desde start_color hasta end_color."""
        def tick(step: int = 0):
            if not label.winfo_exists():
                return
            if step > steps:
                label.configure(text_color=end_color)
                return
            t = self._ease_in_out(step / steps)
            color = self._lerp_hex(start_color, end_color, t)
            label.configure(text_color=color)
            label.after(interval, tick, step + 1)

        tick()

    # ── Utilidades de color ─────────────────────────────────────────────────

    @staticmethod
    def _dim_color(hex_color: str, factor: float = 0.2) -> str:
        """Oscurece un color multiplicando cada canal por un factor (0.0–1.0)."""
        r = int(int(hex_color[1:3], 16) * factor)
        g = int(int(hex_color[3:5], 16) * factor)
        b = int(int(hex_color[5:7], 16) * factor)
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _lerp_hex(c1: str, c2: str, t: float) -> str:
        """Interpola linealmente entre dos colores hex."""
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _ease_in_out(t: float) -> float:
        """Función de suavizado ease-in-out cúbico."""
        return t * t * (3 - 2 * t)

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# DIALOG DE CONFIRMACIÓN MODERNO
# ═══════════════════════════════════════════════════════════════════════════════

class ConfirmDialog(ctk.CTkToplevel):
    """Diálogo de confirmación moderno que sustituye a messagebox.askyesno"""

    def __init__(self, parent, title, message, confirm_text="Sí, confirmar",
                 cancel_text="Cancelar", danger=True):
        super().__init__(parent)
        self.result = False
        self.title(title)
        # [AJUSTE VISUAL] - Dimensiones del diálogo de confirmación
        self.geometry("420x220")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        if os.name != 'nt':
            self.attributes('-topmost', True)

        colors = get_dynamic_colors()
        self.configure(fg_color=colors["bg_secondary"])

        # [AJUSTE VISUAL] - Tamaño y fuente del título del diálogo
        ctk.CTkLabel(
            self, text=title, font=("Arial", 16, "bold"),
            text_color=colors["text_primary"]
        ).pack(pady=(20, 6))

        ctk.CTkLabel(
            self, text=message, font=("Arial", 11),
            text_color=colors["text_secondary"],
            wraplength=360, justify="center"
        ).pack(padx=20, pady=6)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=20)

        # [AJUSTE VISUAL] - Tamaño de los botones del diálogo (width, height)
        ctk.CTkButton(
            btn_row,
            text=cancel_text,
            command=self._cancel,
            fg_color="#616161",
            hover_color="#424242",
            width=160, height=38,
            font=("Arial", 11, "bold"),
            corner_radius=8
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_row,
            text=confirm_text,
            command=self._confirm,
            fg_color=COLOR_ERROR if danger else COLOR_PRIMARY,
            hover_color="#8b0000" if danger else "#1b5e20",
            width=160, height=38,
            font=("Arial", 11, "bold"),
            corner_radius=8
        ).pack(side="left", padx=8)

        self.wait_window()

    def _confirm(self):
        self.result = True
        self.destroy()

    def _cancel(self):
        self.result = False
        self.destroy()

