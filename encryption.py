# encryption.py - cifrado aes-256-gcm
# pbkdf2 con salt aleatorio por documento

import os
import hashlib
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.fernet import Fernet  # solo para docs legacy v1

# iteraciones pbkdf2
_PBKDF2_ITERATIONS = 600_000

# tamaños formato v2
_SALT_SIZE  = 16
_NONCE_SIZE = 12

# magic bytes formato v2
_MAGIC = b"DJv2"

# salt legacy para docs viejos
_LEGACY_SALT = b"DatenJager_v3_AES256_salt_2024"


class EncryptionManager:
    # manejo de encriptacion aes-256

    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        # derivar clave 256 bits
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            _PBKDF2_ITERATIONS,
            dklen=32
        )

    @staticmethod
    def encrypt_data(data: bytes, password: str) -> bytes:
        # encripta con aes-256-gcm
        # formato: MAGIC + SALT + NONCE + CIPHERTEXT+TAG
        
        try:
            salt   = os.urandom(_SALT_SIZE)
            nonce  = os.urandom(_NONCE_SIZE)
            key    = EncryptionManager.derive_key(password, salt)
            aesgcm = AESGCM(key)
            # encrypt agrega el tag gcm al final
            ciphertext = aesgcm.encrypt(nonce, data, None)
            return _MAGIC + salt + nonce + ciphertext
        except Exception as e:
            raise Exception(f"Error encriptando datos: {e}")

    @staticmethod
    def decrypt_data(encrypted_data: bytes, password: str) -> bytes:
        # desencripta detectando formato v2 o v1 legacy
        try:
            if encrypted_data[:4] == _MAGIC:
                # v2 gcm
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
                # v1 legacy fernet
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
        # clave de sesion derivada del password
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            user_salt.encode('utf-8'),
            _PBKDF2_ITERATIONS,
            dklen=32
        )

    @staticmethod
    def encrypt_str_with_key(data: str, key: bytes) -> str:
        # cifra string con clave pre-derivada
        nonce = os.urandom(_NONCE_SIZE)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, data.encode('utf-8'), None)
        return "ENCK:" + base64.urlsafe_b64encode(nonce + ciphertext).decode('ascii')

    @staticmethod
    def decrypt_str_with_key(stored: str, key: bytes) -> str:
        # descifra string ENCK: o devuelve plain si es legacy
        if stored and stored.startswith("ENCK:"):
            payload = base64.urlsafe_b64decode(stored[5:])
            nonce      = payload[:_NONCE_SIZE]
            ciphertext = payload[_NONCE_SIZE:]
            aesgcm = AESGCM(key)
            return aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')
        # legacy sin cifrar
        return stored

    @staticmethod
    def encrypt_str(data: str, password: str) -> str:
        # cifra string con password (solo para migracion legacy)
        encrypted = EncryptionManager.encrypt_data(data.encode('utf-8'), password)
        return "ENC:" + base64.urlsafe_b64encode(encrypted).decode('ascii')

    @staticmethod
    def decrypt_str(stored: str, password: str) -> str:
        # descifra ENC: o devuelve tal cual si es legacy
        if stored and stored.startswith("ENC:"):
            encrypted = base64.urlsafe_b64decode(stored[4:])
            return EncryptionManager.decrypt_data(encrypted, password).decode('utf-8')
        return stored  # legacy sin cambios

# Copyright (c) 2024 DatenJäger. All rights reserved.
