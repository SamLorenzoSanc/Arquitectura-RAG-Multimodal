from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from identity.composition import IdentityContainer, build_identity_container
from identity.adapters.inbound.errors import http_error
from models.user import User
from schemas.auth import LoginRequest, LoginResponse, RegisterRequest
from services.database import get_db
from shared.errors import AppError

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
    from identity.adapters.outbound.jwt_signer import JwtTokenSigner

    return JwtTokenSigner().encode(
        user_id, email, expires_minutes=expires_minutes, jti=jti, token_use=token_use
    )


def decode_token(token: str) -> dict:
    from identity.adapters.outbound.jwt_signer import JwtTokenSigner

    try:
        return JwtTokenSigner().decode(token)
    except AppError as exc:
        raise http_error(exc) from exc


def hash_password(password: str) -> str:
    from identity.adapters.outbound.argon2_hasher import Argon2PasswordHasher

    return Argon2PasswordHasher().hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    from identity.adapters.outbound.argon2_hasher import Argon2PasswordHasher

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
