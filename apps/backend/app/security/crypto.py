"""AES-GCM envelope encryption for sensitive data."""

from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings


@dataclass(slots=True)
class EncryptedPayload:
    nonce_b64: str
    ciphertext_b64: str


class EncryptionService:
    def __init__(self, key_b64: str | None = None) -> None:
        key_material = key_b64 or settings.storage_encryption_key
        if key_material:
            self._key = base64.urlsafe_b64decode(_normalize_key(key_material))
        else:
            # Stable local fallback derived from JWT secret so data remains
            # decryptable across service instances/restarts in local mode.
            # In production, set STORAGE_ENCRYPTION_KEY explicitly.
            self._key = _derive_local_fallback_key()
        self._aes = AESGCM(self._key)

    def encrypt_bytes(self, plaintext: bytes, associated_data: bytes | None = None) -> EncryptedPayload:
        nonce = os.urandom(12)
        ciphertext = self._aes.encrypt(nonce, plaintext, associated_data)
        return EncryptedPayload(
            nonce_b64=base64.urlsafe_b64encode(nonce).decode("utf-8"),
            ciphertext_b64=base64.urlsafe_b64encode(ciphertext).decode("utf-8"),
        )

    def decrypt_bytes(self, payload: EncryptedPayload, associated_data: bytes | None = None) -> bytes:
        nonce = base64.urlsafe_b64decode(payload.nonce_b64.encode("utf-8"))
        ciphertext = base64.urlsafe_b64decode(payload.ciphertext_b64.encode("utf-8"))
        return self._aes.decrypt(nonce, ciphertext, associated_data)

    def encrypt_text(self, text: str, associated_data: bytes | None = None) -> EncryptedPayload:
        return self.encrypt_bytes(text.encode("utf-8"), associated_data=associated_data)

    def decrypt_text(self, payload: EncryptedPayload, associated_data: bytes | None = None) -> str:
        return self.decrypt_bytes(payload, associated_data=associated_data).decode("utf-8")


def _normalize_key(key_b64: str) -> str:
    key = key_b64.strip()
    missing_padding = len(key) % 4
    if missing_padding:
        key += "=" * (4 - missing_padding)
    return key


def _derive_local_fallback_key() -> bytes:
    material = f"medical-doc-assistant:{settings.jwt_secret_key}".encode()
    return hashlib.sha256(material).digest()
