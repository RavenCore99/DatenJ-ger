# Copyright (c) 2024 DatenJäger. All rights reserved.
# pdf_manager.py - panel documental (solo interfaz)

"""Panel de gestión documental.

Este módulo conserva **únicamente** la construcción de la interfaz
(ventanas, widgets, notificaciones). Todas las operaciones de negocio —
listar, crear, abrir, editar, eliminar y exportar PDFs — se delegan en
``backend.services.documentos``, que no depende de Tkinter.

Los errores del servicio se capturan aquí y se traducen a notificaciones.
"""


import os
import threading
import customtkinter as ctk
from tkinter import filedialog

from ui_components import Notification, ConfirmDialog, PDFViewerWindow, get_dynamic_colors
from icons import get_icon
from backend.errors import BackendError
from backend.services import documentos


# colores compartidos
COLOR_PRIMARY   = "#4CAF50"
COLOR_SECONDARY = "#2196F3"
COLOR_WARNING   = "#FF9800"
COLOR_ERROR     = "#F44336"


def _bind_mousewheel(scrollable_frame):
    # habilitar scroll con rueda/touchpad en Linux (Button-4/5)
    def _on_mousewheel(event):
        try:
            canvas = scrollable_frame._parent_canvas
            if event.num == 4:
                canvas.yview_scroll(-3, "units")
            elif event.num == 5:
                canvas.yview_scroll(3, "units")
        except Exception:
            pass

    def _bind_all(widget):
        widget.bind("<Button-4>", _on_mousewheel, add="+")
        widget.bind("<Button-5>", _on_mousewheel, add="+")
        for child in widget.winfo_children():
            _bind_all(child)

    # bind despues de que se renderice
    scrollable_frame.after(100, lambda: _bind_all(scrollable_frame))


def _fila_tree(documento: dict) -> tuple:
    """Convierte un documento del servicio en la fila del Treeview.

    Orden histórico de columnas del panel: id, nombre, descripción,
    tamaño, fecha, cédula, nombres, empresa.
    """
    return (
        documento["id"],
        documento["nombre"],
        documento["descripcion"],
        documento["tamano"],
        documento["fecha_subida"],
        documento["cedula"],
        documento["nombres"],
        documento["empresa"],
    )


class GestorPDF:
    # maneja las operaciones crud de pdfs (interfaz)

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

    # ---- acceso al servicio ----

    @property
    def _servicio(self):
        return documentos

    def _ejecutar(self, operacion, /, **kwargs):
        """Invoca el servicio de documentos bajo el lock de base de datos."""
        with self.app._db_lock:
            return operacion(
                self.app.conn,
                self.app.cursor,
                usuario_id=self.app.usuario_actual,
                **kwargs,
            )

    def _theme_entry(self, entry, colors):
        if entry and entry.winfo_exists():
            entry.configure(
                text_color=colors["text_primary"],
                placeholder_text_color=colors["text_secondary"],
                fg_color=colors["bg_secondary"],
                border_color=colors["secondary"]
            )

    # ---- helpers internos (callbacks de threads) ----

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

        ruta           = self.selected_file
        usuario_nombre = self.app.usuario_nombre

        def encrypt_task():
            try:
                resultado = self._ejecutar(
                    self._servicio.crear_documento_desde_archivo,
                    usuario_nombre=usuario_nombre,
                    ruta=ruta,
                    descripcion=descripcion,
                    cedula=cedula,
                    nombres=nombres,
                    empresa=empresa,
                )
                nombre = resultado["nombre"]
                self.app.root.after(0, lambda: self._on_added(nombre, window))
            except Exception as exc:
                self.app.root.after(0, lambda err=exc: self._on_add_error(err))
            finally:
                self.app.root.after(0, self.app.progress_bar.stop)

        threading.Thread(target=encrypt_task, daemon=True).start()

    def ver_todos(self):
        # listar todos los pdfs del usuario
        if not self.app.usuario_actual:
            return

        self.app.progress_bar.start("Cargando PDFs...")

        try:
            filas = self._ejecutar(self._servicio.listar_documentos)
            self.app._populate_treeview([_fila_tree(d) for d in filas])

            colors = get_dynamic_colors()
            self.app.status.configure(
                text=f"Se muestran {len(filas)} PDFs (Encriptados)",
                text_color=colors["text_primary"]
            )
        except BackendError as e:
            Notification(self.app.root, "Error", e.mensaje, notification_type="error")
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
            filas = self._ejecutar(self._servicio.listar_documentos, termino=term)
            self.app._populate_treeview([_fila_tree(d) for d in filas])

            colors = get_dynamic_colors()
            self.app.status.configure(
                text=f"Se muestran {len(filas)} resultados",
                text_color=colors["text_primary"]
            )
            Notification(
                self.app.root,
                "Búsqueda completada",
                f"Se encontraron {len(filas)} PDF(s) encriptados",
                notification_type="success",
                duration=2000
            )
        except BackendError as e:
            Notification(self.app.root, "Error", e.mensaje, notification_type="error")
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

        usuario_nombre = self.app.usuario_nombre

        def decrypt_task():
            try:
                with self.app._db_lock:
                    datos, nombre = self._servicio.leer_documento(
                        self.app.conn,
                        self.app.cursor,
                        usuario_id=self.app.usuario_actual,
                        documento_id=pdf_id,
                        usuario_nombre=usuario_nombre,
                    )
                # mostrar sin guardar
                self.app.root.after(0, lambda d=datos, n=nombre: self._abrir_visor(d, n, window))
            except Exception as exc:
                mensaje = exc.mensaje if isinstance(exc, BackendError) else f"No se pudo abrir el PDF: {exc}"
                self.app.root.after(
                    0,
                    lambda msg=mensaje: Notification(
                        self.app.root, "Error", msg, notification_type="error"
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
            self._ejecutar(self._servicio.eliminar_documento, documento_id=pdf_id)
            self.app._reset_preview_panel()
            Notification(self.app.root, "Eliminado",
                         f"'{pdf_nombre}' eliminado correctamente",
                         notification_type="success")
            self.app.cargar_dashboard()
            self.ver_todos()
        except BackendError as e:
            Notification(self.app.root, "Error", e.mensaje, notification_type="error")
        except Exception as e:
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
        edit_win.geometry("480x560")
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
        ).pack(pady=(0, 10))

        # contenedor scrollable para campos + botones
        scroll_container = ctk.CTkScrollableFrame(
            edit_win, fg_color="transparent",
            corner_radius=0
        )
        scroll_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # habilitar scroll en Linux
        _bind_mousewheel(scroll_container)

        def add_field(label, current, placeholder=""):
            ctk.CTkLabel(
                scroll_container, text=label,
                text_color=colors["text_primary"],
                font=("Arial", 11, "bold")
            ).pack(anchor="w", padx=30)
            e = ctk.CTkEntry(
                scroll_container, width=380, height=40,
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
                self._ejecutar(
                    self._servicio.actualizar_documento,
                    documento_id=pdf_id,
                    nombre=nuevo_nombre,
                    descripcion=nueva_desc,
                    cedula=nueva_cedula,
                    nombres=nuevos_nombres,
                    empresa=nueva_empresa,
                )
                Notification(self.app.root, "Guardado",
                             "Metadatos actualizados correctamente",
                             notification_type="success")
                edit_win.destroy()
                self.ver_todos()
                self.app._reset_preview_panel()
            except BackendError as exc:
                Notification(edit_win, "Error", exc.mensaje, notification_type="error")
            except Exception as exc:
                Notification(edit_win, "Error", str(exc), notification_type="error")

        ctk.CTkButton(
            scroll_container, text="  Guardar Cambios",
            image=get_icon("save", 18),
            compound="left",
            command=guardar,
            fg_color=COLOR_PRIMARY, hover_color="#388E3C",
            text_color="white", font=("Arial", 12, "bold"),
            corner_radius=8, width=260, height=42
        ).pack(pady=(8, 4))

        ctk.CTkButton(
            scroll_container, text="Cancelar",
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

        usuario_nombre = self.app.usuario_nombre

        def export_task():
            try:
                with self.app._db_lock:
                    self._servicio.exportar_documento(
                        self.app.conn,
                        self.app.cursor,
                        usuario_id=self.app.usuario_actual,
                        documento_id=pdf_id,
                        usuario_nombre=usuario_nombre,
                        destino=dest,
                    )
                self.app.root.after(0, lambda: Notification(
                    self.app.root, "Exportado",
                    f"PDF exportado a:\n{dest}",
                    notification_type="success", duration=4000
                ))
            except Exception as e:
                mensaje = e.mensaje if isinstance(e, BackendError) else f"Error al exportar: {e}"
                self.app.root.after(0, lambda msg=mensaje: Notification(
                    self.app.root, "Error", msg, notification_type="error"
                ))
            finally:
                self.app.root.after(0, self.app.progress_bar.stop)

        threading.Thread(target=export_task, daemon=True).start()