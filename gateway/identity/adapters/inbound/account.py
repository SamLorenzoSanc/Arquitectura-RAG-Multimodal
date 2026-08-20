from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from identity.adapters.inbound.auth import get_current_user, get_identity
from identity.adapters.inbound.errors import http_error
from identity.composition import IdentityContainer
from models.user import User
from shared.errors import AppError

router = APIRouter(prefix="/account", tags=["Account"])


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
    from identity.composition import build_identity_container

    return await build_identity_container(db).account.get_profile(user, None, None)


@router.get("/users")
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


@router.get("/profile")
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


@router.patch("/profile")
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


@router.post("/profile/avatar")
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


@router.get("/profile/avatar")
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


@router.delete("/profile/avatar")
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


@router.get("/tokens")
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


@router.post("/tokens")
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


@router.delete("/tokens/{token_id}")
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


@router.get("/usage")
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


@router.get("/analytics")
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


@router.get("/projects")
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


@router.get("/admins")
async def list_org_admins(
    organization_id: str | None = None,
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        return await hexagon.account.list_admins(current_user, organization_id)
    except AppError as exc:
        raise http_error(exc) from exc


@router.get("/support")
async def list_support_tickets(
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    try:
        return await hexagon.account.list_support(current_user)
    except AppError as exc:
        raise http_error(exc) from exc


@router.post("/support")
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
