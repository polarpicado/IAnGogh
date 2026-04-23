from __future__ import annotations

import base64
from cryptography.fernet import Fernet

from app_infrastructure.config import CONFIG


class CryptoService:
    def __init__(self, key: str | None = None):
        raw = key or CONFIG.app_encryption_key
        if not raw:
            raw = Fernet.generate_key().decode("utf-8")
        if len(raw) != 44:
            raw = base64.urlsafe_b64encode(raw.encode("utf-8").ljust(32, b"0")).decode("utf-8")
        self.fernet = Fernet(raw.encode("utf-8"))

    def encrypt(self, value: str) -> str:
        if not value:
            return ""
        return self.fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, token: str) -> str:
        if not token:
            return ""
        return self.fernet.decrypt(token.encode("utf-8")).decode("utf-8")
