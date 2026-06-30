"""Encrypted local filesystem storage adapter."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.security.crypto import EncryptedPayload, EncryptionService


class EncryptedFileStorage:
    """Store files encrypted at rest using AES-GCM."""

    def __init__(self, root_dir: str | None = None, encryption: EncryptionService | None = None) -> None:
        self.root = Path(root_dir or settings.upload_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.encryption = encryption or EncryptionService()

    def write_encrypted(self, relative_path: str, data: bytes, *, aad: bytes | None = None) -> dict:
        payload = self.encryption.encrypt_bytes(data, associated_data=aad)
        target = self.root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload.ciphertext_b64.encode("utf-8"))
        sidecar = target.with_suffix(target.suffix + ".meta.json")
        sidecar.write_text(
            json.dumps({"nonce_b64": payload.nonce_b64, "encrypted": True}, ensure_ascii=True),
            encoding="utf-8",
        )
        return {"path": str(target), "meta_path": str(sidecar), "encrypted": True}

    def read_encrypted(self, relative_path: str, *, aad: bytes | None = None) -> bytes:
        target = self.root / relative_path
        sidecar = target.with_suffix(target.suffix + ".meta.json")
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        payload = EncryptedPayload(
            nonce_b64=str(metadata["nonce_b64"]),
            ciphertext_b64=target.read_text(encoding="utf-8"),
        )
        return self.encryption.decrypt_bytes(payload, associated_data=aad)
