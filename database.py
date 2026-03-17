#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
database.py - Módulo de Base de Datos
Gestiona toda la conexión y operaciones con SQLite
"""

import sqlite3
import sys
import os
from datetime import datetime

def conectar_db():
    """Conecta a la base de datos SQLite"""
    if getattr(sys, 'frozen', False):
        basepath = sys.MEIPASS
    else:
        basepath = os.path.dirname(os.path.abspath(__file__))

    dbpath = os.path.join(basepath, 'base_datos_pdfs.db')
    conn = sqlite3.connect(dbpath, check_same_thread=False)
    cursor = conn.cursor()

    # Performance pragmas: WAL for better concurrency, NORMAL sync for speed
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")

    # Crear tabla de usuarios con 2FA
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            contrasena TEXT NOT NULL,
            totp_secret TEXT,
            totp_enabled INTEGER DEFAULT 0,
            backup_codes TEXT,
            fecha_creacion TEXT NOT NULL
        )
    ''')

    cursor.execute("PRAGMA table_info(Usuarios)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'totp_secret' not in columns:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN totp_secret TEXT")
    if 'totp_enabled' not in columns:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN totp_enabled INTEGER DEFAULT 0")
    if 'backup_codes' not in columns:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN backup_codes TEXT")
    if 'fecha_creacion' not in columns:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN fecha_creacion TEXT NOT NULL DEFAULT ''")

    # Crear tabla de Personas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula TEXT NOT NULL UNIQUE,
            nombres TEXT NOT NULL
        )
    ''')

    # Crear tabla de PDFs con encriptación
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PDFs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            datos BLOB NOT NULL,
            datos_encriptados INTEGER DEFAULT 1,
            tamano INTEGER NOT NULL,
            fecha_subida TEXT NOT NULL,
            usuario_id INTEGER,
            persona_id INTEGER,
            FOREIGN KEY(usuario_id) REFERENCES Usuarios(id) ON DELETE CASCADE,
            FOREIGN KEY(persona_id) REFERENCES Personas(id) ON DELETE SET NULL
        )
    ''')

    cursor.execute("PRAGMA table_info(PDFs)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'datos_encriptados' not in columns:
        cursor.execute("ALTER TABLE PDFs ADD COLUMN datos_encriptados INTEGER DEFAULT 1")
    if 'persona_id' not in columns:
        cursor.execute("ALTER TABLE PDFs ADD COLUMN persona_id INTEGER REFERENCES Personas(id) ON DELETE SET NULL")

    # Crear tabla de Etiquetas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Etiquetas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    ''')

    # Crear tabla de PDF_Etiquetas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PDF_Etiquetas (
            pdf_id INTEGER,
            etiqueta_id INTEGER,
            PRIMARY KEY(pdf_id, etiqueta_id),
            FOREIGN KEY(pdf_id) REFERENCES PDFs(id) ON DELETE CASCADE,
            FOREIGN KEY(etiqueta_id) REFERENCES Etiquetas(id) ON DELETE CASCADE
        )
    ''')

    # Crear tabla de Auditoría
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            accion TEXT NOT NULL,
            pdf_id INTEGER,
            usuario_id INTEGER,
            fecha TEXT NOT NULL
        )
    ''')

    # Crear índices
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pdfs_usuario ON PDFs(usuario_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pdfs_fecha ON PDFs(fecha_subida)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pdfs_persona ON PDFs(persona_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_auditoria_fecha ON Auditoria(fecha)")

    conn.commit()
    return conn, cursor

def hash_contrasena(contrasena):
    """Hashea una contraseña usando SHA256"""
    import hashlib
    return hashlib.sha256(contrasena.encode()).hexdigest()

def format_size(bytes_size):
    """Convierte bytes a formato legible"""
    if bytes_size is None:
        return "0 B"

    bytes_size = float(bytes_size)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"

def format_date_friendly(iso_date):
    """Convierte fecha ISO a formato amigable"""
    if not iso_date:
        return "Desconocida"

    try:
        dt = datetime.fromisoformat(iso_date)
        now = datetime.now()
        delta = now - dt

        if delta.days == 0:
            if delta.seconds < 60:
                return "Ahora mismo"
            elif delta.seconds < 3600:
                minutes = delta.seconds // 60
                return f"Hace {minutes}m"
            else:
                hours = delta.seconds // 3600
                return f"Hace {hours}h"
        elif delta.days == 1:
            return "Ayer"
        elif delta.days < 7:
            return f"Hace {delta.days}d"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"Hace {weeks}w"
        else:
            months = delta.days // 30
            if months < 12:
                return f"Hace {months}mo"
            else:
                years = delta.days // 365
                return f"Hace {years}y"
    except:
        return iso_date

def ease_in_out(t):
    """Función de easing in-out"""
    return t ** 2 if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2
