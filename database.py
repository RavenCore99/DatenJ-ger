

# database.py - conexion y operaciones con sqlite
# Copyright (c) 2024 DatenJäger. All rights reserved.

import sqlite3
import sys
import os
import hashlib
import secrets
import unicodedata
from datetime import datetime


#: Formas societarias que se unifican para comparar nombres de empresa. La
#: clave es lo que la gente escribe; el valor, la forma canónica.
_SIGLAS_SOCIETARIAS = {
    "sas": "sas",
    "sa": "sa",
    "ltda": "ltda",
    "limitada": "ltda",
    "sucursal": "sucursal",
    "eu": "eu",
    "sc": "sc",
    "cia": "cia",
    "cooperativa": "cooperativa",
}


def normalizar_empresa(nombre) -> str:
    """Forma canónica de un nombre de empresa, para no duplicar variantes.

    Se usa como **clave de comparación**, nunca como texto a mostrar: la
    empresa conserva el nombre tal como lo escribió el usuario. Unifica lo que
    de otro modo serían empresas distintas para la base:

    * espacios sobrantes y saltos de línea (``"Minera  del\\nNorte"``);
    * mayúsculas y minúsculas (``"MINERA DEL NORTE"``);
    * acentos (``"Minería"`` / ``"Mineria"``);
    * puntuación y siglas societarias (``"S.A.S."``, ``"SAS"``, ``"S.A.S"``);
    * el sufijo de tipo de sociedad, para que ``"Minera del Norte S.A.S."`` y
      ``"Minera del Norte"`` no se separen en dos fichas.

    Returns:
        La clave canónica, o cadena vacía si el nombre no aporta nada.
    """
    if nombre is None:
        return ""

    texto = " ".join(str(nombre).split()).strip()
    if not texto:
        return ""

    # Sin acentos y en minúsculas.
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    texto = texto.casefold()

    # La puntuación no distingue empresas: "s.a.s." y "sas" son la misma. Los
    # puntos se quitan **sin dejar hueco** —son separadores de siglas—; el resto
    # de signos pasan a espacio. Si los puntos se convirtieran en espacio, la
    # sigla quedaría "s a s" y no coincidiría con "sas" al retirar la forma
    # societaria.
    limpio = texto.replace(".", "")
    limpio = "".join(caracter if caracter.isalnum() or caracter.isspace() else " "
                     for caracter in limpio)
    palabras = limpio.split()

    # Se retira la forma societaria final para que el nombre corto y el largo
    # apunten a la misma ficha.
    while palabras and palabras[-1] in _SIGLAS_SOCIETARIAS:
        palabras.pop()

    return " ".join(palabras)

def conectar_db(db_path=None):
    # conectar bd
    # db_path permite apuntar a otra base (pruebas o servidor local);
    # sin argumento se mantiene el comportamiento historico.
    if db_path is None:
        if getattr(sys, 'frozen', False):
            basepath = sys.MEIPASS
        else:
            basepath = os.path.dirname(os.path.abspath(__file__))

        dbpath = os.path.join(basepath, 'base_datos_pdfs.db')
    else:
        dbpath = db_path
    conn = sqlite3.connect(dbpath, check_same_thread=False)
    cursor = conn.cursor()

    # pragmas para rendimiento
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")

    # tabla usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            contrasena TEXT NOT NULL,
            totp_secret TEXT,
            totp_enabled INTEGER DEFAULT 0,
            backup_codes TEXT,
            fecha_creacion TEXT NOT NULL,
            failed_attempts INTEGER DEFAULT 0,
            locked_until TEXT
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
    if 'failed_attempts' not in columns:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN failed_attempts INTEGER DEFAULT 0")
    if 'locked_until' not in columns:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN locked_until TEXT")
    if 'trust_token' not in columns:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN trust_token TEXT")
    if 'trust_expires' not in columns:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN trust_expires TEXT")

    # tabla empresas: catálogo propio para no guardar el nombre como texto
    # libre. Dos personas de la misma empresa comparten ficha, y renombrarla se
    # hace en un solo sitio.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            nombre_normalizado TEXT NOT NULL UNIQUE
        )
    ''')

    # tabla personas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula TEXT NOT NULL UNIQUE,
            nombres TEXT NOT NULL,
            empresa TEXT,
            empresa_id INTEGER REFERENCES Empresas(id) ON DELETE SET NULL
        )
    ''')

    cursor.execute("PRAGMA table_info(Personas)")
    personas_columns = [col[1] for col in cursor.fetchall()]
    if 'empresa' not in personas_columns:
        cursor.execute("ALTER TABLE Personas ADD COLUMN empresa TEXT")
    if 'empresa_id' not in personas_columns:
        # La columna de texto se conserva: es lo que escribió el usuario y sirve
        # de respaldo si algo saliera mal en la migración.
        cursor.execute(
            "ALTER TABLE Personas ADD COLUMN empresa_id INTEGER "
            "REFERENCES Empresas(id) ON DELETE SET NULL")

    # tabla pdfs
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

    # tabla etiquetas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Etiquetas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    ''')

    # relacion pdf-etiquetas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PDF_Etiquetas (
            pdf_id INTEGER,
            etiqueta_id INTEGER,
            PRIMARY KEY(pdf_id, etiqueta_id),
            FOREIGN KEY(pdf_id) REFERENCES PDFs(id) ON DELETE CASCADE,
            FOREIGN KEY(etiqueta_id) REFERENCES Etiquetas(id) ON DELETE CASCADE
        )
    ''')

    # tabla auditoria
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            accion TEXT NOT NULL,
            pdf_id INTEGER,
            usuario_id INTEGER,
            fecha TEXT NOT NULL
        )
    ''')

    # indices
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pdfs_usuario ON PDFs(usuario_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pdfs_fecha ON PDFs(fecha_subida)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pdfs_persona ON PDFs(persona_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_auditoria_fecha ON Auditoria(fecha)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_personas_empresa ON Personas(empresa_id)")

    # Migración del texto libre de empresa al catálogo. Idempotente: solo toca
    # las personas que todavía no tienen `empresa_id`.
    _migrar_empresas(cursor)

    conn.commit()
    return conn, cursor


def _migrar_empresas(cursor) -> None:
    """Pasa el texto libre de ``Personas.empresa`` al catálogo ``Empresas``.

    Idempotente: solo mira las personas que aún no tienen ``empresa_id``, así
    que puede correr en cada arranque sin duplicar nada. No borra la columna de
    texto —queda como respaldo de lo que escribió el usuario— y agrupa por la
    forma normalizada, de modo que «Minera del Norte S.A.S.» y «minera del
    norte» acaban en la misma ficha en vez de crear dos.
    """
    cursor.execute(
        "SELECT id, empresa FROM Personas "
        "WHERE empresa_id IS NULL AND empresa IS NOT NULL AND TRIM(empresa) != ''"
    )

    for persona_id, nombre in cursor.fetchall():
        clave = normalizar_empresa(nombre)
        if not clave:
            continue

        cursor.execute("SELECT id FROM Empresas WHERE nombre_normalizado = ?", (clave,))
        fila = cursor.fetchone()

        if fila:
            empresa_id = fila[0]
        else:
            cursor.execute(
                "INSERT INTO Empresas (nombre, nombre_normalizado) VALUES (?, ?)",
                (" ".join(str(nombre).split()).strip(), clave),
            )
            empresa_id = cursor.lastrowid

        cursor.execute(
            "UPDATE Personas SET empresa_id = ? WHERE id = ?", (empresa_id, persona_id))

def hash_contrasena(contrasena):
    # hashea contraseña con pbkdf2
    
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac('sha256', contrasena.encode(), salt.encode(), 260_000)
    return f"pbkdf2:{salt}:{dk.hex()}"


def verify_contrasena(contrasena, stored_hash):
    # verifica contraseña contra el hash guardado
    # soporta pbkdf2 y legacy sha256
    
    # validación de seguridad: si el hash está corrompido o NULL
    if not stored_hash or not isinstance(stored_hash, str):
        return False, False
    
    if stored_hash.startswith("pbkdf2:"):
        parts = stored_hash.split(":")
        if len(parts) != 3:
            return False, False
        _, salt, expected = parts
        
        # validar que salt y expected no estén vacíos
        if not salt or not expected:
            return False, False
        
        try:
            dk = hashlib.pbkdf2_hmac('sha256', contrasena.encode(), salt.encode(), 260_000)
            ok = dk.hex() == expected
            return ok, False
        except Exception:
            return False, False
    else:
        # sha256 viejo, hay que migrar
        try:
            legacy = hashlib.sha256(contrasena.encode()).hexdigest()
            ok = legacy == stored_hash
            return ok, ok  # needs_rehash=True cuando la contraseña coincide
        except Exception:
            return False, False

def format_size(bytes_size):
    # formato legible de bytes
    if bytes_size is None:
        return "0 B"

    bytes_size = float(bytes_size)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"

def format_date_friendly(iso_date):
    # fecha amigable
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
     # easing para animaciones
    return t ** 2 if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2


# helpers de bloqueo de cuenta

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def check_account_locked(cursor, nombre):
    # verifica si la cuenta esta bloqueada
    
    cursor.execute(
        "SELECT failed_attempts, locked_until FROM Usuarios WHERE nombre = ?",
        (nombre,)
    )
    row = cursor.fetchone()
    if not row:
        return False, 0
    failed, locked_until = row
    if locked_until:
        try:
            unlock_at = datetime.fromisoformat(locked_until)
            delta = (unlock_at - datetime.now()).total_seconds()
            if delta > 0:
                return True, int(delta)
            # ya expiro el bloqueo
            cursor.execute(
                "UPDATE Usuarios SET failed_attempts = 0, locked_until = NULL WHERE nombre = ?",
                (nombre,)
            )
        except Exception:
            pass
    return False, 0


def record_failed_attempt(cursor, conn, nombre):
     # incrementa intentos fallidos
    cursor.execute(
        "UPDATE Usuarios SET failed_attempts = failed_attempts + 1 WHERE nombre = ?",
        (nombre,)
    )
    cursor.execute("SELECT failed_attempts FROM Usuarios WHERE nombre = ?", (nombre,))
    row = cursor.fetchone()
    if row and row[0] >= MAX_FAILED_ATTEMPTS:
        from datetime import timedelta
        lock_until = (datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
        cursor.execute(
            "UPDATE Usuarios SET locked_until = ? WHERE nombre = ?",
            (lock_until, nombre)
        )
    conn.commit()


def reset_failed_attempts(cursor, conn, nombre):
     # reset intentos fallidos
    cursor.execute(
        "UPDATE Usuarios SET failed_attempts = 0, locked_until = NULL WHERE nombre = ?",
        (nombre,)
    )
    conn.commit()


# helpers token de confianza


def set_trust_token(cursor, conn, usuario_id: int, token: str, expires_iso: str):
    # guardar token confianza
    cursor.execute(
        "UPDATE Usuarios SET trust_token = ?, trust_expires = ? WHERE id = ?",
        (token, expires_iso, usuario_id)
    )
    conn.commit()


def check_trust_token(cursor, usuario_id: int, local_token: str) -> bool:
    # verificar token confianza
    if not local_token:
        return False
    cursor.execute(
        "SELECT trust_token, trust_expires FROM Usuarios WHERE id = ?",
        (usuario_id,)
    )
    row = cursor.fetchone()
    if not row or not row[0]:
        return False
    db_token, expires_iso = row
    if db_token != local_token:
        return False
    try:
        return datetime.now() < datetime.fromisoformat(expires_iso)
    except Exception:
        return False


def clear_trust_token(cursor, conn, usuario_id: int):
    # limpiar token confianza
    cursor.execute(
        "UPDATE Usuarios SET trust_token = NULL, trust_expires = NULL WHERE id = ?",
        (usuario_id,)
    )
    conn.commit()


# validador de contraseña

def password_strength(password: str) -> tuple:
    # evalua fortaleza y retorna score/label/color
    
    import re
    score = 0
    if len(password) >= 8:
        score += 1
    if re.search(r'[A-Z]', password):
        score += 1
    if re.search(r'[0-9]', password):
        score += 1
    if re.search(r'[^A-Za-z0-9]', password):
        score += 1

    labels = {0: "Muy débil", 1: "Débil", 2: "Regular", 3: "Fuerte", 4: "Muy fuerte"}
    colors = {0: "#F44336", 1: "#FF9800", 2: "#FFC107", 3: "#8BC34A", 4: "#4CAF50"}
    return score, labels[score], colors[score]






# Copyright (c) 2024 DatenJäger. All rights reserved.