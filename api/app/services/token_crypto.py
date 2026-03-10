"""
Encriptacao/decriptacao de tokens OAuth com Fernet (AES-128-CBC).
Usa JWT_SECRET_KEY como base para derivar a chave Fernet.
"""
import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import settings


def _get_fernet() -> Fernet:
    """Deriva chave Fernet de 32 bytes a partir do JWT_SECRET_KEY."""
    key = hashlib.sha256(settings.JWT_SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_token(token: str) -> str:
    """Encripta um token OAuth."""
    if not token:
        return ""
    return _get_fernet().encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decripta um token OAuth."""
    if not encrypted:
        return ""
    return _get_fernet().decrypt(encrypted.encode()).decode()
