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

# Copyright (c) 2024 DatenJäger. All rights reserved.
