from __future__ import annotations

from datetime import datetime, timezone

from identity.domain.ports import (
    AccountRepository,
    PasswordHasher,
    TokenSigner,
    TokenStore,
    UserRepository,
)
from shared.errors import AppError


class RegisterUser:
    def __init__(self, users: UserRepository, hasher: PasswordHasher):
        self.users = users
        self.hasher = hasher

    async def execute(self, name: str, email: str, password: str) -> dict:
        if await self.users.email_exists(email):
            raise AppError("El usuario ya existe", 400)
        try:
            await self.users.register(name, email, self.hasher.hash(password))
        except AppError:
            await self.users.rollback()
            raise
        except Exception as exc:
            await self.users.rollback()
            raise AppError(f"Error en el registro: {exc}", 500) from exc
        return {"status": "registered"}


class LoginUser:
    def __init__(
        self, users: UserRepository, hasher: PasswordHasher, signer: TokenSigner
    ):
        self.users = users
        self.hasher = hasher
        self.signer = signer

    async def execute(self, email: str, password: str) -> dict:
        user = await self.users.get_by_email(email)
        if user is None or not user["active"]:
            raise AppError("Credenciales incorrectas o cuenta inactiva", 401)
        if not self.hasher.verify(password, user["password_hash"]):
            raise AppError("Credenciales incorrectas", 401)
        await self.users.ensure_agrotech(user["id"])
        await self.users.commit()
        token = self.signer.encode(user["id"], user["email"])
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": self.signer.expire_minutes * 60,
        }


class LogoutUser:
    def __init__(self, tokens: TokenStore, signer: TokenSigner):
        self.tokens = tokens
        self.signer = signer

    async def execute(self, raw_token: str) -> dict:
        payload = self.signer.decode(raw_token)
        expires = datetime.fromtimestamp(payload["exp"], tz=timezone.utc).replace(
            tzinfo=None
        )
        await self.tokens.revoke_session(raw_token, expires)
        return {"status": "logged out"}


class AuthenticateUser:
    def __init__(
        self, users: UserRepository, tokens: TokenStore, signer: TokenSigner
    ):
        self.users = users
        self.tokens = tokens
        self.signer = signer

    async def execute(self, authorization: str):
        if not authorization.startswith("Bearer "):
            raise AppError("Token requerido", 401)
        token = authorization.removeprefix("Bearer ").strip()
        payload = self.signer.decode(token)
        user_id = payload.get("sub")
        if not user_id:
            raise AppError("Token inválido: falta el identificador de usuario", 401)
        user = await self.users.get_orm_by_id(user_id)
        if user is None:
            raise AppError("Usuario inexistente o inactivo", 401)
        token_jti = payload.get("jti")
        if token_jti:
            await self.tokens.assert_access_token_active(token_jti, user.id)
        return user


class GetMe:
    def __init__(self, users: UserRepository, accounts: AccountRepository):
        self.users = users
        self.accounts = accounts

    async def execute(self, user) -> dict:
        try:
            payload = await self.accounts.profile_payload(user)
        except Exception:
            payload = {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "has_avatar": False,
            }
        payload["is_admin"] = await self.users.is_admin(user.id)
        return payload


class ListUsers:
    def __init__(self, users: UserRepository):
        self.users = users

    async def execute(self) -> list:
        return await self.users.list_users()


class ListRoles:
    def __init__(self, users: UserRepository):
        self.users = users

    async def execute(self) -> list:
        return await self.users.list_roles()


class ListMyRoles:
    def __init__(self, users: UserRepository):
        self.users = users

    async def execute(self, user_id) -> list:
        return await self.users.list_user_roles(user_id)
