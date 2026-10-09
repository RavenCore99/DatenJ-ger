# Copyright (c) 2024 DatenJäger. All rights reserved.
# scripts/semantico/corpus_sintetico.py - corpus documental de prueba

"""Genera un corpus sintético de PDFs para evaluar la búsqueda semántica.

Crea una base SQLite temporal (o la indicada con ``--db``) con un usuario de
prueba y varios documentos realistas en tres categorías (contrato laboral,
afiliación y reporte de seguridad social), con texto real en español. Los PDFs
se generan en memoria con PyMuPDF y se cargan cifrados con el flujo real del
sistema (``crear_documento``).

Al terminar escribe ``corpus_etiquetas.json`` con el mapeo ``documento_id ->
categoria``, para medir la clasificación sin depender del nombre del archivo.

Uso:

    ./venv/bin/python scripts/semantico/corpus_sintetico.py
    ./venv/bin/python scripts/semantico/corpus_sintetico.py --db /tmp/corpus.db
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ))

from database import conectar_db  # noqa: E402
from backend.services import documentos  # noqa: E402

USUARIO_PRUEBA = "semantica-test"


# --------------------------------------------------------------------------- #
# Textos realistas por categoría
# --------------------------------------------------------------------------- #

_CONTRATO = """CONTRATO INDIVIDUAL DE TRABAJO A TÉRMINO FIJO

Entre la empresa MINERA DEL NORTE S.A.S., en adelante EL EMPLEADOR, y el señor
Pedro Ramírez, identificado con cédula de ciudadanía, en adelante EL
TRABAJADOR, se celebra el presente contrato de trabajo bajo las siguientes
cláusulas.

PRIMERA. OBJETO. El trabajador prestará sus servicios como operario de mina en
las instalaciones de la empresa, desempeñando labores de perforación y
extracción en el socavón principal.

SEGUNDA. SALARIO. El empleador pagará al trabajador un salario mensual de dos
millones de pesos, pagaderos en dos quincenas, más las prestaciones sociales
de ley.

TERCERA. JORNADA LABORAL. La jornada será de cuarenta y ocho horas semanales,
distribuidas en turnos de ocho horas, con descanso compensatorio conforme al
reglamento interno de trabajo.

CUARTA. TÉRMINO. El presente contrato tendrá una duración de doce meses,
iniciando el día primero del mes y finalizando el día último del mes siguiente.
El preaviso para dar por terminado el contrato será de treinta días.

QUINTA. SEGURIDAD. El empleador suministrará los elementos de protección
personal para trabajo en altura y trabajo en socavón, y afiliará al trabajador
al sistema de seguridad social integral antes del inicio de labores.

SEXTA. OBLIGACIONES DEL TRABAJADOR. El trabajador se obliga a cumplir el
reglamento de higiene y seguridad, a portar los elementos de protección y a
asistir puntualmente a su jornada de trabajo.

SÉPTIMA. CAUSALES DE TERMINACIÓN. Son causales de terminación del contrato las
previstas en el código sustantivo del trabajo, incluyendo terminación por
mutuo acuerdo y vencimiento del término pactado.
"""

_AFILIACION = """FORMULARIO DE AFILIACIÓN AL SISTEMA DE SEGURIDAD SOCIAL

FORMULARIO ÚNICO DE AFILIACIÓN Y REGISTRO DE NOVEDADES AL SISTEMA GENERAL DE
SEGURIDAD SOCIAL EN SALUD Y PENSIONES.

DATOS DEL AFILIADO COTIZANTE. Nombre del afiliado: Pedro Ramírez. Tipo y
número de documento: cédula de ciudadanía. Fecha de nacimiento. Lugar de
nacimiento. Estado civil. Dirección de residencia.

DATOS DE LA EMPRESA. Razón social: Minera del Norte S.A.S. Número de
identificación tributaria. Dirección del lugar de trabajo. Código de la
actividad económica relacionada con minería.

ENTIDADES SELECCIONADAS. Entidad promotora de salud EPS. Fondo de pensiones
obligatorias. Administradora de riesgos laborales ARL. Caja de compensación
familiar seleccionada por el empleador.

NOVEDAD DE INGRESO. Se registra la novedad de ingreso del trabajador al
sistema, con fecha de ingreso y tipo de cotizante. El afiliado declara que la
información suministrada es veraz y autoriza su tratamiento conforme a la ley
de protección de datos personales.

FIRMA DEL AFILIADO. FIRMA DEL REPRESENTANTE DE LA EMPRESA.
"""

_REPORTE = """REPORTE DE APORTES A SEGURIDAD SOCIAL Y PLANILLA INTEGRADA

PLANILLA INTEGRADA DE LIQUIDACIÓN DE APORTES A LA SEGURIDAD SOCIAL.

PERIODO DE COTIZACIÓN. La presente planilla corresponde al periodo mensual de
cotización, liquidando los aportes al sistema de seguridad social integral del
personal vinculado a la empresa.

CONCEPTOS LIQUIDADOS. Aportes al sistema general de pensiones obligatorias.
Aportes al sistema general de seguridad social en salud. Aportes a la
administradora de riesgos laborales ARL según el nivel de riesgo de la
actividad económica minera. Aportes parafiscales al SENA, ICBF y caja de
compensación familiar.

DETALLE POR TRABAJADOR. Se relaciona cada trabajador con su documento, salario
base de cotización, días laborados y valor liquidado por cada concepto de
seguridad social.

TOTALES. Se totalizan los aportes del periodo, el valor de la autoliquidación
de aportes y las fechas límite de pago para evitar intereses de mora.

CERTIFICADO DE APORTES. Se emite el certificado de aportes correspondiente a
cada trabajador, con el detalle de periodos cotizados a pensión, salud y
riesgos laborales.
"""


_TEMPLATES: dict[str, str] = {
    "contrato_laboral": _CONTRATO,
    "afiliacion": _AFILIACION,
    "reporte_seguridad_social": _REPORTE,
}


# --------------------------------------------------------------------------- #
# Generación
# --------------------------------------------------------------------------- #

def _pdf_desde_texto(texto: str) -> bytes:
    import fitz  # PyMuPDF
    doc = fitz.open()
    pagina = doc.new_page()
    rect = fitz.Rect(50, 50, 545, 792)
    pagina.insert_textbox(rect, texto, fontsize=11, fontname="helv", lineheight=1.35)
    return doc.tobytes()


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera un corpus sintético de PDFs")
    parser.add_argument("--db", default="/tmp/corpus_semantico.db",
                        help="base SQLite destino (default /tmp/corpus_semantico.db)")
    parser.add_argument("--por-categoria", type=int, default=3,
                        help="documentos por categoría (default 3)")
    args = parser.parse_args()

    db_path = Path(args.db)
    if db_path.exists():
        db_path.unlink()

    conn, cursor = conectar_db(str(db_path))

    # Usuario de prueba (clave = nombre, como usa el sistema).
    cursor.execute(
        "INSERT INTO Usuarios (nombre, contrasena, fecha_creacion) VALUES (?, ?, ?)",
        (USUARIO_PRUEBA, "pbkdf2:test:test", "2026-01-01T00:00:00"),
    )
    usuario_id = cursor.lastrowid
    conn.commit()

    etiquetas: dict[int, str] = {}
    for categoria, plantilla in _TEMPLATES.items():
        for i in range(1, args.por_categoria + 1):
            variante = f"{plantilla}\n\nDOCUMENTO DE REFERENCIA {categoria.upper()} N.{i}."
            pdf_bytes = _pdf_desde_texto(variante)
            doc = documentos.crear_documento(
                conn,
                cursor,
                usuario_id=usuario_id,
                usuario_nombre=USUARIO_PRUEBA,
                nombre=f"{categoria}_{i}.pdf",
                datos=pdf_bytes,
                descripcion=f"Documento de prueba {categoria} número {i}",
            )
            etiquetas[doc["id"]] = categoria
            print(f"  cargado {doc['nombre']} -> id {doc['id']} ({categoria})")

    conn.close()

    ruta_etiquetas = db_path.with_suffix(".etiquetas.json")
    ruta_etiquetas.write_text(json.dumps({str(k): v for k, v in etiquetas.items()},
                                         indent=2, ensure_ascii=False))

    print(f"\nCorpus listo:")
    print(f"  base       {db_path}")
    print(f"  usuario    {USUARIO_PRUEBA} (id {usuario_id})")
    print(f"  documentos {len(etiquetas)}")
    print(f"  etiquetas  {ruta_etiquetas}")
    return 0


if __name__ == "__main__":
    sys.exit(main())