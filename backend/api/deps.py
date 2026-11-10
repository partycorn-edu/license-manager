"""Проверка JWT. Токен выдаёт auth, api только проверяет подпись и срок."""
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from common.security import decode_token

bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if creds is None:
        raise HTTPException(401, "Нужна авторизация")
    try:
        return decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(401, "Токен недействителен или просрочен")


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(403, "Недостаточно прав")
    return user
