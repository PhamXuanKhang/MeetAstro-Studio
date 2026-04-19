"""
Credential vault — Fernet symmetric encryption cho provider credentials.
Key lấy từ APP_SECRET_KEY trong config.
"""
import base64

from cryptography.fernet import Fernet, InvalidToken

from src.config import APP_SECRET_KEY, get_logger

logger = get_logger(__name__)


def _get_fernet() -> Fernet:
    if not APP_SECRET_KEY:
        raise ValueError(
            "APP_SECRET_KEY chưa được cấu hình. "
            "Set APP_SECRET_KEY trong .env (dùng: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\")."
        )
    # Fernet key phải là 32-byte URL-safe base64 — nếu raw string thì derive bằng padding
    key = APP_SECRET_KEY.encode()
    # Nếu key chưa đúng format Fernet, pad/encode lại
    try:
        return Fernet(key)
    except Exception:
        # Fallback: hash key thành 32 bytes rồi base64-encode
        import hashlib
        derived = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
        return Fernet(derived)


def encrypt(plaintext: str) -> str:
    """Mã hóa chuỗi plaintext. Trả về ciphertext dạng string."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Giải mã ciphertext. Raise InvalidToken nếu key sai hoặc data corrupt."""
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Không thể decrypt — key sai hoặc dữ liệu bị hỏng.") from exc
