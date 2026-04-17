"""
Sécurité : déchiffrement AES128 (compatibilité WinDev) + JWT.
"""

import hashlib
from datetime import datetime, timedelta, timezone

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from jose import jwt, JWTError

from app.core.config import HASH_SECRET_KEY

# Clé AES dérivée comme en WinDev : MD5 de la phrase secrète
_AES_KEY = hashlib.md5(HASH_SECRET_KEY.encode("utf-8")).digest()  # 16 bytes = AES-128

# JWT config
JWT_SECRET = HASH_SECRET_KEY  # à séparer si besoin plus tard
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 12


def verify_password(encrypted_password: str, plain_password: str) -> bool:
    """
    Vérifie un mot de passe en déchiffrant le MDPCrypte stocké en base (AES-128).
    Compatible avec CrypteStandard/DécrypteStandard de WinDev.
    """
    if not encrypted_password:
        return False
    try:
        import base64
        encrypted_bytes = base64.b64decode(encrypted_password)

        # WinDev CrypteStandard AES128 : IV = premiers 16 octets, reste = ciphertext
        iv = encrypted_bytes[:16]
        ciphertext = encrypted_bytes[16:]

        cipher = AES.new(_AES_KEY, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted.decode("utf-8") == plain_password
    except Exception:
        return False


def create_access_token(data: dict) -> str:
    """Crée un token JWT avec expiration."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Décode un token JWT. Retourne None si invalide/expiré."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
