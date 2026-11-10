"""Пароли (PBKDF2 из стандартной библиотеки) и JWT."""
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from common.config import settings

ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt, digest = stored.split("$")
        new = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iters))
        return hmac.compare_digest(new.hex(), digest)
    except (ValueError, TypeError):
        return False


def create_token(user_id: int, username: str, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": username, "uid": user_id, "role": role, "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Бросает jwt.PyJWTError, если токен плохой или просрочен."""
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
