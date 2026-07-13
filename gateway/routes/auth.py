import os
from datetime import datetime, timedelta, timezone
import jwt

from dotenv import load_dotenv

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.auth import RegisterRequest, LoginResponse, LoginRequest
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from services.database import get_db, AsyncSessionLocal
from models.user import User

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

router = APIRouter(prefix="/auth", tags=["Authentication"])

ph = PasswordHasher()


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password_ingresado: str, password_guardado_en_db: str) -> bool:
    try:
        return ph.verify(password_guardado_en_db, password_ingresado)
    except VerifyMismatchError:
        return False


def create_access_token(user_id, email):
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),   # usa la sesión de la request, no crea otra
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token requerido")

    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido: falta el identificador de usuario")

    # devuelve el modelo ORM: la ruta de upload espera current_user.id (atributo)
    user = await db.scalar(
        select(User).where(User.id == user_id, User.active.is_(True))
    )
    if user is None:
        raise HTTPException(status_code=401, detail="Usuario inexistente o inactivo")

    return user


@router.post("/register")
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        exists = await db.scalar(
            text("SELECT id FROM users WHERE email = :email"), {"email": request.email}
        )
        if exists:
            raise HTTPException(status_code=400, detail="El usuario ya existe")

        org_id = await db.scalar(text("SELECT id FROM organizations LIMIT 1"))
        if not org_id:
            raise HTTPException(status_code=500, detail="No existen organizaciones configuradas en el sistema")

        role_id = await db.scalar(
            text(
                "SELECT id FROM roles "
                "WHERE name = 'user' AND (organization_id = :org_id OR organization_id IS NULL) "
                "LIMIT 1"
            ),
            {"org_id": org_id},
        )

        password_hash = hash_password(request.password)

        new_user_id = await db.scalar(
            text(
                "INSERT INTO users (name, email, password_hash) "
                "VALUES (:name, :email, :password) RETURNING id"
            ),
            {"name": request.name, "email": request.email, "password": password_hash},
        )

        await db.execute(
            text(
                "INSERT INTO organization_members (organization_id, user_id, role_id) "
                "VALUES (:org_id, :user_id, :role_id)"
            ),
            {"org_id": org_id, "user_id": new_user_id, "role_id": role_id},
        )

        await db.commit()
        return {"status": "registered"}
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error en el registro: {e}")


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (
        await db.execute(
            text("SELECT * FROM users WHERE email = :email"), {"email": request.email}
        )
    ).mappings().first()

    if user is None or not user["active"]:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas o cuenta inactiva")

    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    token = create_access_token(user["id"], user["email"])
    return LoginResponse(access_token=token, expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.post("/logout")
async def logout(authorization: str = Header(...), db: AsyncSession = Depends(get_db)):
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)

    await db.execute(
        text("INSERT INTO revoked_tokens (token, expires_at) VALUES (:token, :expires)"),
        {"token": token, "expires": datetime.fromtimestamp(payload["exp"], tz=timezone.utc)},
    )
    await db.commit()
    return {"status": "logged out"}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": str(user.id), "name": user.name, "email": user.email}