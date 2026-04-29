# Copyright (c) 2024 DatenJäger. All rights reserved.
# personas.py - gestion de personas (crud)


import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import hashlib
from datetime import datetime

from ui_components import Notification, ConfirmDialog, get_dynamic_colors
from icons import get_icon


# colores compartidos
COLOR_PRIMARY   = "#4CAF50"
COLOR_SECONDARY = "#2196F3"
COLOR_ERROR     = "#F44336"


class GestorPersonas:
    # maneja el modal de gestion de personas

    def __init__(self, app):
        # referencia a la app principal
        self.app = app

    def mostrar(self):
        # abrir ventana de gestion de personas
        if not self.app.usuario_actual:
            Notification(self.app.root, "Error", "No hay sesión activa.",
                         notification_type="error")
            return

        win = ctk.CTkToplevel(self.app.root)
        win.title("Gestión de Personas — DatenJäger")
        win.geometry("960x620")
        win.minsize(760, 480)
        win.transient(self.app.root)
        win.withdraw()

        _auto_refresh_id = [None]
        _last_hash = [None]

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
        self.app._show_modal_window(win)
        colors = get_dynamic_colors()

        # header
        header = ctk.CTkFrame(win, fg_color=("#6A1B9A", "#311B92"),
                               height=52, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        title_lbl = ctk.CTkLabel(
            header, text="  Gestión de Personas",
            image=get_icon("users", 18),
            compound="left",
            font=("Arial", 16, "bold"), text_color="white"
        )
        title_lbl.pack(side="left", padx=16, pady=14)
        subtitle_lbl = ctk.CTkLabel(
            header, text="Administración de titulares de documentos",
            font=("Arial", 10), text_color="#ce93d8"
        )
        subtitle_lbl.pack(side="left", padx=4)

        # barra busqueda
        action_bar = ctk.CTkFrame(win, fg_color=("#f3e5f5", "#1e1533"),
                                   corner_radius=10)
        action_bar.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(action_bar, text="",
                     image=get_icon("search", 14),
                     font=("Arial", 14)).pack(side="left", padx=(14, 4), pady=8)
        entry_buscar = ctk.CTkEntry(action_bar,
                                     placeholder_text="Buscar por cédula, nombre o empresa…",
                                     width=300, height=30, corner_radius=6)
        entry_buscar.pack(side="left", padx=(0, 10), pady=8)

        lbl_count = ctk.CTkLabel(action_bar, text="",
                                  font=("Arial", 10),
                                  text_color=colors["text_secondary"])
        lbl_count.pack(side="right", padx=14)

        # treeview
        tree_wrapper = ctk.CTkFrame(win, fg_color=("#ffffff", "#1e2a4a"),
                                     corner_radius=10)
        tree_wrapper.pack(fill="both", expand=True, padx=14, pady=(4, 6))

        style = ttk.Style()

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

        def _apply_theme():
            local_colors = get_dynamic_colors()
            is_dark = ctk.get_appearance_mode() == "Dark"
            header.configure(fg_color=("#6A1B9A", "#311B92"))
            title_lbl.configure(text_color="white")
            subtitle_lbl.configure(text_color="#ce93d8" if is_dark else "#8e24aa")
            action_bar.configure(fg_color=("#f3e5f5", "#1e1533"))
            tree_wrapper.configure(fg_color=("#ffffff", "#1e2a4a"))
            lbl_count.configure(text_color=local_colors["text_secondary"])
            lbl_refresh.configure(text_color=local_colors["text_secondary"])
            entry_buscar.configure(
                text_color=local_colors["text_primary"],
                placeholder_text_color=local_colors["text_secondary"],
                fg_color=local_colors["bg_secondary"],
                border_color=local_colors["secondary"],
            )

            style.configure("Persona.Treeview",
                            rowheight=28, font=("Arial", 10),
                            background="#1e2a4a" if is_dark else "#ffffff",
                            foreground="#e0e0e0" if is_dark else "#1a237e",
                            fieldbackground="#1e2a4a" if is_dark else "#ffffff")
            style.configure("Persona.Treeview.Heading",
                            font=("Arial", 10, "bold"),
                            background="#6A1B9A", foreground="white")
            style.map("Persona.Treeview", background=[("selected", "#9C27B0")])
            tree.tag_configure("odd",  background="#1e1533" if is_dark else "#f3e5f5")
            tree.tag_configure("even", background="#16213e" if is_dark else "#ffffff")

        # carga datos
        def _fetch_rows(filtro=""):
            # query
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
            with self.app._db_lock:
                self.app.cursor.execute(query, params)
                return self.app.cursor.fetchall()

        def _rows_hash(rows):
            # hash rapido para detectar cambios
            return hashlib.md5(str(rows).encode()).hexdigest()

        def _cargar(filtro="", force=False):
            try:
                rows = _fetch_rows(filtro)
                new_hash = _rows_hash(rows)
                if not force and new_hash == _last_hash[0]:
                    return
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
                Notification(self.app.root, "Error al cargar personas",
                             str(e), notification_type="error")

        def _filtrar(*_args):
            _cargar(entry_buscar.get(), force=True)

        entry_buscar.bind("<KeyRelease>", _filtrar)

        # auto refresh
        def _auto_refresh():
            try:
                if win.winfo_exists():
                    _cargar(entry_buscar.get())
                    _auto_refresh_id[0] = win.after(10000, _auto_refresh)
            except tk.TclError:
                pass

        _auto_refresh_id[0] = win.after(10000, _auto_refresh)

        # formulario agregar/editar
        def _abrir_formulario(modo="agregar", datos=None):
            form = ctk.CTkToplevel(win)
            titulo = "Agregar Persona" if modo == "agregar" else "Editar Persona"
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
                    Notification(form, "Error",
                                 "Cédula y nombres son obligatorios.",
                                 notification_type="error")
                    return

                try:
                    with self.app._db_lock:
                        if modo == "agregar":
                            self.app.cursor.execute(
                                "SELECT id FROM Personas WHERE cedula = ?",
                                (cedula,)
                            )
                            if self.app.cursor.fetchone():
                                Notification(form, "Duplicado",
                                             f"Ya existe una persona con cédula {cedula}.",
                                             notification_type="warning")
                                return
                            self.app.cursor.execute(
                                "INSERT INTO Personas (cedula, nombres, empresa) "
                                "VALUES (?, ?, ?)",
                                (cedula, nombres, empresa)
                            )
                            self.app._audit("Agregar persona (Panel Personas)")
                            msg = f"Persona '{nombres}' registrada."
                        else:
                            self.app.cursor.execute(
                                "UPDATE Personas SET nombres = ?, empresa = ? "
                                "WHERE id = ?",
                                (nombres, empresa, datos[0])
                            )
                            self.app._audit("Editar persona (Panel Personas)")
                            msg = f"Persona '{nombres}' actualizada."
                        self.app.conn.commit()

                    Notification(self.app.root, "Guardado", msg,
                                 notification_type="success", duration=2500)
                    form.destroy()
                    _cargar(entry_buscar.get())
                except Exception as exc:
                    self.app.conn.rollback()
                    Notification(form, "Error", str(exc),
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
                text="  Guardar" if modo == "editar" else "  Agregar",
                command=_guardar,
                fg_color="#6A1B9A" if modo == "agregar" else COLOR_PRIMARY,
                hover_color="#4A148C" if modo == "agregar" else "#388E3C",
                text_color="white", font=("Arial", 11, "bold"),
                corner_radius=8, width=150, height=38
            ).pack(side="left", padx=6)

            form.after(200, lambda: (
                form.update_idletasks(),
                form.deiconify(),
                form.lift(),
                form.focus_force(),
                form.grab_set()
            ))
            form.wait_window()

        # acciones
        def _agregar():
            _abrir_formulario("agregar")

        def _editar():
            sel = tree.selection()
            if not sel:
                Notification(win, "Selecciona una persona",
                             "Haz clic en una persona de la lista para editarla.",
                             notification_type="warning")
                return
            vals = tree.item(sel[0])["values"]
            _abrir_formulario("editar", datos=(vals[0], vals[1], vals[2], vals[3]))

        def _eliminar():
            sel = tree.selection()
            if not sel:
                Notification(win, "Selecciona una persona",
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
                win, "Eliminar Persona", msg,
                confirm_text="Eliminar", danger=True
            )
            if not dlg.result:
                return
            try:
                with self.app._db_lock:
                    self.app.cursor.execute(
                        "DELETE FROM Personas WHERE id = ?", (pid,)
                    )
                    self.app._audit("Eliminar persona (Panel Personas)")
                    self.app.conn.commit()
                Notification(self.app.root, "Eliminada",
                             f"Persona '{nombres}' eliminada correctamente.",
                             notification_type="success", duration=2500)
                _cargar(entry_buscar.get())
            except Exception as exc:
                self.app.conn.rollback()
                Notification(win, "Error", str(exc),
                             notification_type="error")

        # botones
        bottom_bar = ctk.CTkFrame(win, fg_color="transparent")
        bottom_bar.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkButton(
            bottom_bar, text="  Agregar Persona",
            image=get_icon("plus", 16),
            compound="left",
            command=_agregar,
            fg_color="#6A1B9A", hover_color="#4A148C",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=160, height=38
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            bottom_bar, text="  Editar",
            command=_editar,
            fg_color=COLOR_SECONDARY, hover_color="#1565c0",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=120, height=38
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            bottom_bar, text="  Eliminar",
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
            lbl_refresh.configure(text=f"Última: {datetime.now().strftime('%H:%M:%S')}")

        ctk.CTkButton(
            bottom_bar, text="  Refrescar",
            image=get_icon("refresh-cw", 16),
            compound="left",
            command=_manual_refresh,
            fg_color=("#78909c", "#546e7a"), hover_color="#455a64",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=120, height=38
        ).pack(side="right", padx=6)

        tree.bind("<Double-1>", lambda _e: _editar())

        def _on_theme_changed(_event=None):
            if win.winfo_exists():
                _apply_theme()

        theme_bind_id = self.app.root.bind("<<ThemeChanged>>", _on_theme_changed, add="+")

        original_close = _close_win

        def _close_with_unbind():
            try:
                self.app.root.unbind("<<ThemeChanged>>", theme_bind_id)
            except Exception:
                pass
            original_close()

        win.protocol("WM_DELETE_WINDOW", _close_with_unbind)
        _apply_theme()
        _cargar(force=True)
