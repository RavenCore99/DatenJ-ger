#
"""
Modulo de Encriptación
encriptacion AES-256-GCM para PDFs y datos 
la clave se deriva usando PBKDF2-HMAC-SHA256 (600 000 iteraciones) 
con salt aleatorio por documento para mayor resistencia y proteccion de datos
v2: MAGIC(4) + SALT(16) + NONCE(12) + CIPHERTEXT+TAG(variable)
"""
# Copyright (c) 2024 DatenJäger. All rights reserved. #

import os
import hashlib
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.fernet import Fernet  # solo para descifrar documentos legacy (v1)

# numero de iteraciones PBKDF2 para derivacion de clave
_PBKDF2_ITERATIONS = 600_000

# tamaños fijos del formato v2
_SALT_SIZE  = 16  # bytes — salt aleatorio por documento
_NONCE_SIZE = 12  # bytes — nonce aleatorio por cifrado (estándar GCM)

# identificador de formato v2 (AES-256-GCM con salt por documento)
_MAGIC = b"DJv2"

# salt fijo legacy — solo se usa para descifrar documentos v1 ya existentes
_LEGACY_SALT = b"DatenJager_v3_AES256_salt_2024"


class EncryptionManager:
    # gestiona encriptacion AES-256-GCM de PDFs y datos sensibles

    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        # deriva una clave de 32 bytes (256 bits) usando PBKDF2-HMAC-SHA256
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            _PBKDF2_ITERATIONS,
            dklen=32
        )

    @staticmethod
    def encrypt_data(data: bytes, password: str) -> bytes:
        #
        # enncripta datos usando AES-256-GCM con salt y nonce aleatorios por documento.
            # formato de salida: MAGIC(4) + SALT(16) + NONCE(12) + CIPHERTEXT+TAG
        #   el GCM tag (16 bytes) queda incluido al final del ciphertext por AESGCM.
        
        try:
            salt   = os.urandom(_SALT_SIZE)
            nonce  = os.urandom(_NONCE_SIZE)
            key    = EncryptionManager.derive_key(password, salt)
            aesgcm = AESGCM(key)
            # AESGCM.encrypt devuelve ciphertext + GCM tag (16 bytes al final)
            ciphertext = aesgcm.encrypt(nonce, data, None)
            return _MAGIC + salt + nonce + ciphertext
        except Exception as e:
            raise Exception(f"Error encriptando datos: {e}")

    @staticmethod
    def decrypt_data(encrypted_data: bytes, password: str) -> bytes:
        
        # desencripta datos detectando automaticamente el formato:
        # - v2 (magic DJv2): AES-256-GCM con salt por documento
        # - v1 (legacy):     Fernet AES-128-CBC con salt fijo de aplicacion
        
        try:
            if encrypted_data[:4] == _MAGIC:
                # formato v2: AES-256-GCM
                offset_salt       = 4
                offset_nonce      = offset_salt  + _SALT_SIZE
                offset_ciphertext = offset_nonce + _NONCE_SIZE

                salt       = encrypted_data[offset_salt:offset_nonce]
                nonce      = encrypted_data[offset_nonce:offset_ciphertext]
                ciphertext = encrypted_data[offset_ciphertext:]

                key    = EncryptionManager.derive_key(password, salt)
                aesgcm = AESGCM(key)
                return aesgcm.decrypt(nonce, ciphertext, None)
            else:
                # formato v1 legacy: Fernet (AES-128-CBC)
                dk  = hashlib.pbkdf2_hmac(
                    'sha256',
                    password.encode('utf-8'),
                    _LEGACY_SALT,
                    _PBKDF2_ITERATIONS,
                    dklen=32
                )
                key = base64.urlsafe_b64encode(dk)
                return Fernet(key).decrypt(encrypted_data)
        except Exception as e:
            raise Exception(f"Error desencriptando datos: {e}")

    @staticmethod
    def derive_session_key(password: str, user_salt: str) -> bytes:
        # deriva una clave de sesión AES-256 (32 bytes) desde la contraseña del usuario.
        # usa el salt PBKDF2 del hash almacenado para que sea único por usuario y determinista.
        # la clave derivada se guarda en memoria en lugar de la contraseña original.
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            user_salt.encode('utf-8'),
            _PBKDF2_ITERATIONS,
            dklen=32
        )

    @staticmethod
    def encrypt_str_with_key(data: str, key: bytes) -> str:
        # cifra un string usando una clave AES-256 pre-derivada (32 bytes).
        # formato de salida: 'ENCK:<base64(nonce + ciphertext+tag)>'
        # no requiere PBKDF2 interno porque la clave ya fue derivada externamente.
        nonce = os.urandom(_NONCE_SIZE)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, data.encode('utf-8'), None)
        return "ENCK:" + base64.urlsafe_b64encode(nonce + ciphertext).decode('ascii')

    @staticmethod
    def decrypt_str_with_key(stored: str, key: bytes) -> str:
        # descifra un string cifrado con encrypt_str_with_key (prefijo 'ENCK:').
        # también soporta datos legacy en texto plano (pre-cifrado).
        # los datos 'ENC:' (password-based, del método antiguo) deben migrarse en login().
        if stored and stored.startswith("ENCK:"):
            payload = base64.urlsafe_b64decode(stored[5:])
            nonce      = payload[:_NONCE_SIZE]
            ciphertext = payload[_NONCE_SIZE:]
            aesgcm = AESGCM(key)
            return aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')
        # legacy: texto plano (pre-implementación de cifrado)
        return stored

    @staticmethod
    def encrypt_str(data: str, password: str) -> str:
        # cifra un string y retorna 'ENC:<base64>' para almacenamiento seguro en DB.
        # el prefijo 'ENC:' permite detectar valores ya cifrados vs. legacy en texto plano.
        # nota: este método se conserva solo para migración de datos legacy en login().
        encrypted = EncryptionManager.encrypt_data(data.encode('utf-8'), password)
        return "ENC:" + base64.urlsafe_b64encode(encrypted).decode('ascii')

    @staticmethod
    def decrypt_str(stored: str, password: str) -> str:
        # descifra un string cifrado con encrypt_str (ENC: password-based).
        # si no tiene el prefijo 'ENC:' lo retorna tal cual (compatibilidad con datos legacy).
        # nota: este método se conserva solo para migración de datos legacy en login().
        if stored and stored.startswith("ENC:"):
            encrypted = base64.urlsafe_b64decode(stored[4:])
            return EncryptionManager.decrypt_data(encrypted, password).decode('utf-8')
        return stored  # valor legacy en texto plano — sin cambios

# Copyright (c) 2024 DatenJäger. All rights reserved.
