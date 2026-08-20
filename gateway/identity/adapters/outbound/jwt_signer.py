from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import jwt

from shared.errors import AppError

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
