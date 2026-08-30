from __future__ import annotations

from fastapi import HTTPException

from core.exceptions import AppError

def http_error(exc: AppError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)

from identity.service import IdentityContainer, build_identity_container
from identity.crypto import Argon2PasswordHasher, JwtTokenSigner
from core.exceptions import AppError
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from schemas.common import LoginRequest, LoginResponse, RegisterRequest
from services.database import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_identity(db: AsyncSession = Depends(get_db)) -> IdentityContainer:
    return build_identity_container(db)


async def get_current_user(
    authorization: str = Header(...),
    hexagon: IdentityContainer = Depends(get_identity),
) -> User:
    try:
        return await hexagon.authenticate.execute(authorization)
    except AppError as exc:
        raise http_error(exc) from exc


def create_access_token(
    user_id,
    email,
    expires_minutes: int | None = None,
    jti: str | None = None,
    token_use: str = "session",
):

    return JwtTokenSigner().encode(
        user_id, email, expires_minutes=expires_minutes, jti=jti, token_use=token_use
    )


def decode_token(token: str) -> dict:

    try:
        return JwtTokenSigner().decode(token)
    except AppError as exc:
        raise http_error(exc) from exc


def hash_password(password: str) -> str:

    return Argon2PasswordHasher().hash(password)


def verify_password(password: str, password_hash: str) -> bool:

    return Argon2PasswordHasher().verify(password, password_hash)


@router.post("/register")
async def register(
    request: RegisterRequest, hexagon: IdentityContainer = Depends(get_identity)
):
    try:
        return await hexagon.register.execute(
            request.name, request.email, request.password
        )
    except AppError as exc:
        raise http_error(exc) from exc


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest, hexagon: IdentityContainer = Depends(get_identity)
):
    try:
        return await hexagon.login.execute(request.email, request.password)
    except AppError as exc:
        raise http_error(exc) from exc


@router.post("/logout")
async def logout(
    authorization: str = Header(...),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        token = authorization.removeprefix("Bearer ").strip()
        return await hexagon.logout.execute(token)
    except AppError as exc:
        raise http_error(exc) from exc


@router.get("/me")
async def me(
    user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        return await hexagon.me.execute(user)
    except AppError as exc:
        raise http_error(exc) from exc


import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from models.user import User

account_router = APIRouter(prefix="/account", tags=["Account"])


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    job_title: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, max_length=30)
    island: str | None = Field(default=None, max_length=40)
    municipality: str | None = Field(default=None, max_length=80)
    bio: str | None = Field(default=None, max_length=500)
    crop_focus: str | None = Field(default=None, max_length=80)
    preferred_language: str | None = Field(default=None, max_length=8)
    notify_email: bool | None = None
    notify_whatsapp: bool | None = None


class TokenCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    kind: str = Field(default="access")
    expires_days: int = Field(default=30, ge=1, le=365)


class SupportCreate(BaseModel):
    subject: str = Field(min_length=4, max_length=200)
    message: str = Field(min_length=10, max_length=4000)
    organization_id: str | None = None


async def profile_payload(db, user) -> dict:

    return await build_identity_container(db).account.get_profile(user, None, None)


@account_router.get("/users")
async def list_managed_users(
    organization_id: uuid.UUID | None = None,
    q: str = "",
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        return await hexagon.account.list_managed_users(
            current_user, organization_id, q, limit, offset
        )
    except AppError as exc:
        raise http_error(exc) from exc


@account_router.get("/profile")
async def get_profile(
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        return await hexagon.account.get_profile(current_user, user_id, organization_id)
    except AppError as exc:
        raise http_error(exc) from exc


@account_router.patch("/profile")
async def update_profile(
    payload: ProfileUpdate,
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        return await hexagon.account.update_profile(
            current_user, payload.model_dump(exclude_unset=True), user_id, organization_id
        )
    except AppError as exc:
        raise http_error(exc) from exc


@account_router.post("/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        content = await file.read()
        return await hexagon.account.save_avatar(
            current_user, content, file.content_type or "", user_id, organization_id
        )
    except AppError as exc:
        raise http_error(exc) from exc


@account_router.get("/profile/avatar")
async def get_avatar(
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        path = await hexagon.account.avatar_path(
            current_user, user_id, organization_id
        )
        return FileResponse(path)
    except AppError as exc:
        raise http_error(exc) from exc


@account_router.delete("/profile/avatar")
async def delete_avatar(
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        return await hexagon.account.delete_avatar(
            current_user, user_id, organization_id
        )
    except AppError as exc:
        raise http_error(exc) from exc


@account_router.get("/tokens")
async def list_tokens(
    kind: str | None = None,
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        return await hexagon.account.list_tokens(
            current_user, kind, user_id, organization_id
        )
    except AppError as exc:
        raise http_error(exc) from exc


@account_router.post("/tokens")
async def create_token(
    payload: TokenCreate,
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        return await hexagon.account.create_token(
            current_user,
            payload.name,
            payload.kind,
            payload.expires_days,
            user_id,
            organization_id,
        )
    except AppError as exc:
        raise http_error(exc) from exc


@account_router.delete("/tokens/{token_id}")
async def revoke_token(
    token_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        return await hexagon.account.revoke_token(
            current_user, token_id, user_id, organization_id
        )
    except AppError as exc:
        raise http_error(exc) from exc


@account_router.get("/usage")
async def account_usage(
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        return await hexagon.account.usage(current_user, user_id, organization_id)
    except AppError as exc:
        raise http_error(exc) from exc


@account_router.get("/analytics")
async def account_analytics(
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        return await hexagon.account.analytics(
            current_user, user_id, organization_id
        )
    except AppError as exc:
        raise http_error(exc) from exc
    except Exception:
        return {
            "user_id": str(current_user.id),
            "user_name": getattr(current_user, "name", None),
            "totals": {
                "documents": 0,
                "conversations": 0,
                "questions": 0,
                "projects": 0,
                "organizations": 0,
                "api_calls": 0,
                "active_tokens": 0,
                "support_tickets": 0,
                "documents_week": 0,
                "questions_week": 0,
            },
            "activity": [],
            "recent_documents": [],
            "recent_conversations": [],
            "projects": [],
            "timeline": [],
        }


@account_router.get("/projects")
async def account_projects(
    organization_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        return await hexagon.account.projects(
            current_user, organization_id, user_id
        )
    except AppError as exc:
        raise http_error(exc) from exc


@account_router.get("/admins")
async def list_org_admins(
    organization_id: str | None = None,
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        return await hexagon.account.list_admins(current_user, organization_id)
    except AppError as exc:
        raise http_error(exc) from exc


@account_router.get("/support")
async def list_support_tickets(
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        return await hexagon.account.list_support(current_user)
    except AppError as exc:
        raise http_error(exc) from exc


@account_router.post("/support")
async def create_support_ticket(
    payload: SupportCreate,
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        return await hexagon.account.create_support(
            current_user, payload.subject, payload.message, payload.organization_id
        )
    except AppError as exc:
        raise http_error(exc) from exc

from fastapi import APIRouter, Depends

from models.user import User

user_router = APIRouter(prefix="/users", tags=["Users"])


@user_router.get("/")
async def list_users(hexagon: IdentityContainer = Depends(get_identity)):
    return await hexagon.list_users.execute()


@user_router.get("/roles")
async def list_roles(hexagon: IdentityContainer = Depends(get_identity)):
    return await hexagon.list_roles.execute()


@user_router.get("/me/roles")
async def get_my_roles(
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    return await hexagon.my_roles.execute(current_user.id)
