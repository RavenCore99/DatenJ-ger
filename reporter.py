"""
Modulo de Reportes
Generacio de reportes de inventario en CSV y PDF para DatenJäger.

"""
# Copyright (c) 2024 DatenJäger. All rights reserved.

import csv
from datetime import datetime
import fitz  # PyMuPDF 


# ── Paleta colores (RGB 0.0–1.0) ───
_AZUL_CORP   = (0.10, 0.13, 0.49)   # #1a237e
_VERDE_CORP  = (0.30, 0.69, 0.31)   # #4CAF50
_GRIS_CLARO  = (0.94, 0.94, 0.94)
_BLANCO      = (1.0,  1.0,  1.0)
_NEGRO       = (0.0,  0.0,  0.0)
_GRIS_TEXTO  = (0.35, 0.35, 0.35)

# Paleta para el grafico de barras (máx. 6 colores cíclicos)
_CHART_COLORS = [
    (0.30, 0.69, 0.31),  # verde
    (0.23, 0.51, 0.96),  # azul
    (0.61, 0.15, 0.69),  # morado
    (0.00, 0.54, 0.48),  # teal
    (0.96, 0.49, 0.00),  # naranja
    (0.90, 0.22, 0.21),  # rojo
]


class ReporteInventario:
    """Punto de entrada publico para generar reportes CSV y PDF."""

    # ── CSV ──

    @staticmethod
    def generar_csv(rows: list, dest_path: str, usuario_nombre: str = "") -> None:
        """
        Exporta el inventario como CSV compatible 
        rows: lista de tuplas (id, nombre, descripcion, tamano_bytes, fecha_iso,
                               cedula, nombres, empresa)
        """
        from database import format_size

        headers = [
            "ID", "Nombre del Archivo", "Descripción",
            "Tamaño", "Fecha de Subida", "Cédula", "Nombres Titular", "Empresa",
        ]

        with open(dest_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["DatenJäger — Reporte de Inventario Documental"])
            writer.writerow([f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"])
            writer.writerow([f"Usuario: {usuario_nombre}"])
            writer.writerow([])
            writer.writerow(headers)

            for row in rows:
                try:
                    fecha = datetime.fromisoformat(row[4]).strftime("%d/%m/%Y %H:%M") if row[4] else ""
                except Exception:
                    fecha = row[4] or ""
                writer.writerow([
                    row[0],
                    row[1] or "",
                    row[2] or "",
                    format_size(row[3]),
                    fecha,
                    row[5] or "",
                    row[6] or "",
                    row[7] or "",
                ])

            writer.writerow([])
            writer.writerow([f"Total de documentos: {len(rows)}"])

    # ── PDF ─────

    @staticmethod
    def generar_pdf(rows: list, stats: dict, dest_path: str,
                    usuario_nombre: str = "") -> None:
        """
        genera un reporte PDF de 3 páginas:
          1. Portada con resumen ejecutivo y lista de empresas
          2. Tabla del inventario (paginada automáticamente)
          3. Gráfico de barras horizontales por empresa

        stats: {
            'total_pdfs'    : int,
            'total_size_str': str,
            'total_personas': int,
            'total_empresas': int,
            'empresas_data' : [(empresa, count), ...]   ordenada DESC
        }
        """
        doc = fitz.open()
        gen = _PDFGenerator(doc, usuario_nombre)
        gen.pagina_portada(stats)
        gen.pagina_inventario(rows)
        if stats.get("empresas_data"):
            gen.pagina_grafico(stats["empresas_data"])
        doc.save(dest_path)
        doc.close()


# ── Generador interno (no usar directamente) ─────────────────────────────

class _PDFGenerator:
    """construye las paginas del reporte usando las primitivas de PyMuPDF."""

    PAGE_W  = 595   # A4 ancho 
    PAGE_H  = 842   # A4 alto
    MARGIN  = 40

    def __init__(self, doc: fitz.Document, usuario: str):
        self.doc    = doc
        self.usuario = usuario
        self.fecha_gen = datetime.now().strftime("%d/%m/%Y  %H:%M")

    # ── pagina 1: Portada / Resumen ─

    def pagina_portada(self, stats: dict):
        page = self.doc.new_page(width=self.PAGE_W, height=self.PAGE_H)

        # banda azul superior
        page.draw_rect(fitz.Rect(0, 0, self.PAGE_W, 112),
                       color=None, fill=_AZUL_CORP)
        # franja verde acento
        page.draw_rect(fitz.Rect(0, 112, self.PAGE_W, 116),
                       color=None, fill=_VERDE_CORP)

        page.insert_text((self.MARGIN, 54),
                         "DatenJäger",
                         fontsize=30, fontname="helv-bo", color=_BLANCO)
        page.insert_text((self.MARGIN, 78),
                         "Sistema de Gestión Documental — Sector Minero Ubaté",
                         fontsize=10, fontname="helv", color=(0.75, 0.85, 1.0))
        page.insert_text((self.MARGIN, 100),
                         f"Reporte de Inventario  ·  {self.fecha_gen}  ·  Usuario: {self.usuario}",
                         fontsize=8, fontname="helv", color=(0.65, 0.75, 0.95))

        # ── tarjetas de resumen ──
        page.insert_text((self.MARGIN, y),
                         "RESUMEN EJECUTIVO",
                         fontsize=11, fontname="helv-bo", color=_AZUL_CORP)
        page.draw_line(fitz.Point(self.MARGIN, y + 5),
                       fitz.Point(self.PAGE_W - self.MARGIN, y + 5),
                       color=_VERDE_CORP, width=1.5)

        y += 22
        tarjetas = [
            ("📄  Documentos",    str(stats.get("total_pdfs", 0))),
            ("💾  Espacio",        stats.get("total_size_str", "0 B")),
            ("👥  Personas",       str(stats.get("total_personas", 0))),
            ("🏢  Empresas",       str(stats.get("total_empresas", 0))),
        ]
        n       = len(tarjetas)
        gap     = 10
        card_w  = (self.PAGE_W - 2 * self.MARGIN - gap * (n - 1)) / n
        colores = [_AZUL_CORP, _VERDE_CORP,
                   (0.38, 0.09, 0.43), (0.00, 0.54, 0.48)]

        for i, (label, valor) in enumerate(tarjetas):
            x = self.MARGIN + i * (card_w + gap)
            page.draw_rect(fitz.Rect(x, y, x + card_w, y + 74),
                           color=None, fill=colores[i], radius=6)
            page.insert_textbox(
                fitz.Rect(x + 4, y + 8, x + card_w - 4, y + 44),
                valor,
                fontsize=20, fontname="helv-bo",
                color=_BLANCO, align=fitz.TEXT_ALIGN_CENTER
            )
            page.insert_textbox(
                fitz.Rect(x + 4, y + 46, x + card_w - 4, y + 70),
                label,
                fontsize=8, fontname="helv",
                color=(0.85, 0.93, 1.0), align=fitz.TEXT_ALIGN_CENTER
            )

        # ── lista de empresas en portada ──
        y += 96
        if stats.get("empresas_data"):
            page.insert_text((self.MARGIN, y),
                             "DISTRIBUCIÓN POR EMPRESA",
                             fontsize=11, fontname="helv-bo", color=_AZUL_CORP)
            page.draw_line(fitz.Point(self.MARGIN, y + 5),
                           fitz.Point(self.PAGE_W - self.MARGIN, y + 5),
                           color=_VERDE_CORP, width=1.5)
            y += 20
            for j, (emp, cnt) in enumerate(stats["empresas_data"][:10]):
                color = _CHART_COLORS[j % len(_CHART_COLORS)]
                # Cuadro de color
                page.draw_rect(fitz.Rect(self.MARGIN, y, self.MARGIN + 10, y + 10),
                               color=None, fill=color)
                page.insert_text(
                    (self.MARGIN + 16, y + 9),
                    f"{emp or 'Sin empresa'}  —  {cnt} documento{'s' if cnt != 1 else ''}",
                    fontsize=9, fontname="helv", color=_NEGRO
                )
                y += 18

        self._footer(page)

    # ── paginas de inventario (paginacion automatica) ─

    def pagina_inventario(self, rows: list):
        from database import format_size

        # Definición de columnas: (encabezado, ancho_pt, índice_row, truncar_chars)
        cols = [
            ("Nombre",       115, 1, 21),
            ("Descripción",  130, 2, 26),
            ("Tamaño",        50, 3, None),
            ("Fecha",         65, 4, None),
            ("Cédula",        54, 5, None),
            ("Titular",       82, 6, 14),
            ("Empresa",       75, 7, 14),
        ]
        total_w  = sum(c[1] for c in cols)
        table_x  = (self.PAGE_W - total_w) / 2
        row_h    = 16
        header_h = 20

        page  = None
        y     = 0

        def nueva_pagina():
            nonlocal page, y
            page = self.doc.new_page(width=self.PAGE_W, height=self.PAGE_H)
            page.draw_rect(fitz.Rect(0, 0, self.PAGE_W, 36),
                           color=None, fill=_AZUL_CORP)
            page.insert_text((self.MARGIN, 23),
                             "DatenJäger  —  Inventario de Documentos",
                             fontsize=11, fontname="helv-bo", color=_BLANCO)
            page.insert_text((self.PAGE_W - 170, 23),
                             f"Generado: {self.fecha_gen}",
                             fontsize=8, fontname="helv", color=(0.75, 0.85, 1.0))
            y = 54
            dibujar_header()

        def dibujar_header():
            nonlocal y
            page.draw_rect(fitz.Rect(table_x, y, table_x + total_w, y + header_h),
                           color=None, fill=_AZUL_CORP)
            x = table_x
            for (hdr, w, _idx, _trunc) in cols:
                page.insert_textbox(
                    fitz.Rect(x + 3, y + 3, x + w - 2, y + header_h - 2),
                    hdr, fontsize=7.5, fontname="helv-bo",
                    color=_BLANCO, align=fitz.TEXT_ALIGN_LEFT
                )
                x += w
            y += header_h

        nueva_pagina()

        for i, row in enumerate(rows):
            if y + row_h > self.PAGE_H - 52:
                self._footer(page)
                nueva_pagina()

            bg = _GRIS_CLARO if i % 2 == 0 else _BLANCO
            page.draw_rect(fitz.Rect(table_x, y, table_x + total_w, y + row_h),
                           color=None, fill=bg)

            x = table_x
            for (_, w, idx, trunc) in cols:
                raw = row[idx]
                if idx == 3:
                    val = format_size(raw)
                elif idx == 4:
                    try:
                        val = datetime.fromisoformat(raw).strftime("%d/%m/%Y") if raw else "—"
                    except Exception:
                        val = raw or "—"
                else:
                    val = str(raw) if raw else "—"

                if trunc and len(val) > trunc:
                    val = val[:trunc] + "…"

                page.insert_textbox(
                    fitz.Rect(x + 3, y + 2, x + w - 2, y + row_h - 1),
                    val, fontsize=7, fontname="helv",
                    color=_NEGRO, align=fitz.TEXT_ALIGN_LEFT
                )
                x += w

            # Línea divisora entre filas
            page.draw_line(
                fitz.Point(table_x, y + row_h),
                fitz.Point(table_x + total_w, y + row_h),
                color=(0.85, 0.85, 0.85), width=0.3
            )
            y += row_h

        # Pie de tabla
        y += 10
        if y < self.PAGE_H - 52:
            page.insert_text(
                (table_x, y),
                f"Total de documentos registrados: {len(rows)}",
                fontsize=8, fontname="helv-bo", color=_GRIS_TEXTO
            )
        self._footer(page)

    # ── pagina para grafico de barras ──

    def pagina_grafico(self, empresas_data: list):
        page = self.doc.new_page(width=self.PAGE_W, height=self.PAGE_H)

        # Header
        page.draw_rect(fitz.Rect(0, 0, self.PAGE_W, 36),
                       color=None, fill=_AZUL_CORP)
        page.insert_text((self.MARGIN, 23),
                         "DatenJäger  —  Distribución de Documentos por Empresa",
                         fontsize=11, fontname="helv-bo", color=_BLANCO)

        # titulo seccion
        y = 60
        page.insert_text((self.MARGIN, y),
                         "DOCUMENTOS POR EMPRESA",
                         fontsize=11, fontname="helv-bo", color=_AZUL_CORP)
        page.draw_line(fitz.Point(self.MARGIN, y + 5),
                       fitz.Point(self.PAGE_W - self.MARGIN, y + 5),
                       color=_VERDE_CORP, width=1.5)

        # barras horizontales
        y        = 84
        bar_h    = 24
        gap      = 10
        label_w  = 135
        chart_x  = self.MARGIN + label_w + 6
        chart_w  = self.PAGE_W - self.MARGIN - chart_x - 55
        max_val  = max((cnt for _, cnt in empresas_data), default=1)

        for j, (emp, cnt) in enumerate(empresas_data[:14]):
            color = _CHART_COLORS[j % len(_CHART_COLORS)]
            bar_w = max(6, int((cnt / max_val) * chart_w))
            label = (emp or "Sin empresa")[:24]

            # etiqueta izquierda
            page.insert_textbox(
                fitz.Rect(self.MARGIN, y + 4, self.MARGIN + label_w, y + bar_h),
                label, fontsize=8, fontname="helv",
                color=_NEGRO, align=fitz.TEXT_ALIGN_RIGHT
            )
            # barra coloreada
            page.draw_rect(
                fitz.Rect(chart_x, y + 3, chart_x + bar_w, y + bar_h - 3),
                color=None, fill=color, radius=3
            )
            # valor numerico al final
            page.insert_text(
                (chart_x + bar_w + 6, y + bar_h - 5),
                str(cnt),
                fontsize=8, fontname="helv-bo", color=color
            )
            y += bar_h + gap

        # nota
        y += 14
        page.insert_text(
            (self.MARGIN, y),
            "* Se muestran hasta 14 empresas. Sin nombre se agrupan como 'Sin empresa'.",
            fontsize=7, fontname="helv", color=_GRIS_TEXTO
        )

        self._footer(page)

    # ── Footer  ──

    def _footer(self, page: fitz.Page):
        page.draw_line(
            fitz.Point(self.MARGIN, self.PAGE_H - 30),
            fitz.Point(self.PAGE_W - self.MARGIN, self.PAGE_H - 30),
            color=_GRIS_CLARO, width=0.8
        )
        page.insert_text(
            (self.MARGIN, self.PAGE_H - 17),
            "DatenJäger © 2024  ·  Sistema de Gestión Documental  ·  Sector Minero Ubaté",
            fontsize=7, fontname="helv", color=_GRIS_TEXTO
        )
        page.insert_text(
            (self.PAGE_W - 100, self.PAGE_H - 17),
            f"Usuario: {self.usuario}",
            fontsize=7, fontname="helv", color=_GRIS_TEXTO
        )
