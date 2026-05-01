# Copyright (c) 2024 DatenJäger. All rights reserved.
# pdf_manager.py - operaciones crud de pdfs


import os
import threading
import customtkinter as ctk
from tkinter import filedialog
from datetime import datetime

from ui_components import Notification, ConfirmDialog, PDFViewerWindow, get_dynamic_colors
from encryption import EncryptionManager
from icons import get_icon


# colores compartidos
COLOR_PRIMARY   = "#4CAF50"
COLOR_SECONDARY = "#2196F3"
COLOR_WARNING   = "#FF9800"
COLOR_ERROR     = "#F44336"


class GestorPDF:
    # maneja las operaciones crud de pdfs

    def __init__(self, app):
        # referencia a la app principal
        self.app = app
        # estado temporal del formulario agregar
        self.selected_file = None
        self.label_file = None
        self.entry_descripcion = None
        self.entry_cedula = None
        self.entry_nombres = None
        self.entry_empresa = None

    def _theme_entry(self, entry, colors):
        if entry and entry.winfo_exists():
            entry.configure(
                text_color=colors["text_primary"],
                placeholder_text_color=colors["text_secondary"],
                fg_color=colors["bg_secondary"],
                border_color=colors["secondary"]
            )

    # ---- helpers internos (callbacks de threads) ----

    def _save_to_db(self, datos_enc, tamano, nombre, descripcion,
                    cedula, nombres, empresa, usuario_actual, window):
        # guarda el blob pdf cifrado en la db
        try:
            self.app.cursor.execute("SELECT id FROM Personas WHERE cedula = ?", (cedula,))
            result = self.app.cursor.fetchone()
            if result:
                persona_id = result[0]
                self.app.cursor.execute(
                    "UPDATE Personas SET nombres = ?, empresa = ? WHERE id = ?",
                    (nombres, empresa, persona_id)
                )
            else:
                self.app.cursor.execute(
                    "INSERT INTO Personas (cedula, nombres, empresa) VALUES (?, ?, ?)",
                    (cedula, nombres, empresa)
                )
                persona_id = self.app.cursor.lastrowid

            self.app.cursor.execute(
                "INSERT INTO PDFs (nombre, descripcion, datos, datos_encriptados, "
                "tamano, fecha_subida, usuario_id, persona_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (nombre, descripcion, datos_enc, 1, tamano,
                 datetime.now().isoformat(), usuario_actual, persona_id)
            )
            pdf_id = self.app.cursor.lastrowid

            self.app.cursor.execute(
                "INSERT INTO Auditoria (accion, pdf_id, usuario_id, fecha) VALUES (?, ?, ?, ?)",
                ("Agregar PDF (Encriptado AES-256-GCM)", pdf_id, usuario_actual,
                 datetime.now().isoformat())
            )
            self.app.conn.commit()
            self._on_added(nombre, window)
        except Exception as e:
            self.app.conn.rollback()
            self._on_add_error(e)
        finally:
            self.app.progress_bar.stop()

    def _on_added(self, nombre, window):
        # callback exito al agregar pdf
        colors = get_dynamic_colors()
        self.app.status.configure(
            text=f"PDF {nombre} agregado y encriptado",
            text_color=colors["text_primary"]
        )
        Notification(self.app.root, "Éxito",
                     f"PDF {nombre} agregado\nEncriptado con AES-256-GCM",
                     notification_type="success")
        window.destroy()
        self.app.cargar_dashboard()
        self.ver_todos()

    def _on_add_error(self, error):
        # callback error al agregar pdf
        Notification(self.app.root, "Error", str(error), notification_type="error")
        colors = get_dynamic_colors()
        self.app.status.configure(text="Error al agregar PDF",
                                  text_color=colors["text_primary"])

    def _abrir_visor(self, pdf_bytes: bytes, nombre: str, window=None):
        # abre el visor pdf con los bytes descifrados
        if window:
            window.destroy()
        colors = get_dynamic_colors()
        self.app.status.configure(
            text=f"PDF cargado: {nombre}",
            text_color=colors["text_primary"]
        )
        PDFViewerWindow(self.app.root, pdf_bytes, nombre)

    # ---- operaciones publicas ----

    def mostrar_agregar(self):
        # ventana agregar pdf
        if not self.app.usuario_actual:
            Notification(
                self.app.root, "Error",
                "No hay usuario autenticado",
                notification_type="error"
            )
            return

        colors = get_dynamic_colors()
        add_window = ctk.CTkToplevel(self.app.root)
        add_window.title("Agregar PDF")
        add_window.geometry("500x640")
        add_window.resizable(False, False)
        add_window.transient(self.app.root)
        add_window.configure(fg_color=colors["bg_secondary"])
        add_window.withdraw()

        ctk.CTkLabel(
            add_window,
            text="Agregar Nuevo PDF",
            font=("Arial", 20, "bold"),
            text_color=colors["text_primary"]
        ).pack(pady=(20, 4))

        ctk.CTkLabel(
            add_window,
            text="El archivo se encriptará con AES-256-GCM antes de guardarse",
            font=("Arial", 10),
            text_color=colors["secondary"]
        ).pack(pady=(0, 12))

        self.selected_file = None

        btn_buscar = ctk.CTkButton(
            add_window,
            text="  Seleccionar Archivo PDF",
            image=get_icon("folder", 18),
            compound="left",
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
            text="Ningún archivo seleccionado",
            text_color=colors["text_secondary"],
            font=("Arial", 10)
        )
        self.label_file.pack(pady=4)

        sep = ctk.CTkFrame(add_window, height=1, fg_color=("#c8d8ff", "#2a3f72"))
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
        for entry in (self.entry_descripcion, self.entry_cedula, self.entry_nombres, self.entry_empresa):
            self._theme_entry(entry, colors)

        ctk.CTkButton(
            add_window,
            text="  Agregar y Encriptar (AES-256-GCM)",
            image=get_icon("check-circle", 18),
            compound="left",
            command=lambda: self.procesar_agregar(add_window),
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
            fg_color=("#78909c", "#546e7a"), hover_color="#455a64",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=180, height=34
        ).pack(pady=(0, 16))

        self.app._show_modal_window(add_window, delay_ms=250)

    def seleccionar_archivo(self):
        # seleccionar archivo pdf
        self.selected_file = filedialog.askopenfilename(
            filetypes=[("PDF files", "*.pdf")]
        )
        if self.selected_file:
            self.label_file.configure(text=f"{os.path.basename(self.selected_file)}")

    def procesar_agregar(self, window):
        # encriptar en thread y guardar
        if not self.selected_file:
            Notification(self.app.root, "Error", "Selecciona un archivo PDF",
                         notification_type="error")
            return

        descripcion = self.entry_descripcion.get().strip()
        cedula      = self.entry_cedula.get().strip()
        nombres     = self.entry_nombres.get().strip()
        empresa     = self.entry_empresa.get().strip()

        if not cedula or not nombres:
            Notification(self.app.root, "Error", "Cédula y nombres son requeridos",
                         notification_type="error")
            return

        self.app.progress_bar.start("Encriptando y agregando PDF...")

        selected_file  = self.selected_file
        usuario_nombre = self.app.usuario_nombre
        usuario_actual = self.app.usuario_actual

        def encrypt_task():
            try:
                with open(selected_file, 'rb') as f:
                    datos_originales = f.read()
                datos_enc = EncryptionManager.encrypt_data(datos_originales, usuario_nombre)
                tamano    = len(datos_originales)
                nombre    = os.path.basename(selected_file)
                # guardar en main thread
                self.app.root.after(0, lambda: self._save_to_db(
                    datos_enc, tamano, nombre, descripcion,
                    cedula, nombres, empresa, usuario_actual, window
                ))
            except Exception as e:
                self.app.root.after(0, lambda err=e: self._on_add_error(err))
                self.app.root.after(0, self.app.progress_bar.stop)

        threading.Thread(target=encrypt_task, daemon=True).start()

    def ver_todos(self):
        # listar todos los pdfs del usuario
        if not self.app.usuario_actual:
            return

        self.app.progress_bar.start("Cargando PDFs...")

        try:
            self.app.cursor.execute("""
                SELECT p.id, p.nombre, p.descripcion, p.tamano,
                       p.fecha_subida, pe.cedula, pe.nombres, pe.empresa
                FROM PDFs p
                LEFT JOIN Personas pe ON p.persona_id = pe.id
                WHERE p.usuario_id = ?
                ORDER BY p.fecha_subida DESC
            """, (self.app.usuario_actual,))

            rows = self.app.cursor.fetchall()
            self.app._populate_treeview(rows)

            colors = get_dynamic_colors()
            self.app.status.configure(
                text=f"Se muestran {len(rows)} PDFs (Encriptados)",
                text_color=colors["text_primary"]
            )
        except Exception as e:
            Notification(self.app.root, "Error", str(e), notification_type="error")
        finally:
            self.app.progress_bar.stop()

    def buscar(self):
        # buscar pdfs por termino
        term = self.app.entry_busqueda.get().strip()

        if not term:
            self.ver_todos()
            return

        self.app.progress_bar.start(f"Buscando '{term}'...")

        try:
            self.app.cursor.execute("""
                SELECT p.id, p.nombre, p.descripcion, p.tamano,
                       p.fecha_subida, pe.cedula, pe.nombres, pe.empresa
                FROM PDFs p
                LEFT JOIN Personas pe ON p.persona_id = pe.id
                WHERE p.usuario_id = ? AND (
                    p.nombre LIKE ? OR p.descripcion LIKE ?
                    OR pe.cedula LIKE ? OR pe.nombres LIKE ?
                    OR pe.empresa LIKE ?
                )
            """, (self.app.usuario_actual,
                  f"%{term}%", f"%{term}%", f"%{term}%", f"%{term}%", f"%{term}%"))

            rows = self.app.cursor.fetchall()
            self.app._populate_treeview(rows)

            colors = get_dynamic_colors()
            self.app.status.configure(
                text=f"Se muestran {len(rows)} resultados",
                text_color=colors["text_primary"]
            )
            Notification(
                self.app.root,
                "Búsqueda completada",
                f"Se encontraron {len(rows)} PDF(s) encriptados",
                notification_type="success",
                duration=2000
            )
        except Exception as e:
            Notification(self.app.root, "Error", str(e), notification_type="error")
        finally:
            self.app.progress_bar.stop()

    def mostrar_detalles(self):
        # ventana detalles del pdf
        selected = self.app.tree.selection()

        if not selected:
            Notification(
                self.app.root, "Advertencia",
                "Selecciona un PDF de la lista",
                notification_type="warning"
            )
            return

        values = self.app.tree.item(selected[0])['values']
        pdf_id, pdf_nombre, descripcion, tamano, fecha, cedula, nombres, empresa = values

        colors = get_dynamic_colors()
        details_window = ctk.CTkToplevel(self.app.root)
        details_window.title("Detalles del PDF")
        details_window.geometry("460x680")
        details_window.resizable(False, False)
        details_window.transient(self.app.root)
        details_window.configure(fg_color=colors["bg_secondary"])
        details_window.withdraw()

        ctk.CTkLabel(
            details_window, text="Detalles del Documento",
            font=("Arial", 18, "bold"),
            text_color=colors["text_primary"]
        ).pack(pady=(20, 4))

        sep = ctk.CTkFrame(details_window, height=1, fg_color=("#c8d8ff", "#2a3f72"))
        sep.pack(fill="x", padx=30)

        info_frame = ctk.CTkFrame(
            details_window, fg_color=("#f0f4ff", "#1a2540"),
            corner_radius=10, border_width=1,
            border_color=("#d0d8e8", "#2a3a5e")
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

        info_row("ID:", pdf_id)
        info_row("Nombre:", pdf_nombre)
        info_row("Descripción:", descripcion)
        info_row("Tamaño:", tamano)
        info_row("Fecha:", fecha)
        info_row("Cédula:", cedula)
        info_row("Nombres:", nombres)
        info_row("Empresa:", empresa)
        info_row("Encriptación:", "AES-256-GCM")

        btn_row = ctk.CTkFrame(details_window, fg_color="transparent")
        btn_row.pack(pady=14)

        ctk.CTkButton(
            btn_row, text="  Abrir",
            image=get_icon("folder-open", 16),
            compound="left",
            command=lambda: self.abrir_por_id(pdf_id, details_window),
            fg_color=COLOR_SECONDARY, hover_color="#1565c0",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=150, height=40
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            btn_row, text="  Exportar",
            command=lambda: (details_window.destroy(), self.exportar()),
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

        self.app._show_modal_window(details_window, delay_ms=250)

    def abrir_doble_click(self):
        # abrir pdf al hacer doble click en treeview
        selected = self.app.tree.selection()

        if not selected:
            return

        values = self.app.tree.item(selected[0])['values']
        pdf_id = values[0]
        self.abrir_por_id(pdf_id)

    def abrir_por_id(self, pdf_id, window=None):
        # abrir pdf por id, decrypt en thread
        self.app.progress_bar.start("Desencriptando PDF...")

        try:
            self.app.cursor.execute(
                "SELECT datos, nombre, datos_encriptados FROM PDFs WHERE id = ? AND usuario_id = ?",
                (pdf_id, self.app.usuario_actual)
            )
            result = self.app.cursor.fetchone()
        except Exception as e:
            self.app.progress_bar.stop()
            Notification(self.app.root, "Error", str(e), notification_type="error")
            return

        if not result:
            self.app.progress_bar.stop()
            Notification(self.app.root, "Error", "PDF no encontrado", notification_type="error")
            return

        datos_enc, nombre, encriptado = result
        self.app._audit("Abrir / Descifrar PDF", pdf_id=pdf_id)
        usuario_nombre = self.app.usuario_nombre

        def decrypt_task():
            try:
                datos = (EncryptionManager.decrypt_data(bytes(datos_enc), usuario_nombre)
                         if encriptado else bytes(datos_enc))
                # mostrar sin guardar
                self.app.root.after(0, lambda d=datos: self._abrir_visor(d, nombre, window))
            except Exception as e:
                self.app.root.after(
                    0,
                    lambda err=e: Notification(
                        self.app.root, "Error",
                        f"No se pudo abrir el PDF: {err}",
                        notification_type="error"
                    )
                )
            finally:
                self.app.root.after(0, self.app.progress_bar.stop)

        threading.Thread(target=decrypt_task, daemon=True).start()

    def eliminar(self):
        # eliminar pdf seleccionado
        selected = self.app.tree.selection()

        if not selected:
            Notification(
                self.app.root, "Advertencia",
                "Selecciona un PDF de la lista",
                notification_type="warning"
            )
            return

        pdf_id = self.app.tree.item(selected[0])['values'][0]
        pdf_nombre = self.app.tree.item(selected[0])['values'][1]

        dlg = ConfirmDialog(
            self.app.root,
            "Eliminar PDF",
            f"¿Eliminar permanentemente\n\"{pdf_nombre}\"?\n\nEsta acción no se puede deshacer.",
            confirm_text="Sí, eliminar",
            cancel_text="Cancelar",
            danger=True
        )
        if not dlg.result:
            return

        self.app.progress_bar.start("Eliminando PDF…")

        try:
            self.app.cursor.execute(
                "DELETE FROM PDFs WHERE id = ? AND usuario_id = ?",
                (pdf_id, self.app.usuario_actual)
            )

            if self.app.cursor.rowcount == 0:
                Notification(self.app.root, "Error", "PDF no encontrado",
                             notification_type="error")
                return

            self.app.cursor.execute(
                "INSERT INTO Auditoria (accion, pdf_id, usuario_id, fecha) VALUES (?, ?, ?, ?)",
                ("Eliminar PDF", pdf_id, self.app.usuario_actual, datetime.now().isoformat())
            )

            self.app.conn.commit()
            self.app._reset_preview_panel()
            Notification(self.app.root, "Eliminado",
                         f"'{pdf_nombre}' eliminado correctamente",
                         notification_type="success")
            self.app.cargar_dashboard()
            self.ver_todos()
        except Exception as e:
            self.app.conn.rollback()
            Notification(self.app.root, "Error", str(e), notification_type="error")
        finally:
            self.app.progress_bar.stop()

    def editar(self):
        # editar metadatos del pdf seleccionado
        selected = self.app.tree.selection()

        if not selected:
            Notification(
                self.app.root, "Advertencia",
                "Selecciona un PDF de la lista",
                notification_type="warning"
            )
            return

        values = self.app.tree.item(selected[0])['values']
        pdf_id, pdf_nombre, descripcion, tamano, fecha, cedula, nombres, empresa = values

        colors = get_dynamic_colors()
        edit_win = ctk.CTkToplevel(self.app.root)
        edit_win.title("Editar Metadatos del PDF")
        edit_win.geometry("480x520")
        edit_win.resizable(False, False)
        edit_win.transient(self.app.root)
        edit_win.configure(fg_color=colors["bg_secondary"])
        edit_win.withdraw()

        ctk.CTkLabel(
            edit_win, text="Editar Metadatos",
            font=("Arial", 18, "bold"),
            text_color=colors["text_primary"]
        ).pack(pady=(20, 4))

        ctk.CTkLabel(
            edit_win, text=f"Editando: {pdf_nombre}",
            font=("Arial", 10), text_color=colors["secondary"]
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
        for entry in (e_nombre, e_desc, e_cedula, e_nombres, e_empresa):
            self._theme_entry(entry, colors)

        def guardar():
            nuevo_nombre   = e_nombre.get().strip()
            nueva_desc     = e_desc.get().strip()
            nueva_cedula   = e_cedula.get().strip()
            nuevos_nombres = e_nombres.get().strip()
            nueva_empresa  = e_empresa.get().strip()

            if not nuevo_nombre:
                Notification(edit_win, "Error", "El nombre no puede estar vacío",
                             notification_type="error")
                return

            try:
                self.app.cursor.execute(
                    "UPDATE PDFs SET nombre = ?, descripcion = ? WHERE id = ? AND usuario_id = ?",
                    (nuevo_nombre, nueva_desc, pdf_id, self.app.usuario_actual)
                )
                if nueva_cedula:
                    self.app.cursor.execute(
                        """UPDATE Personas SET nombres = ?, empresa = ?
                           WHERE id = (SELECT persona_id FROM PDFs WHERE id = ?)""",
                        (nuevos_nombres, nueva_empresa, pdf_id)
                    )
                self.app.cursor.execute(
                    "INSERT INTO Auditoria (accion, pdf_id, usuario_id, fecha) VALUES (?,?,?,?)",
                    ("Editar metadatos PDF", pdf_id, self.app.usuario_actual, datetime.now().isoformat())
                )
                self.app.conn.commit()
                Notification(self.app.root, "Guardado",
                             "Metadatos actualizados correctamente",
                             notification_type="success")
                edit_win.destroy()
                self.ver_todos()
                self.app._reset_preview_panel()
            except Exception as exc:
                self.app.conn.rollback()
                Notification(edit_win, "Error", str(exc), notification_type="error")

        ctk.CTkButton(
            edit_win, text="  Guardar Cambios",
            image=get_icon("save", 18),
            compound="left",
            command=guardar,
            fg_color=COLOR_PRIMARY, hover_color="#388E3C",
            text_color="white", font=("Arial", 12, "bold"),
            corner_radius=8, width=260, height=42
        ).pack(pady=(8, 4))

        ctk.CTkButton(
            edit_win, text="Cancelar",
            command=edit_win.destroy,
            fg_color=("#78909c", "#546e7a"), hover_color="#455a64",
            text_color="white", font=("Arial", 11, "bold"),
            corner_radius=8, width=260, height=36
        ).pack(pady=(0, 20))

        self.app._show_modal_window(edit_win, delay_ms=250)

    def exportar(self):
        # exportar pdf desencriptado a disco
        selected = self.app.tree.selection()

        if not selected:
            Notification(
                self.app.root, "Advertencia",
                "Selecciona un PDF de la lista",
                notification_type="warning"
            )
            return

        values = self.app.tree.item(selected[0])['values']
        pdf_id = values[0]
        pdf_nombre = values[1]

        dest = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=pdf_nombre,
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if not dest:
            return

        self.app.progress_bar.start("Desencriptando y exportando…")

        try:
            self.app.cursor.execute(
                "SELECT datos, datos_encriptados FROM PDFs WHERE id = ? AND usuario_id = ?",
                (pdf_id, self.app.usuario_actual)
            )
            result = self.app.cursor.fetchone()
        except Exception as e:
            self.app.progress_bar.stop()
            Notification(self.app.root, "Error", str(e), notification_type="error")
            return

        if not result:
            self.app.progress_bar.stop()
            Notification(self.app.root, "Error", "PDF no encontrado", notification_type="error")
            return

        datos_enc, encriptado = result
        usuario_nombre = self.app.usuario_nombre

        def export_task():
            try:
                datos = (EncryptionManager.decrypt_data(bytes(datos_enc), usuario_nombre)
                         if encriptado else bytes(datos_enc))
                with open(dest, 'wb') as f:
                    f.write(datos)
                self.app.root.after(0, lambda: Notification(
                    self.app.root, "Exportado",
                    f"PDF exportado a:\n{dest}",
                    notification_type="success", duration=4000
                ))
                self.app.cursor.execute(
                    "INSERT INTO Auditoria (accion, pdf_id, usuario_id, fecha) VALUES (?,?,?,?)",
                    ("Exportar PDF", pdf_id, self.app.usuario_actual, datetime.now().isoformat())
                )
                self.app.conn.commit()
            except Exception as e:
                self.app.root.after(0, lambda err=e: Notification(
                    self.app.root, "Error",
                    f"Error al exportar: {err}",
                    notification_type="error"
                ))
            finally:
                self.app.root.after(0, self.app.progress_bar.stop)

        threading.Thread(target=export_task, daemon=True).start()
