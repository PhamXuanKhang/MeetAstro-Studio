"""
Credential vault using Fernet symmetric encryption for provider credentials.

Uses APP_SECRET_KEY from configuration for encryption/decryption.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from src.config import get_logger, get_settings

logger = get_logger(__name__)


def _get_fernet() -> Fernet:
    """Get Fernet instance using APP_SECRET_KEY from settings."""
    settings = get_settings()
    secret_key = settings.app_secret_key

    if not secret_key:
        raise ValueError(
            "APP_SECRET_KEY is not configured. Set APP_SECRET_KEY in .env file. "
            "Generate a key with: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )

    key = secret_key.encode()
    try:
        return Fernet(key)
    except Exception:
        derived = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
        return Fernet(derived)


def encrypt(plaintext: str) -> str:
    """
    Encrypt a plaintext string.

    Args:
        plaintext: String to encrypt.

    Returns:
        Encrypted ciphertext as string.
    """
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """
    Decrypt a ciphertext string.

    Args:
        ciphertext: Encrypted string to decrypt.

    Returns:
        Decrypted plaintext.

    Raises:
        ValueError: If decryption fails (wrong key or corrupted data).
    """
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Decryption failed - wrong key or corrupted data.") from exc
