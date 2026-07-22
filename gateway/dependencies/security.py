from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Dict, List, Optional
import jwt
from dotenv import load_dotenv

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import get_db, AsyncSessionLocal
from models.user import User

load_dotenv()

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
ALGORITHM = "HS256"


# ==========================================
# 1. ENUMS Y MATRIZ DE PERMISOS
# ==========================================

class Role(str, Enum):
    ADMIN = "admin"
    MEMBER = "user"
    VIEWER = "viewer"


class Permission(str, Enum):
    # Organización & Tenants
    ORG_READ = "org:read"
    ORG_CREATE = "org:create"
    ORG_UPDATE = "org:update"
    ORG_DELETE = "org:delete"
    ORG_SETTINGS = "org:settings"

    TENANT_READ = "tenant:read"
    TENANT_CREATE = "tenant:create"
    TENANT_UPDATE = "tenant:update"
    TENANT_DELETE = "tenant:delete"

    # Miembros & Departamentos
    MEMBER_MANAGE = "member:manage"
    DEPT_READ = "dept:read"
    DEPT_MANAGE = "dept:manage"

    # Knowledge Base
    KB_CREATE = "kb:create"
    KB_READ = "kb:read"
    KB_UPDATE = "kb:update"
    KB_DELETE = "kb:delete"

    # Documentos
    DOC_CREATE = "doc:create"
    DOC_READ = "doc:read"
    DOC_DELETE = "doc:delete"

    # Chat & RAG
    CHAT_CREATE = "chat:create"
    CHAT_READ = "chat:read"

    # Métricas
    METRICS_READ = "metrics:read"


# Mapa global de permisos por rol
ROLE_PERMISSIONS: Dict[str, List[Permission]] = {
    "admin": list(Permission),  # El rol 'admin' posee todos los permisos
    "user": [
        Permission.ORG_READ,
        Permission.TENANT_READ,
        Permission.DEPT_READ,
        Permission.KB_READ,
        Permission.DOC_CREATE,
        Permission.DOC_READ,
        Permission.CHAT_CREATE,
        Permission.CHAT_READ,
        Permission.METRICS_READ,
    ],
    "viewer": [
        Permission.ORG_READ,
        Permission.TENANT_READ,
        Permission.DEPT_READ,
        Permission.KB_READ,
        Permission.DOC_READ,
        Permission.CHAT_CREATE,
        Permission.CHAT_READ,
    ],
}


def has_permission(user_role: str, permission: Permission) -> bool:
    """Verifica si el rol posee el permiso requerido."""
    allowed_permissions = ROLE_PERMISSIONS.get(user_role.lower(), [])
    return permission in allowed_permissions


# ==========================================
# 2. AUTENTICACIÓN Y RESOLUCIÓN DE TENANT
# ==========================================

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token de acceso ha expirado."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso inválido."
        )


async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extrae y valida el usuario actual desde el header JWT Bearer."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cabecera Authorization inválida o ausente."
        )

    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: falta el identificador del usuario."
        )

    user = await db.scalar(
        select(User).where(User.id == user_id, User.active.is_(True))
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inexistente o inactivo."
        )

    return user


async def get_tenant_context(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Resuelve la Organización y Tenant activo, verificando la membresía
    y obteniendo el rol del usuario dentro de la organización.
    """
    target_org_id = x_organization_id
    target_tenant_id = x_tenant_id

    # 1. Si sólo se provee X-Tenant-ID, resolver la Organización asociada
    if target_tenant_id and not target_org_id:
        target_org_id = await db.scalar(
            text("SELECT organization_id FROM tenants WHERE id = :t_id AND active = true"),
            {"t_id": target_tenant_id}
        )

    # 2. Si sólo se provee X-Organization-ID, resolver el Tenant predeterminado
    if target_org_id and not target_tenant_id:
        target_tenant_id = await db.scalar(
            text("SELECT id FROM tenants WHERE organization_id = :org_id AND active = true ORDER BY created_at ASC LIMIT 1"),
            {"org_id": target_org_id}
        )

    if not target_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar la cabecera 'X-Tenant-ID' o 'X-Organization-ID'."
        )

    # 3. Validar la membresía activa del usuario y obtener su rol
    member_row = (
        await db.execute(
            text("""
                SELECT om.role_id, r.name as role_name
                FROM organization_members om
                JOIN roles r ON om.role_id = r.id
                WHERE om.organization_id = :org_id
                  AND om.user_id = :user_id
                  AND om.active = true
            """),
            {"org_id": target_org_id, "user_id": current_user.id}
        )
    ).mappings().first()

    if not member_row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta organización o tu membresía está inactiva."
        )

    return {
        "user_id": str(current_user.id),
        "organization_id": str(target_org_id),
        "tenant_id": str(target_tenant_id) if target_tenant_id else None,
        "role": member_row["role_name"]
    }


async def get_tenant_db(context: dict = Depends(get_tenant_context)):
    """Inyecta la sesión de la base de datos correspondiente al Tenant."""
    async with AsyncSessionLocal() as session:
        yield session


# ==========================================
# 3. GUARDIÁN DE PERMISOS (DEPENDENCY CLASS)
# ==========================================

class RequirePermission:
    """Dependencia para proteger endpoints según permisos RBAC."""
    def __init__(self, required_permission: Permission):
        self.required_permission = required_permission

    async def __call__(self, context: dict = Depends(get_tenant_context)) -> bool:
        user_role = context.get("role", "")

        if not has_permission(user_role, self.required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso denegado. Se requiere '{self.required_permission.value}'."
            )
        return True