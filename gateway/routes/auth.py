import os
from datetime import datetime, timedelta, timezone
import jwt

from dotenv import load_dotenv

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.auth import LoginRequest, LoginResponse, RegisterRequest
from argon2.exceptions import VerifyMismatchError
import uuid
from services.database import get_db
from models.user import User
from argon2 import PasswordHasher

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
    db: AsyncSession = Depends(get_db),  # usa la sesión de la request, no crea otra
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token requerido")

    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=401, detail="Token inválido: falta el identificador de usuario"
        )

    user = await db.scalar(
        select(User).where(User.id == user_id, User.active.is_(True))
    )
    if user is None:
        raise HTTPException(status_code=401, detail="Usuario inexistente o inactivo")

    return user


@router.post("/register")
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        # 1. Verificar si el usuario ya existe
        exists = await db.scalar(
            text("SELECT id FROM users WHERE email = :email"), {"email": request.email}
        )
        if exists:
            raise HTTPException(status_code=400, detail="El usuario ya existe")

        # 2. Crear la Organización por defecto
        org_id = str(uuid.uuid4())
        await db.execute(
            text("""
                INSERT INTO organizations (id, name, description, active)
                VALUES (:id, :name, :description, :active)
            """),
            {
                "id": org_id,
                "name": f"{request.name} Organization",
                "description": "Organización por defecto para nuevos usuarios",
                "active": True,
            },
        )

        # 3. Crear el Usuario
        password_hash = hash_password(request.password)
        new_user_id = await db.scalar(
            text("""
                INSERT INTO users (name, email, password_hash)
                VALUES (:name, :email, :password) RETURNING id
            """),
            {"name": request.name, "email": request.email, "password": password_hash},
        )

        # 4. Obtener el ID del rol global 'ORG_ADMIN'
        role_id = await db.scalar(text("""
                SELECT id FROM roles
                WHERE name = 'ORG_ADMIN' AND organization_id IS NULL
                LIMIT 1
            """))

        if not role_id:
            raise HTTPException(
                status_code=500,
                detail="Error crítico: No existe el rol ORG_ADMIN global en el sistema.",
            )

        # 5. Asociar el Usuario a la Organización con el rol ORG_ADMIN
        await db.execute(
            text("""
                INSERT INTO organization_members (organization_id, user_id, role_id, active)
                VALUES (:org_id, :user_id, :role_id, true)
            """),
            {"org_id": org_id, "user_id": new_user_id, "role_id": role_id},
        )

        # 6. Crear el Tenant principal
        tenant_id = str(uuid.uuid4())
        await db.execute(
            text("""
                INSERT INTO tenants (id, organization_id, name, description, active)
                VALUES (:id, :organization_id, :name, :description, true)
            """),
            {
                "id": tenant_id,
                "organization_id": org_id,
                "name": "Default",
                "description": "Tenant principal",
            },
        )

        # 7. Crear la Knowledge Base por defecto para el sistema RAG
        knowledge_base_id = str(uuid.uuid4())
        await db.execute(
            text("""
                INSERT INTO knowledge_bases (id, tenant_id, name, description, chroma_collection)
                VALUES (:id, :tenant_id, :name, :description, :chroma_collection)
            """),
            {
                "id": knowledge_base_id,
                "tenant_id": tenant_id,
                "name": "General",
                "description": "Knowledge Base por defecto",
                "chroma_collection": f"col_{tenant_id.replace('-', '')}",
            },
        )

        # =========================================================
        # 8. INSCRIBIR AUTOMÁTICAMENTE EN LA ORG GLOBAL (AgroTech)
        # =========================================================
        from utils.global_org import ensure_agrotech_membership

        await ensure_agrotech_membership(db, new_user_id)
        # =========================================================

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
        (
            await db.execute(
                text("SELECT * FROM users WHERE email = :email"),
                {"email": request.email},
            )
        )
        .mappings()
        .first()
    )

    if user is None or not user["active"]:
        raise HTTPException(
            status_code=401, detail="Credenciales incorrectas o cuenta inactiva"
        )

    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    from utils.global_org import ensure_agrotech_membership

    await ensure_agrotech_membership(db, user["id"])
    await db.commit()

    token = create_access_token(user["id"], user["email"])
    return LoginResponse(
        access_token=token, expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout")
async def logout(authorization: str = Header(...), db: AsyncSession = Depends(get_db)):
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)

    # La BD remota puede no tener aún la tabla del modelo RevokedToken.
    await db.execute(
        text("""
            CREATE TABLE IF NOT EXISTS revoked_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                token TEXT NOT NULL,
                expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                revoked_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
            """)
    )
    await db.execute(
        text(
            "INSERT INTO revoked_tokens (token, expires_at) VALUES (:token, :expires)"
        ),
        {
            "token": token,
            "expires": datetime.fromtimestamp(payload["exp"], tz=timezone.utc).replace(
                tzinfo=None
            ),
        },
    )
    await db.commit()
    return {"status": "logged out"}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": str(user.id), "name": user.name, "email": user.email}
