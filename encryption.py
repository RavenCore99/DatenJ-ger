
# -*- coding: utf-8 -*-
"""
encryption.py - Módulo de Encriptación
Gestiona encriptación AES-256 (Fernet) de PDFs y datos sensibles.
La clave se deriva usando PBKDF2-HMAC-SHA256 (600 000 iteraciones) para
mayor resistencia a ataques de fuerza bruta.
"""
# Copyright (c) 2024 DatenJäger. All rights reserved.

import hashlib
import base64
from cryptography.fernet import Fernet

# Número de iteraciones PBKDF2 para derivación de clave de archivo
_PBKDF2_ITERATIONS = 600_000
# Salt fijo por aplicación (la clave maestra es el nombre de usuario)
_APP_SALT = b"DatenJager_v3_AES256_salt_2024"


class EncryptionManager:
    """Gestiona encriptación AES-256 de PDFs y datos sensibles"""

    @staticmethod
    def derive_key(password: str) -> bytes:
        """Deriva una clave criptográfica de 32 bytes usando PBKDF2-HMAC-SHA256."""
        dk = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            _APP_SALT,
            _PBKDF2_ITERATIONS,
            dklen=32
        )
        return base64.urlsafe_b64encode(dk)

    @staticmethod
    def encrypt_data(data: bytes, password: str) -> bytes:
        """Encripta datos usando AES-256 (Fernet)"""
        try:
            key = EncryptionManager.derive_key(password)
            cipher = Fernet(key)
            encrypted = cipher.encrypt(data)
            return encrypted
        except Exception as e:
            raise Exception(f"Error encriptando datos: {e}")

    @staticmethod
    def decrypt_data(encrypted_data: bytes, password: str) -> bytes:
        """Desencripta datos usando AES-256 (Fernet)"""
        try:
            key = EncryptionManager.derive_key(password)
            cipher = Fernet(key)
            decrypted = cipher.decrypt(encrypted_data)
            return decrypted
        except Exception as e:
            raise Exception(f"Error desencriptando datos: {e}")
