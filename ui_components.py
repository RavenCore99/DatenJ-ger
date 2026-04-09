


# Modulo de Componentes UI
# Contiene widgets reutilizables para la interfaz
# Colores adaptados dinamicamente a modo oscuro/claro


import customtkinter as ctk
import tkinter as tk
import os
import math


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
# CLASE DASHBOARD
#                    #

class DashboardWidget:
    # widget de dashboard con estadisticas

    def __init__(self, parent, cursor, usuario_id):
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.cursor = cursor
        self.usuario_id = usuario_id
        self.construir_dashboard()

    def construir_dashboard(self):
        # construye el dashboard
        from database import format_size
        
        colors = get_dynamic_colors()
        
        title = ctk.CTkLabel(
            self.frame,
            text="📊 ESTADÍSTICAS DEL REPOSITORIO",
            font=("Arial", 13, "bold"),
            text_color=colors["text_secondary"]
        )
        title.pack(pady=(8, 4))

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
            ("📄", f"{total_pdfs}", "PDFs Totales",  COLOR_SECONDARY),
            ("💾", format_size(total_size), "Espacio Usado", "#7B1FA2"),
            ("👥", f"{total_personas}", "Personas",    "#00897B"),
            ("🔒", "AES-256-GCM", "Encriptación",        COLOR_PRIMARY),
        ]

        for icono, valor, label, color in tarjetas:
            self.crear_tarjeta(stats_frame, icono, valor, label, color)

    def crear_tarjeta(self, parent, icono, valor, label, color):
        # crea una tarjeta de estadística
        card = ctk.CTkFrame(parent, fg_color=color, corner_radius=12)
        card.pack(side="left", padx=6, pady=6, expand=True, fill="both")

        ctk.CTkLabel(
            card,
            text=icono,
            font=("Arial", 22),
            text_color="white"
        ).pack(pady=(8, 2))

        ctk.CTkLabel(
            card,
            text=valor,
            font=("Arial", 16, "bold"),
            text_color="white"
        ).pack(pady=2)

        ctk.CTkLabel(
            card,
            text=label,
            font=("Arial", 9),
            text_color="#dddddd"
        ).pack(pady=(2, 8))

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
