


# Modulo de Componentes UI
# Contiene widgets reutilizables para la interfaz
# Colores adaptados dinamicamente a modo oscuro/claro


import customtkinter as ctk
import tkinter as tk
import os
import math
from datetime import datetime, timedelta


# FUNCIon PARA OBTENER COLORES DINAMICOS SEGuN EL TEMA


def get_dynamic_colors():
    # retorna colores dinamicos según el tema actual
    mode = ctk.get_appearance_mode()
    
    if mode == "Dark": # Dark mode
        return {
            "bg_primary": "#1a1a2e",
            "bg_secondary": "#16213e",
            "bg_card": "#0f3460",
            "text_primary": "#e0e0e0",
            "text_secondary": "#a0a0a0",
            "accent": "#4CAF50",
            "secondary": "#2196F3",
            "warning": "#FF9800",
            "error": "#F44336",
            "success": "#4CAF50",
            "gradient_start": "#1a1a2e",
            "gradient_end": "#0f3460",
        }
    else:  # Light mode
        return {
            "bg_primary": "#f0f4ff",
            "bg_secondary": "#ffffff",
            "bg_card": "#e8f0fe",
            "text_primary": "#1a237e",
            "text_secondary": "#455a64",
            "accent": "#4CAF50",
            "secondary": "#2196F3",
            "warning": "#FF9800",
            "error": "#F44336",
            "success": "#4CAF50",
            "gradient_start": "#e8f0fe",
            "gradient_end": "#bbdefb",
        }

# colores estaticos (no cambian)
COLOR_BG_LIGHT = "#f0f4ff"
COLOR_BG_DARK = "#1a1a2e"
COLOR_PRIMARY = "#4CAF50"
COLOR_SECONDARY = "#2196F3"
COLOR_WARNING = "#FF9800"
COLOR_ERROR = "#F44336"
COLOR_SUCCESS = "#4CAF50"
COLOR_TEXT_LIGHT = "#1a237e"
COLOR_TEXT_DARK = "#e0e0e0"


# CLASE DE NOTIFICACIÓN APILABLE


# Registro global de notificaciones activas para apilarlas
_active_notifications = []


class Notification(ctk.CTkToplevel):
    # notificaciones emergentes tipo toast con apilamiento automatico

    COLORS = {
        "success": ("#2e7d32", "#43a047"),
        "error":   ("#c62828", "#e53935"),
        "warning": ("#e65100", "#ef6c00"),
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

        # barra de progreso de duracion
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
        # repossciona todas las notificaciones activas en una pila en la esquina inferior derecha
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



# WIDGET INDICADOR DE FORTALEZA DE CONTRASEÑA


class PasswordStrengthBar:
    # indicador visual de fortaleza de contraseña

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



# FONDO CON GRADIENTE ANIMADO


class GradientBackground(tk.Canvas):
    # canvas que pinta un gradiente vertical animado que oscila suavemente

    def __init__(self, parent, colors_dark=None, colors_light=None, **kwargs):
        super().__init__(parent, highlightthickness=0, **kwargs)
        self._phase = 0.0
        self._colors_dark  = colors_dark  or [("#0d0d2b", "#1a237e"), ("#1a237e", "#0d47a1")]
        self._colors_light = colors_light or [("#e3f2fd", "#bbdefb"), ("#bbdefb", "#e8f5e9")]
        self.bind("<Configure>", self._on_resize)
        self.bind("<Map>", self._on_resize)
        self._animate()

    def _lerp_color(self, c1, c2, t):
        # interpola entre dos colores hex
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

        # agarra los dos pares de colores de gradiente para mezclar entre ellos
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
        self._phase += 0.012
        self._draw()
        self.after(60, self._animate)

    def _on_resize(self, event):
        self._draw()


# ─
# FONDO COSMICO CON PARTICULAS — Improvement #13
#                                                   ──

class CosmicBackground(GradientBackground):
    """Fondo animado con gradiente + estrellas flotantes + nebulosas pulsantes."""

    def __init__(self, parent, num_stars=55, **kwargs):
        import random as _rnd
        self._stars = []
        self._nebulas = []
        self._num_stars = num_stars
        self._rnd = _rnd

        # Paleta cósmica oscura por defecto
        kwargs.setdefault("colors_dark",
                          [("#050510", "#0d1b3e"), ("#0d1b3e", "#1a0a2e")])
        kwargs.setdefault("colors_light",
                          [("#e3f2fd", "#f3e5f5"), ("#f3e5f5", "#e8f5e9")])

        super().__init__(parent, **kwargs)
        self._init_particles()

    def _init_particles(self):
        rnd = self._rnd
        self._stars = []
        for _ in range(self._num_stars):
            self._stars.append({
                "x": rnd.random(),
                "y": rnd.random(),
                "size": rnd.uniform(0.8, 2.5),
                "speed": rnd.uniform(0.0003, 0.0012),
                "brightness": rnd.uniform(0.4, 1.0),
                "phase": rnd.uniform(0, 2 * math.pi),
                "color_idx": rnd.randint(0, 2),  # 0=blanco, 1=azul, 2=violeta
            })

        # Nebulosas (manchas de glow grandes)
        self._nebulas = []
        for _ in range(4):
            self._nebulas.append({
                "x": rnd.uniform(0.1, 0.9),
                "y": rnd.uniform(0.1, 0.9),
                "radius": rnd.uniform(0.08, 0.18),
                "phase": rnd.uniform(0, 2 * math.pi),
                "hue": rnd.choice(["#1a237e", "#4a148c", "#006064", "#b71c1c"]),
            })

    def _draw(self):
        super()._draw()
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 2 or h < 2:
            return

        mode = ctk.get_appearance_mode()
        is_dark = mode == "Dark"

        # ── Nebulosas pulsantes ──
        if is_dark:
            for neb in self._nebulas:
                pulse = (math.sin(self._phase * 0.8 + neb["phase"]) + 1) / 2
                alpha_hex = int(8 + 14 * pulse)
                r_base = int(neb["hue"][1:3], 16)
                g_base = int(neb["hue"][3:5], 16)
                b_base = int(neb["hue"][5:7], 16)
                nx = neb["x"] * w
                ny = neb["y"] * h
                nr = neb["radius"] * min(w, h)
                # dibujar varias capas concéntricas para simular glow
                for layer in range(3):
                    factor = 1.0 - layer * 0.25
                    lr = nr * factor
                    r = min(255, r_base + int(40 * factor))
                    g = min(255, g_base + int(20 * factor))
                    b = min(255, b_base + int(40 * factor))
                    opacity = max(0, min(255, alpha_hex - layer * 3))
                    color = f"#{r:02x}{g:02x}{b:02x}"
                    self.create_oval(
                        nx - lr, ny - lr, nx + lr, ny + lr,
                        fill=color, outline="", stipple="gray12"
                    )

        # ── Estrellas ──
        star_palettes = {
            "Dark": [
                lambda a: f"#{int(180+75*a):02x}{int(180+75*a):02x}{int(200+55*a):02x}",
                lambda a: f"#{int(100+80*a):02x}{int(140+90*a):02x}{min(255,int(200+55*a)):02x}",
                lambda a: f"#{int(160+70*a):02x}{int(100+60*a):02x}{min(255,int(200+55*a)):02x}",
            ],
            "Light": [
                lambda a: f"#{int(140+40*a):02x}{int(140+40*a):02x}{int(160+40*a):02x}",
                lambda a: f"#{int(80+50*a):02x}{int(100+60*a):02x}{int(180+40*a):02x}",
                lambda a: f"#{int(130+40*a):02x}{int(80+30*a):02x}{int(170+40*a):02x}",
            ],
        }
        palette = star_palettes.get(mode, star_palettes["Dark"])

        for star in self._stars:
            # Movimiento ascendente suave
            star["y"] -= star["speed"]
            if star["y"] < -0.02:
                star["y"] = 1.02
                star["x"] = self._rnd.random()

            # Parpadeo
            twinkle = (math.sin(self._phase * 2.5 + star["phase"]) + 1) / 2
            alpha = star["brightness"] * (0.3 + 0.7 * twinkle)

            color_fn = palette[star["color_idx"]]
            color = color_fn(alpha)

            x = star["x"] * w
            y = star["y"] * h
            s = star["size"] * (0.6 + 0.4 * twinkle)

            self.create_oval(x - s, y - s, x + s, y + s,
                             fill=color, outline="")



# CLASE DE BARRA DE PROGRESO MEJORADA


class ProgressBarModerno:
    # barra de progreso moderna con porcentaje

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
        # inicia animacion
        if not self.animating:
            colors = get_dynamic_colors()
            self.label_text.configure(text=text, text_color=colors["text_primary"])
            self.progress.start()
            self.animating = True
            self.frame.pack(fill="x", pady=5)

    def stop(self):
        # detiene animacion
        if self.animating:
            self.progress.stop()
            self.animating = False
            self.frame.pack_forget()

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)


#                    #
# CLASE DASHBOARD  — improvement #11
# Gráficos visuales con matplotlib + regresión lineal (ML)
#                    #

class DashboardWidget:
    """Dashboard con tarjetas KPI, gráfico donut por empresa y línea de
    tendencia temporal con regresión lineal (numpy).
    Se integra con Tkinter via matplotlib FigureCanvasTkAgg."""

    def __init__(self, parent, cursor, usuario_id):
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.cursor = cursor
        self.usuario_id = usuario_id
        self._chart_canvases = []  # referencias para cleanup
        self.construir_dashboard()

    def _query_stats(self):
        """Consulta las estadísticas globales del usuario."""
        from database import format_size

        self.cursor.execute(
            "SELECT COUNT(*), COALESCE(SUM(tamano),0) FROM PDFs WHERE usuario_id = ?",
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

        self.cursor.execute(
            "SELECT COUNT(DISTINCT COALESCE(pe.empresa,'')) "
            "FROM PDFs p LEFT JOIN Personas pe ON p.persona_id = pe.id "
            "WHERE p.usuario_id = ?",
            (self.usuario_id,)
        )
        total_empresas = self.cursor.fetchone()[0] or 0

        return {
            "total_pdfs": total_pdfs,
            "total_size_str": format_size(total_size),
            "total_personas": total_personas,
            "total_empresas": total_empresas,
        }

    def _query_empresas(self):
        """Distribución de documentos por empresa."""
        self.cursor.execute(
            "SELECT COALESCE(pe.empresa, 'Sin empresa'), COUNT(*) "
            "FROM PDFs p LEFT JOIN Personas pe ON p.persona_id = pe.id "
            "WHERE p.usuario_id = ? "
            "GROUP BY COALESCE(pe.empresa, 'Sin empresa') "
            "ORDER BY COUNT(*) DESC",
            (self.usuario_id,)
        )
        return self.cursor.fetchall()

    def _query_timeline(self):
        """Subidas por día (para gráfico temporal y regresión)."""
        self.cursor.execute(
            "SELECT DATE(fecha_subida) AS dia, COUNT(*) "
            "FROM PDFs WHERE usuario_id = ? "
            "GROUP BY DATE(fecha_subida) ORDER BY dia ASC",
            (self.usuario_id,)
        )
        return self.cursor.fetchall()

    # ── Construcción ──────────────────────────────────────────────

    def construir_dashboard(self):
        import matplotlib
        matplotlib.use("Agg")  # backend sin ventana
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import numpy as np

        colors = get_dynamic_colors()
        is_dark = ctk.get_appearance_mode() == "Dark"
        stats = self._query_stats()
        empresas = self._query_empresas()
        timeline = self._query_timeline()

        # Colores matplotlib según tema
        fig_bg   = "#1a1a2e" if is_dark else "#f0f4ff"
        ax_bg    = "#16213e" if is_dark else "#f0f4ff"
        txt_col  = "#e0e0e0" if is_dark else "#1a237e"
        grid_col = "#2a3a5e" if is_dark else "#d0d8e8"
        ring_bg  = "#2a3a5e" if is_dark else "#d0d8e8"

        # ── Título ─────────────────────────────────────────
        ctk.CTkLabel(
            self.frame,
            text="📊 ESTADÍSTICAS DEL REPOSITORIO",
            font=("Arial", 13, "bold"),
            text_color=colors["text_secondary"]
        ).pack(pady=(8, 4))

        # ── Fila 1: 4 Mini-gauges + card AES ──────────────
        row1 = ctk.CTkFrame(self.frame, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=(2, 0))

        # --- 4 gauges como una sola figura matplotlib ---
        gauge_data = [
            (stats["total_pdfs"],     "PDFs Totales",  "#2196F3", 50),
            (stats["total_size_str"], "Espacio Usado",  "#7B1FA2", None),
            (stats["total_personas"], "Personas",       "#00897B", 30),
            (stats["total_empresas"], "Empresas",       "#E65100", 15),
        ]

        fig_g, axes_g = plt.subplots(1, 4, figsize=(7.8, 1.8), dpi=90)
        fig_g.patch.set_facecolor(fig_bg)

        for i, (valor, label, color, max_val) in enumerate(gauge_data):
            ax = axes_g[i]
            ax.set_facecolor(fig_bg)
            ax.set_aspect("equal")
            ax.axis("off")

            if max_val is not None and isinstance(valor, (int, float)):
                # gauge numérico: semicírculo de progreso
                ratio = min(valor / max(max_val, 1), 1.0)
                theta_bg = np.linspace(0, np.pi, 60)
                theta_fg = np.linspace(0, np.pi * ratio, max(2, int(60 * ratio)))

                r_outer = 1.0
                r_inner = 0.65

                # fondo del semicírculo
                x_bg = np.concatenate([r_outer * np.cos(theta_bg),
                                        r_inner * np.cos(theta_bg[::-1])])
                y_bg = np.concatenate([r_outer * np.sin(theta_bg),
                                        r_inner * np.sin(theta_bg[::-1])])
                ax.fill(x_bg, y_bg, color=ring_bg, alpha=0.4)

                # progreso del semicírculo
                x_fg = np.concatenate([r_outer * np.cos(theta_fg),
                                        r_inner * np.cos(theta_fg[::-1])])
                y_fg = np.concatenate([r_outer * np.sin(theta_fg),
                                        r_inner * np.sin(theta_fg[::-1])])
                ax.fill(x_fg, y_fg, color=color, alpha=0.9)

                # valor centrado
                ax.text(0, 0.35, str(valor),
                        ha="center", va="center",
                        fontsize=16, fontweight="bold", color=color)
            else:
                # gauge de texto (para espacio) — anillo completo decorativo
                theta_full = np.linspace(0, np.pi, 60)
                r_outer = 1.0
                r_inner = 0.65
                x_ring = np.concatenate([r_outer * np.cos(theta_full),
                                          r_inner * np.cos(theta_full[::-1])])
                y_ring = np.concatenate([r_outer * np.sin(theta_full),
                                          r_inner * np.sin(theta_full[::-1])])
                ax.fill(x_ring, y_ring, color=color, alpha=0.85)

                display_val = str(valor) if valor else "0 B"
                ax.text(0, 0.38, display_val,
                        ha="center", va="center",
                        fontsize=10, fontweight="bold", color="white" if is_dark else color)

            # label debajo
            ax.text(0, -0.15, label,
                    ha="center", va="center",
                    fontsize=7.5, color=txt_col, fontweight="bold")
            ax.set_xlim(-1.3, 1.3)
            ax.set_ylim(-0.4, 1.2)

        fig_g.tight_layout(pad=0.5)
        canvas_g = FigureCanvasTkAgg(fig_g, master=row1)
        canvas_g.draw()
        canvas_g.get_tk_widget().pack(side="left", fill="both",
                                       expand=True, padx=(0, 5))
        self._chart_canvases.append((fig_g, canvas_g))

        # --- Card AES-256-GCM (se mantiene como CTk widget) ---
        aes_card = ctk.CTkFrame(row1, fg_color=COLOR_PRIMARY,
                                 corner_radius=12, width=120)
        aes_card.pack(side="right", fill="y", padx=(5, 0), pady=4)
        aes_card.pack_propagate(False)

        ctk.CTkLabel(
            aes_card, text="🔒", font=("Arial", 20), text_color="white"
        ).pack(pady=(16, 2))
        ctk.CTkLabel(
            aes_card, text="AES-256",
            font=("Arial", 13, "bold"), text_color="white"
        ).pack(pady=0)
        ctk.CTkLabel(
            aes_card, text="GCM",
            font=("Arial", 11, "bold"), text_color="#c8e6c9"
        ).pack(pady=0)
        ctk.CTkLabel(
            aes_card, text="Encriptación",
            font=("Arial", 8), text_color="#dddddd"
        ).pack(pady=(2, 8))

        plt.close(fig_g)

        # ── Fila 2: Gráficos analíticos ──────────────────
        charts_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        charts_frame.pack(fill="x", padx=10, pady=(4, 4))

        # ── Gráfico 1: Donut chart por empresa ────────────
        fig1, ax1 = plt.subplots(figsize=(3.2, 2.4), dpi=90)
        fig1.patch.set_facecolor(fig_bg)
        ax1.set_facecolor(ax_bg)

        if empresas and stats["total_pdfs"] > 0:
            labels  = [e[0][:18] for e in empresas[:6]]
            valores = [e[1] for e in empresas[:6]]
            palette = ["#4CAF50", "#2196F3", "#9C27B0",
                       "#00897B", "#FF9800", "#E53935"]
            wedges, texts, autotexts = ax1.pie(
                valores, labels=None, autopct="%1.0f%%",
                colors=palette[:len(valores)],
                startangle=90, pctdistance=0.78,
                wedgeprops=dict(width=0.42, edgecolor=fig_bg, linewidth=1.5)
            )
            for t in autotexts:
                t.set_fontsize(7)
                t.set_color("white")
                t.set_fontweight("bold")
            ax1.legend(
                wedges, labels, loc="center left",
                bbox_to_anchor=(0.92, 0.5), fontsize=6.5,
                frameon=False, labelcolor=txt_col
            )
            ax1.set_title("Documentos por Empresa",
                          fontsize=9, fontweight="bold", color=txt_col, pad=8)
        else:
            ax1.text(0.5, 0.5, "Sin datos\naún",
                     ha="center", va="center", fontsize=10,
                     color=txt_col, alpha=0.5,
                     transform=ax1.transAxes)
            ax1.set_title("Documentos por Empresa",
                          fontsize=9, fontweight="bold", color=txt_col, pad=8)
            ax1.axis("off")

        fig1.tight_layout(pad=1.0)
        canvas1 = FigureCanvasTkAgg(fig1, master=charts_frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack(side="left", padx=(0, 5), pady=2,
                                      expand=True, fill="both")
        self._chart_canvases.append((fig1, canvas1))

        # ── Gráfico 2: Línea temporal + Regresión lineal ──
        fig2, ax2 = plt.subplots(figsize=(4.4, 2.4), dpi=90)
        fig2.patch.set_facecolor(fig_bg)
        ax2.set_facecolor(ax_bg)

        if timeline and len(timeline) >= 1:
            dias    = [t[0] for t in timeline]
            counts  = [t[1] for t in timeline]

            x_vals = np.arange(len(dias))

            bar_colors = "#4CAF50" if is_dark else "#2196F3"
            ax2.bar(x_vals, counts, color=bar_colors, alpha=0.7,
                    width=0.6, zorder=2, label="Subidas/día")

            if len(timeline) >= 2:
                coeffs = np.polyfit(x_vals, counts, 1)
                trend_line = np.polyval(coeffs, x_vals)
                ax2.plot(x_vals, trend_line, color="#FF9800",
                         linewidth=2, linestyle="--", zorder=3,
                         label=f"Tendencia (m={coeffs[0]:+.2f})")

                next_x = len(dias)
                pred_y = max(0, np.polyval(coeffs, next_x))
                ax2.scatter([next_x], [pred_y], color="#E53935",
                            s=40, zorder=4, marker="D",
                            label=f"Predicción: {pred_y:.0f}")

            if len(dias) <= 10:
                ax2.set_xticks(x_vals)
                ax2.set_xticklabels(
                    [d[5:] for d in dias],
                    fontsize=6, rotation=35, color=txt_col
                )
            else:
                step = max(1, len(dias) // 8)
                ticks = x_vals[::step]
                ax2.set_xticks(ticks)
                ax2.set_xticklabels(
                    [dias[i][5:] for i in ticks],
                    fontsize=6, rotation=35, color=txt_col
                )

            ax2.set_ylabel("Documentos", fontsize=7, color=txt_col)
            ax2.tick_params(axis="y", labelsize=7, colors=txt_col)
            ax2.grid(axis="y", color=grid_col, linewidth=0.4, alpha=0.5)
            ax2.legend(fontsize=6, frameon=False, labelcolor=txt_col,
                       loc="upper left")
            ax2.set_title("Actividad Temporal ", 
                          fontsize=9, fontweight="bold", color=txt_col, pad=8)

            if len(timeline) >= 3:
                y_mean = np.mean(counts)
                ss_tot = np.sum((np.array(counts) - y_mean) ** 2)
                ss_res = np.sum((np.array(counts) - trend_line) ** 2)
                r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                ax2.text(0.98, 0.02, f"R²={r2:.3f}",
                         transform=ax2.transAxes, fontsize=6.5,
                         ha="right", va="bottom", color="#FF9800",
                         fontweight="bold", alpha=0.8)
        else:
            ax2.text(0.5, 0.5,
                     "Sin datos temporales\nSube documentos para ver tendencias",
                     ha="center", va="center", fontsize=9,
                     color=txt_col, alpha=0.5,
                     transform=ax2.transAxes)
            ax2.set_title("Actividad Temporal + Regresión Lineal",
                          fontsize=9, fontweight="bold", color=txt_col, pad=8)
            ax2.axis("off")

        fig2.tight_layout(pad=1.0)
        canvas2 = FigureCanvasTkAgg(fig2, master=charts_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(side="left", padx=(5, 0), pady=2,
                                      expand=True, fill="both")
        self._chart_canvases.append((fig2, canvas2))

        plt.close(fig1)
        plt.close(fig2)

    # ── Cleanup ───────────────────────────────────────────

    def destroy(self):
        """Libera recursos de matplotlib al destruir el widget."""
        for fig, canvas in self._chart_canvases:
            try:
                canvas.get_tk_widget().destroy()
            except Exception:
                pass
        self._chart_canvases.clear()
        self.frame.destroy()

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)



# DIALOG DE CONFIRMACION ACTUALIZADO


class ConfirmDialog(ctk.CTkToplevel):
    # dialogo de confirmacion moderno que sustituye a messagebox.askyesno

    def __init__(self, parent, title, message, confirm_text="Sí, confirmar",
                 cancel_text="Cancelar", danger=True):
        super().__init__(parent)
        self.result = False
        self.title(title)
        self.geometry("420x220")
        self.resizable(False, False)
        self.transient(parent)
        colors = get_dynamic_colors()
        self.configure(fg_color=colors["bg_secondary"])
        self.withdraw()

        def _build():
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

            ctk.CTkButton(
                btn_row,
                text=cancel_text,
                command=self._cancel,
                fg_color="#9E9E9E",
                hover_color="#757575",
                width=160, height=38,
                font=("Arial", 11, "bold"),
                corner_radius=8
            ).pack(side="left", padx=8)

            ctk.CTkButton(
                btn_row,
                text=confirm_text,
                command=self._confirm,
                fg_color=COLOR_ERROR if danger else COLOR_PRIMARY,
                hover_color="#C62828" if danger else "#388E3C",
                width=160, height=38,
                font=("Arial", 11, "bold"),
                corner_radius=8
            ).pack(side="left", padx=8)

            self.update_idletasks()
            self.deiconify()
            self.lift()
            self.focus_force()
            self.grab_set()

        self.after(250, _build)
        self.wait_window()

    def _confirm(self):
        self.result = True
        self.destroy()

    def _cancel(self):
        self.result = False
        self.destroy()



# VISOR DE PDF INLINE


class PDFViewerWindow(ctk.CTkToplevel):
    """Visor de PDF inline con PyMuPDF.
    Renderiza páginas como imágenes directamente desde bytes en memoria —
    el documento descifrado nunca se escribe al disco.
    """

    _ZOOM_LEVELS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
    _ZOOM_DEFAULT = 2  # índice inicial → 1.0x

    def __init__(self, parent, pdf_bytes: bytes, nombre: str):
        import fitz  # PyMuPDF — importado localmente para detectar error temprano
        super().__init__(parent)

        self.title(f"📄 {nombre}")
        self.geometry("940x740")
        self.minsize(640, 500)
        self.transient(parent)

        # documento abierto desde bytes, sin archivo temporal
        self._doc      = fitz.open(stream=pdf_bytes, filetype="pdf")
        self._page_idx = 0
        self._zoom_idx = self._ZOOM_DEFAULT
        self._tk_img   = None  # referencia retenida para evitar GC de Tkinter

        colors = get_dynamic_colors()
        self.configure(fg_color=colors["bg_primary"])

        self._build_ui(nombre, colors)
        self.update_idletasks()
        self._render_page()

        # atajos de teclado
        self.bind("<Left>",  lambda e: self._prev_page())
        self.bind("<Right>", lambda e: self._next_page())
        self.bind("<Prior>", lambda e: self._prev_page())   # Re Pág
        self.bind("<Next>",  lambda e: self._next_page())   # Av Pág
        self.bind("<equal>", lambda e: self._zoom_in())
        self.bind("<plus>",  lambda e: self._zoom_in())
        self.bind("<minus>", lambda e: self._zoom_out())

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.focus_force()

    # ── construcción de UI ────────────────────────────────────────────────

    def _build_ui(self, nombre, colors):
        # barra superior: nombre del archivo y contador de páginas
        top = ctk.CTkFrame(self, fg_color=colors["bg_card"], corner_radius=0, height=50)
        top.pack(fill="x")
        top.pack_propagate(False)

        ctk.CTkLabel(
            top,
            text=f"📄  {nombre}",
            font=("Arial", 13, "bold"),
            text_color=colors["text_primary"]
        ).pack(side="left", padx=18, pady=10)

        self._page_label = ctk.CTkLabel(
            top,
            text=f"Página 1 / {len(self._doc)}",
            font=("Arial", 11),
            text_color=colors["text_secondary"]
        )
        self._page_label.pack(side="right", padx=18)

        # barra de controles: navegación y zoom
        ctrl = ctk.CTkFrame(self, fg_color=colors["bg_secondary"], corner_radius=0, height=48)
        ctrl.pack(fill="x")
        ctrl.pack_propagate(False)

        _btn = dict(width=38, height=34, corner_radius=7, font=("Arial", 14, "bold"),
                    text_color="white")

        ctk.CTkButton(ctrl, text="◀", command=self._prev_page,
                      fg_color=COLOR_SECONDARY, hover_color="#1565c0",
                      **_btn).pack(side="left", padx=(14, 4), pady=7)

        ctk.CTkButton(ctrl, text="▶", command=self._next_page,
                      fg_color=COLOR_SECONDARY, hover_color="#1565c0",
                      **_btn).pack(side="left", padx=(4, 14), pady=7)

        # divisor visual
        ctk.CTkFrame(ctrl, width=2, height=26,
                     fg_color=colors["text_secondary"]).pack(side="left", padx=4)

        ctk.CTkLabel(ctrl, text="Zoom:", font=("Arial", 11),
                     text_color=colors["text_secondary"]).pack(side="left", padx=(8, 4))

        ctk.CTkButton(ctrl, text="−", command=self._zoom_out,
                      fg_color="#7B1FA2", hover_color="#6A1B9A",
                      **_btn).pack(side="left", padx=4, pady=7)

        self._zoom_label = ctk.CTkLabel(
            ctrl, text="100%",
            font=("Arial", 11, "bold"),
            text_color=COLOR_PRIMARY, width=52
        )
        self._zoom_label.pack(side="left", padx=2)

        ctk.CTkButton(ctrl, text="+", command=self._zoom_in,
                      fg_color="#7B1FA2", hover_color="#6A1B9A",
                      **_btn).pack(side="left", padx=4, pady=7)

        # área del canvas con barras de desplazamiento
        canvas_outer = ctk.CTkFrame(self, fg_color=colors["bg_primary"], corner_radius=0)
        canvas_outer.pack(fill="both", expand=True)

        bg_canvas = "#2a2a2a" if ctk.get_appearance_mode() == "Dark" else "#d8d8d8"
        self._canvas = tk.Canvas(
            canvas_outer,
            bg=bg_canvas,
            highlightthickness=0,
            cursor="hand2"
        )

        v_sb = ctk.CTkScrollbar(canvas_outer, command=self._canvas.yview)
        h_sb = ctk.CTkScrollbar(canvas_outer, orientation="horizontal",
                                 command=self._canvas.xview)

        self._canvas.configure(yscrollcommand=v_sb.set, xscrollcommand=h_sb.set)

        v_sb.pack(side="right",  fill="y")
        h_sb.pack(side="bottom", fill="x")
        self._canvas.pack(fill="both", expand=True)

        # scroll con rueda del ratón (Linux y Windows/Mac)
        self._canvas.bind("<MouseWheel>", self._on_scroll)
        self._canvas.bind("<Button-4>",   self._on_scroll)
        self._canvas.bind("<Button-5>",   self._on_scroll)

    # ── renderizado ───────────────────────────────────────────────────────

    def _render_page(self):
        import fitz
        from PIL import Image, ImageTk

        zoom = self._ZOOM_LEVELS[self._zoom_idx]
        page = self._doc[self._page_idx]
        pix  = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)

        img          = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        self._tk_img = ImageTk.PhotoImage(img)

        self._canvas.delete("all")

        # centrar página horizontalmente en el canvas
        cw = max(self._canvas.winfo_width(), pix.width + 40)
        cx = cw // 2
        self._canvas.create_image(cx, 20, anchor="n", image=self._tk_img)
        self._canvas.configure(scrollregion=(0, 0, cw, pix.height + 40))
        self._canvas.yview_moveto(0)

        self._page_label.configure(
            text=f"Página {self._page_idx + 1} / {len(self._doc)}"
        )
        self._zoom_label.configure(text=f"{int(zoom * 100)}%")

    # ── controles ─────────────────────────────────────────────────────────

    def _prev_page(self):
        if self._page_idx > 0:
            self._page_idx -= 1
            self._render_page()

    def _next_page(self):
        if self._page_idx < len(self._doc) - 1:
            self._page_idx += 1
            self._render_page()

    def _zoom_in(self):
        if self._zoom_idx < len(self._ZOOM_LEVELS) - 1:
            self._zoom_idx += 1
            self._render_page()

    def _zoom_out(self):
        if self._zoom_idx > 0:
            self._zoom_idx -= 1
            self._render_page()

    def _on_scroll(self, event):
        # compatibilidad Linux (Button-4/5) y Windows/Mac (delta)
        if event.num == 4 or getattr(event, 'delta', 0) > 0:
            self._canvas.yview_scroll(-1, "units")
        else:
            self._canvas.yview_scroll(1, "units")

    def _on_close(self):
        # liberar el documento de memoria al cerrar
        self._doc.close()
        self.destroy()


# Copyright (c) 2024 DatenJäger. All rights reserved.
