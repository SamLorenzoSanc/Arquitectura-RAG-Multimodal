from __future__ import annotations

from argon2 import PasswordHasher as _Argon2
from argon2.exceptions import VerifyMismatchError


class Argon2PasswordHasher:
    def __init__(self):
        self._hasher = _Argon2()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except VerifyMismatchError:
            return False



import os
from datetime import datetime, timedelta, timezone

import jwt

from core.exceptions import AppError

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


class JwtTokenSigner:
    expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES

    def encode(
        self,
        user_id,
        email: str,
        expires_minutes: int | None = None,
        jti: str | None = None,
        token_use: str = "session",
    ) -> str:
        minutes = expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
        expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        payload = {
            "sub": str(user_id),
            "email": email,
            "exp": expire,
            "use": token_use,
        }
        if jti:
            payload["jti"] = jti
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    def decode(self, token: str) -> dict:
        try:
            return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except jwt.ExpiredSignatureError as exc:
            raise AppError("Token expirado", 401) from exc
        except jwt.InvalidTokenError as exc:
            raise AppError("Token inválido", 401) from exc
