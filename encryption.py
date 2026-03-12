#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
encryption.py - Módulo de Encriptación
Gestiona encriptación AES-256 (Fernet) de PDFs y datos sensibles
"""

import hashlib
import base64
from cryptography.fernet import Fernet

class EncryptionManager:
    """Gestiona encriptación AES-256 de PDFs y datos sensibles"""

    @staticmethod
    def derive_key(password: str) -> bytes:
        """Deriva una clave criptográfica de una contraseña"""
        hash1 = hashlib.sha256(password.encode()).digest()
        hash2 = hashlib.sha256(hash1).digest()
        return base64.urlsafe_b64encode(hash2[:32].ljust(32, b'\0')[:32])

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
