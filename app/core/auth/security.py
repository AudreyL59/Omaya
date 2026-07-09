"""
Sécurité : déchiffrement AES128 (compatibilité WinDev) + JWT.
"""

import hashlib
import secrets as _secrets
import string
from datetime import datetime, timedelta, timezone

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from jose import jwt, JWTError

from app.core.config import HASH_SECRET_KEY

# Clé AES dérivée comme en WinDev : MD5 de la phrase secrète
_AES_KEY = hashlib.md5(HASH_SECRET_KEY.encode("utf-8")).digest()  # 16 bytes = AES-128

# JWT config
JWT_SECRET = HASH_SECRET_KEY  # à séparer si besoin plus tard
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 12


def decrypt_password(encrypted_password) -> str | None:
    """Dechiffre un MDPCrypte (AES-128 CBC, format WinDev) en clair.

    Retourne le mot de passe en clair ou None si echec.
    Utile pour Btn 'Renvoyer les codes' qui envoie le MDP existant.
    """
    if not encrypted_password:
        return None
    try:
        if isinstance(encrypted_password, (bytes, bytearray, memoryview)):
            enc = bytes(encrypted_password)
        else:
            import base64
            enc = base64.b64decode(encrypted_password)
        iv = enc[:16]
        ct = enc[16:]
        cipher = AES.new(_AES_KEY, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(ct), AES.block_size).decode("utf-8")
    except Exception:
        return None


def encrypt_password(plain_password: str) -> bytes:
    """Chiffre un mot de passe en clair au format compatible WinDev
    (AES-128 CBC, IV alea + PKCS7). Retourne les bytes bruts a
    stocker dans mdp_crypte (bytea).
    """
    iv = get_random_bytes(16)
    cipher = AES.new(_AES_KEY, AES.MODE_CBC, iv)
    ct = cipher.encrypt(pad(plain_password.encode("utf-8"), AES.block_size))
    return iv + ct


_MDP_CHARSET = string.ascii_letters + string.digits


def generate_password(length: int = 12) -> str:
    """Genere un mot de passe alea (equivalent WinDev GenereMotDePasse)."""
    return "".join(_secrets.choice(_MDP_CHARSET) for _ in range(length))


def verify_password(encrypted_password, plain_password: str) -> bool:
    """
    Vérifie un mot de passe en déchiffrant le mdp_crypte stocké en base (AES-128).
    Compatible avec CrypteStandard/DécrypteStandard de WinDev.

    Gère les deux sources :
    - PG    : colonne `bytea` -> `bytes` / `memoryview` (octets bruts).
    - HFSQL : champ binaire renvoyé par le bridge en `str` base64.
    """
    if not encrypted_password:
        return False
    try:
        if isinstance(encrypted_password, (bytes, bytearray, memoryview)):
            encrypted_bytes = bytes(encrypted_password)
        else:
            # Bridge HFSQL : binaire serialise en base64 (str)
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
