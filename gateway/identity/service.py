from __future__ import annotations

from datetime import datetime, timezone

from identity.domain import (
    AccountRepository,
    PasswordHasher,
    TokenSigner,
    TokenStore,
    UserRepository,
)
from core.exceptions import AppError


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



import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from identity.domain import AccountRepository, TokenSigner, UserRepository
from core.exceptions import AppError

AVATAR_ROOT = Path(
    os.getenv(
        "AVATAR_STORAGE_ROOT",
        Path(__file__).resolve().parent.parent / "uploads" / "avatars",
    )
)
AVATAR_MAX_BYTES = 2 * 1024 * 1024
AVATAR_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AccountService:
    def __init__(
        self,
        accounts: AccountRepository,
        users: UserRepository,
        signer: TokenSigner,
    ):
        self.accounts = accounts
        self.users = users
        self.signer = signer

    async def list_managed_users(
        self, current_user, organization_id, q: str, limit: int, offset: int
    ) -> dict:
        limit = min(max(limit, 1), 50)
        offset = max(offset, 0)
        is_admin = await self.users.is_admin(current_user.id)
        self_item = {
            "id": str(current_user.id),
            "name": current_user.name,
            "email": current_user.email,
            "role": None,
            "active": True,
            "is_self": True,
        }
        if not is_admin:
            return {
                "is_admin": False,
                "total": 1,
                "limit": limit,
                "offset": 0,
                "items": [self_item],
            }
        if organization_id is None:
            raise AppError("Selecciona una organización", 400)
        if not await self.accounts.is_org_member(organization_id, current_user.id):
            raise AppError("No perteneces a esta organización", 403)
        rows = await self.accounts.list_managed_users(
            organization_id, q.strip(), limit, offset
        )
        total = int(rows[0]["total"]) if rows else 0
        return {
            "is_admin": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [
                {
                    "id": str(row["id"]),
                    "name": row["name"],
                    "email": row["email"],
                    "role": row["role"],
                    "active": bool(row["active"]),
                    "is_self": str(row["id"]) == str(current_user.id),
                }
                for row in rows
            ],
        }

    async def get_profile(self, current_user, user_id, organization_id) -> dict:
        target = await self.accounts.resolve_managed_user(
            current_user, user_id, organization_id
        )
        return await self.accounts.profile_payload(target)

    async def update_profile(
        self, current_user, payload: dict, user_id, organization_id
    ) -> dict:
        target = await self.accounts.resolve_managed_user(
            current_user, user_id, organization_id
        )
        name = payload.get("name")
        if name is not None:
            name = name.strip()
            if len(name) < 2:
                raise AppError("El nombre es demasiado corto", 400)
            await self.accounts.update_name(target.id, name)
            target.name = name
        profile_data = {key: value for key, value in payload.items() if key != "name"}
        if profile_data:
            await self.accounts.upsert_profile(target.id, profile_data)
        await self.accounts.commit()
        refreshed = await self.users.get_orm_by_id(target.id)
        return await self.accounts.profile_payload(refreshed or target)

    async def save_avatar(
        self, current_user, content: bytes, content_type: str, user_id, organization_id
    ) -> dict:
        target = await self.accounts.resolve_managed_user(
            current_user, user_id, organization_id
        )
        if not content:
            raise AppError("Imagen vacía", 400)
        if len(content) > AVATAR_MAX_BYTES:
            raise AppError("La imagen no puede superar 2 MB", 400)
        suffix = AVATAR_TYPES.get((content_type or "").lower())
        if suffix is None:
            raise AppError("Usa JPG, PNG o WEBP", 400)
        AVATAR_ROOT.mkdir(parents=True, exist_ok=True)
        path = AVATAR_ROOT / f"{target.id}{suffix}"
        for old in AVATAR_ROOT.glob(f"{target.id}.*"):
            if old != path:
                old.unlink(missing_ok=True)
        path.write_bytes(content)
        await self.accounts.upsert_profile(target.id, {"avatar_path": str(path)})
        await self.accounts.commit()
        return await self.accounts.profile_payload(target)

    async def avatar_path(self, current_user, user_id, organization_id) -> str:
        target = await self.accounts.resolve_managed_user(
            current_user, user_id, organization_id
        )
        stored = await self.accounts.get_avatar_path(target.id)
        if not stored or not Path(str(stored)).exists():
            raise AppError("Sin foto de perfil", 404)
        return str(stored)

    async def delete_avatar(self, current_user, user_id, organization_id) -> dict:
        target = await self.accounts.resolve_managed_user(
            current_user, user_id, organization_id
        )
        stored = await self.accounts.get_avatar_path(target.id)
        if stored:
            Path(str(stored)).unlink(missing_ok=True)
        await self.accounts.clear_avatar(target.id)
        await self.accounts.commit()
        return await self.accounts.profile_payload(target)

    async def list_tokens(self, current_user, kind, user_id, organization_id):
        target = await self.accounts.resolve_managed_user(
            current_user, user_id, organization_id
        )
        return await self.accounts.list_tokens(target.id, kind)

    async def create_token(
        self, current_user, name: str, kind: str, expires_days: int, user_id, organization_id
    ) -> dict:
        target = await self.accounts.resolve_managed_user(
            current_user, user_id, organization_id
        )
        kind = kind if kind in {"access", "api_key"} else "access"
        jti = uuid.uuid4()
        expires_minutes = expires_days * 24 * 60
        token = self.signer.encode(
            target.id,
            target.email,
            expires_minutes=expires_minutes,
            jti=str(jti),
            token_use=kind,
        )
        prefix = f"agro_{str(jti).replace('-', '')[:8]}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
        token_id = uuid.uuid4()
        await self.accounts.insert_token(
            {
                "id": token_id,
                "user_id": target.id,
                "name": name.strip(),
                "kind": kind,
                "prefix": prefix,
                "token_hash": hash_token(token),
                "jti": str(jti),
                "expires_at": expires_at.replace(tzinfo=None),
            }
        )
        return {
            "id": str(token_id),
            "name": name.strip(),
            "kind": kind,
            "prefix": prefix,
            "expires_at": expires_at.isoformat(),
            "token": token,
            "token_type": "Bearer",
            "user_id": str(target.id),
            "note": "Copia el token ahora. No se volverá a mostrar.",
        }

    async def revoke_token(self, current_user, token_id, user_id, organization_id):
        target = await self.accounts.resolve_managed_user(
            current_user, user_id, organization_id
        )
        await self.accounts.revoke_token(token_id, target.id)
        return {"status": "revoked", "id": str(token_id)}

    async def usage(self, current_user, user_id, organization_id) -> dict:
        target = await self.accounts.resolve_managed_user(
            current_user, user_id, organization_id
        )
        counts = await self.accounts.usage(target.id)
        return {"user_id": str(target.id), **counts}

    async def analytics(self, current_user, user_id, organization_id) -> dict:
        target = await self.accounts.resolve_managed_user(
            current_user, user_id, organization_id
        )
        snapshot = await self.accounts.analytics(target.id)
        return {
            "user_id": str(target.id),
            "user_name": getattr(target, "name", None),
            **snapshot,
        }

    async def projects(self, current_user, organization_id, user_id) -> dict:
        target = await self.accounts.resolve_managed_user(
            current_user, user_id, organization_id
        )
        if not await self.accounts.is_org_member(organization_id, current_user.id):
            raise AppError("No perteneces a esta organización", 403)
        rows = await self.accounts.projects(organization_id, target.id)
        return {
            "user_id": str(target.id),
            "items": [
                {
                    "id": str(row["id"]),
                    "name": row["name"],
                    "description": row["description"],
                    "use_case": row.get("use_case") or "Q/A",
                    "created_by": (str(row["created_by"]) if row["created_by"] else None),
                    "created_at": row["created_at"],
                    "document_count": int(row["document_count"] or 0),
                    "owned": str(row["created_by"] or "") == str(target.id),
                }
                for row in rows
            ],
        }

    async def list_admins(self, current_user, organization_id):
        return await self.accounts.list_admins(current_user.id, organization_id)

    async def list_support(self, current_user) -> dict:
        is_admin = await self.users.is_admin(current_user.id)
        tickets = await self.accounts.list_support(current_user.id, is_admin)
        return {"is_admin": is_admin, "tickets": tickets}

    async def create_support(self, current_user, subject, message, organization_id):
        ticket_id = uuid.uuid4()
        await self.accounts.create_support(
            {
                "id": ticket_id,
                "user_id": current_user.id,
                "organization_id": organization_id,
                "subject": subject.strip(),
                "message": message.strip(),
            }
        )
        return {"id": str(ticket_id), "status": "open"}


from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from identity.crypto import Argon2PasswordHasher, JwtTokenSigner
from identity.postgres import PostgresIdentityRepository


@dataclass
class IdentityContainer:
    hasher: Argon2PasswordHasher
    signer: JwtTokenSigner
    repo: PostgresIdentityRepository
    register: RegisterUser
    login: LoginUser
    logout: LogoutUser
    authenticate: AuthenticateUser
    me: GetMe
    list_users: ListUsers
    list_roles: ListRoles
    my_roles: ListMyRoles
    account: AccountService


def build_identity_container(db: AsyncSession) -> IdentityContainer:
    hasher = Argon2PasswordHasher()
    signer = JwtTokenSigner()
    repo = PostgresIdentityRepository(db)
    return IdentityContainer(
        hasher=hasher,
        signer=signer,
        repo=repo,
        register=RegisterUser(repo, hasher),
        login=LoginUser(repo, hasher, signer),
        logout=LogoutUser(repo, signer),
        authenticate=AuthenticateUser(repo, repo, signer),
        me=GetMe(repo, repo),
        list_users=ListUsers(repo),
        list_roles=ListRoles(repo),
        my_roles=ListMyRoles(repo),
        account=AccountService(repo, repo, signer),
    )
