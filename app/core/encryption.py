"""
Symmetric encryption utility using Fernet (AES-128-CBC + HMAC-SHA256).
Used for storing sensitive values like Razorpay Key Secrets in the database.

Requires ENCRYPTION_KEY env var — a 32-byte URL-safe base64-encoded key.
Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import base64
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


def _get_fernet():
    """Lazily import and initialise Fernet with the configured key."""
    from cryptography.fernet import Fernet, InvalidToken  # noqa: F401

    settings = get_settings()
    key = settings.encryption_key
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY is not configured. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        raise RuntimeError(f"Invalid ENCRYPTION_KEY: {exc}") from exc


def encrypt(value: str) -> str:
    """Encrypt a plaintext string. Returns a URL-safe base64 token string."""
    if not value:
        return value
    fernet = _get_fernet()
    token = fernet.encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt(token: str) -> str:
    """Decrypt an encrypted token string back to plaintext."""
    if not token:
        return token
    from cryptography.fernet import InvalidToken
    try:
        fernet = _get_fernet()
        plaintext = fernet.decrypt(token.encode("utf-8") if isinstance(token, str) else token)
        return plaintext.decode("utf-8")
    except InvalidToken as exc:
        logger.error("[Encryption] Failed to decrypt value — token may be corrupted or key mismatch.")
        raise ValueError("Decryption failed: invalid token or wrong encryption key.") from exc
