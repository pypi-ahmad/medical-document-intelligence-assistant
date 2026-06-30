"""Tests for upload encryption/decryption safety behavior."""

from app.config import settings
from app.security.crypto import EncryptionService


def test_encryption_local_fallback_is_stable() -> None:
    original_key = settings.storage_encryption_key
    original_jwt = settings.jwt_secret_key
    try:
        settings.storage_encryption_key = ""
        settings.jwt_secret_key = "unit-test-secret"

        encryptor = EncryptionService()
        decryptor = EncryptionService()

        payload = encryptor.encrypt_text("cbc 5.6 mmol/L")
        assert decryptor.decrypt_text(payload) == "cbc 5.6 mmol/L"
    finally:
        settings.storage_encryption_key = original_key
        settings.jwt_secret_key = original_jwt

