

# audit.py - visor de auditoria y registro de eventos


import os
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from datetime import datetime

from ui_components import Notification, get_dynamic_colors
from icons import get_icon


# colores compartidos
COLOR_SECONDARY = "#2196F3"


class GestorAuditoria:
    # maneja el modal de auditoria y el registro de eventos

    def __init__(self, app):
        # referencia a la app principal
        self.app = app

    def registrar(self, accion: str, pdf_id=None, usuario_id=None):
        # registrar evento de auditoria en la db
        try:
            uid = usuario_id if usuario_id is not None else self.app.usuario_actual
            self.app.cursor.execute(
                "INSERT INTO Auditoria (accion, pdf_id, usuario_id, fecha) VALUES (?, ?, ?, ?)",
                (accion, pdf_id, uid, datetime.now().isoformat())
            )
            self.app.conn.commit()
        except Exception:
            pass

    def mostrar(self):
        # abrir ventana del visor de auditoria
        if not self.app.usuario_actual:
            Notification(self.app.root, "Error", "No hay sesión activa.",
                         notification_type="error")
            return

        win = ctk.CTkToplevel(self.app.root)
        win.title("Log de Auditoría — DatenJäger")
        win.geometry("960x600")
        win.minsize(760, 460)
        win.transient(self.app.root)
        win.withdraw()

        def _close_audit_win():
            try:
                win.grab_release()
            except tk.TclError:
                pass
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", _close_audit_win)
        self.app._show_modal_window(win)
        colors = get_dynamic_colors()

        # header
        header = ctk.CTkFrame(win, fg_color=("#1a237e", "#0d1b3e"),
                               height=52, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        title_lbl = ctk.CTkLabel(
            header, text="  Log de Auditoría",
            image=get_icon("clipboard", 18),
            compound="left",
            font=("Arial", 16, "bold"), text_color="white"
        )
        title_lbl.pack(side="left", padx=16, pady=14)
        subtitle_lbl = ctk.CTkLabel(
            header, text="Historial de acciones del sistema",
            font=("Arial", 10), text_color="#90caf9"
        )
        subtitle_lbl.pack(side="left", padx=4)

        # filtros
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

        lbl_count = ctk.CTkLabel(filter_card, text="",
                                  font=("Arial", 10), text_color=colors["text_secondary"])
        lbl_count.pack(side="right", padx=14)

        # treeview
        tree_wrapper = ctk.CTkFrame(win, fg_color=("#ffffff", "#1e2a4a"),
                                     corner_radius=10)
        tree_wrapper.pack(fill="both", expand=True, padx=14, pady=(4, 6))

        style = ttk.Style()

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

        def _apply_theme():
            local_colors = get_dynamic_colors()
            is_dark = ctk.get_appearance_mode() == "Dark"
            header.configure(fg_color=("#1a237e", "#0d1b3e"))
            title_lbl.configure(text_color="white")
            subtitle_lbl.configure(text_color="#90caf9" if is_dark else "#5c6bc0")
            filter_card.configure(fg_color=("#e8f0fe", "#1e2a4a"))
            tree_wrapper.configure(fg_color=("#ffffff", "#1e2a4a"))
            lbl_count.configure(text_color=local_colors["text_secondary"])

            for entry in (entry_desde, entry_hasta, entry_accion):
                entry.configure(
                    text_color=local_colors["text_primary"],
                    placeholder_text_color=local_colors["text_secondary"],
                    fg_color=local_colors["bg_secondary"],
                    border_color=local_colors["secondary"],
                )

            style.configure("Audit.Treeview",
                            rowheight=26, font=("Arial", 10),
                            background="#1e2a4a" if is_dark else "#ffffff",
                            foreground="#e0e0e0" if is_dark else "#1a237e",
                            fieldbackground="#1e2a4a" if is_dark else "#ffffff")
            style.configure("Audit.Treeview.Heading",
                            font=("Arial", 10, "bold"),
                            background="#1a237e", foreground="white")
            style.map("Audit.Treeview", background=[("selected", "#2196F3")])
            tree.tag_configure("odd",  background="#1e2a4a" if is_dark else "#f5f7ff")
            tree.tag_configure("even", background="#16213e" if is_dark else "#ffffff")

        # cargar datos
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

                with self.app._db_lock:
                    self.app.cursor.execute(query, params)
                    rows = self.app.cursor.fetchall()

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
                Notification(self.app.root, "Error al cargar auditoría",
                             str(e), notification_type="error")

        def _aplicar_filtros():
            _cargar(entry_desde.get(), entry_hasta.get(), entry_accion.get())

        def _limpiar_filtros():
            entry_desde.delete(0, tk.END)
            entry_hasta.delete(0, tk.END)
            entry_accion.delete(0, tk.END)
            _cargar()

        # visor log backend
        def _ver_log_backend():
            import glob
            log_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "datenjager.log"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.log"),
            ]

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
                    with self.app._db_lock:
                        self.app.cursor.execute(
                            "SELECT a.fecha, a.accion, COALESCE(a.pdf_id,'—'), "
                            "COALESCE(u.nombre,'—') FROM Auditoria a "
                            "LEFT JOIN Usuarios u ON a.usuario_id = u.id "
                            "ORDER BY a.fecha DESC LIMIT 500"
                        )
                        for r in self.app.cursor.fetchall():
                            fecha_f = r[0][:19].replace('T', ' ') if r[0] else '—'
                            log_content += f"[{fecha_f}] {r[1]} | PDF={r[2]} | User={r[3]}\n"
                except Exception as ex:
                    log_content += f"Error leyendo BD: {ex}\n"
                found_log = "(generado en memoria)"

            log_win = ctk.CTkToplevel(win)
            log_win.title("Log del Sistema — Backend")
            log_win.geometry("820x540")
            log_win.transient(win)
            log_win.configure(fg_color=("#1b1b2f", "#0d0d1a"))
            log_win.withdraw()

            hdr = ctk.CTkFrame(log_win, fg_color=("#263238", "#1a1a2e"),
                                height=42, corner_radius=0)
            hdr.pack(fill="x")
            hdr.pack_propagate(False)
            ctk.CTkLabel(
                hdr, text="  Log del Sistema",
                image=get_icon("scroll-text", 16),
                compound="left",
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

        ctk.CTkButton(
            filter_card, text="  Filtrar",
            image=get_icon("search", 14),
            compound="left",
            command=_aplicar_filtros,
            fg_color=COLOR_SECONDARY, hover_color="#1565c0",
            font=("Arial", 10, "bold"), corner_radius=7,
            width=86, height=30
        ).pack(side="left", padx=(0, 4), pady=8)

        ctk.CTkButton(
            filter_card, text="Limpiar",
            command=_limpiar_filtros,
            fg_color=("#78909c", "#546e7a"), hover_color="#455a64",
            font=("Arial", 10, "bold"), corner_radius=7,
            width=80, height=30
        ).pack(side="left", pady=8)

        bottom_bar = ctk.CTkFrame(win, fg_color="transparent")
        bottom_bar.pack(fill="x", padx=14, pady=(0, 8))

        ctk.CTkButton(
            bottom_bar, text="  Log del Sistema",
            image=get_icon("scroll-text", 16),
            compound="left",
            command=_ver_log_backend,
            fg_color="#263238", hover_color="#37474f",
            text_color="#4fc3f7", font=("Arial", 10, "bold"),
            corner_radius=8, width=160, height=34
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            bottom_bar, text="  Refrescar",
            image=get_icon("refresh-cw", 16),
            compound="left",
            command=_aplicar_filtros,
            fg_color=("#78909c", "#546e7a"), hover_color="#455a64",
            font=("Arial", 10, "bold"), corner_radius=8,
            width=110, height=34
        ).pack(side="right", padx=4)

        for e in (entry_desde, entry_hasta, entry_accion):
            e.bind("<Return>", lambda _ev: _aplicar_filtros())

        def _on_theme_changed(_event=None):
            if win.winfo_exists():
                _apply_theme()

        theme_bind_id = self.app.root.bind("<<ThemeChanged>>", _on_theme_changed, add="+")

        original_close = _close_audit_win

        def _close_with_unbind():
            try:
                self.app.root.unbind("<<ThemeChanged>>", theme_bind_id)
            except Exception:
                pass
            original_close()

        win.protocol("WM_DELETE_WINDOW", _close_with_unbind)
        _apply_theme()
        _cargar()

# Copyright (c) 2024 DatenJäger. All rights reserved.