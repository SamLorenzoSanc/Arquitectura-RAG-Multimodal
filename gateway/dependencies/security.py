from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, List, Optional
from dotenv import load_dotenv

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from identity.adapters.inbound.auth import get_current_user
from services.database import get_db, AsyncSessionLocal
from models.user import User

load_dotenv()

logger = logging.getLogger(__name__)


# ==========================================
# 1. ENUMS Y MATRIZ DE PERMISOS
# ==========================================


class Role(str, Enum):
    """Roles legacy + operativos del seed."""

    ADMIN = "admin"
    MEMBER = "user"
    VIEWER = "viewer"
    SUPER_ADMIN = "SUPER_ADMIN"
    ORG_ADMIN = "ORG_ADMIN"
    FARM_MANAGER = "FARM_MANAGER"
    LOGISTICS_OPERATOR = "LOGISTICS_OPERATOR"
    QUALITY_CONTROLLER = "QUALITY_CONTROLLER"
    USER = "USER"


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
    DOC_READ = "doc:read"

    # Chat & RAG
    CHAT_CREATE = "chat:create"
    CHAT_READ = "chat:read"

    EVAL_READ = "eval:read"
    EVAL_MANAGE = "eval:manage"
    SETTINGS_MANAGE = "settings:manage"
    DEBUG_ACCESS = "debug:access"

    # Métricas
    METRICS_READ = "metrics:read"


_ALL = list(Permission)

_BASE_READ = [
    Permission.ORG_READ,
    Permission.KB_READ,
    Permission.DOC_READ,
    Permission.CHAT_CREATE,
    Permission.CHAT_READ,
    Permission.EVAL_READ,
    Permission.EVAL_MANAGE,
    Permission.DEPT_READ,
]

# Mapa global de permisos por rol (legacy + seed operativo)
ROLE_PERMISSIONS: Dict[str, List[Permission]] = {
    "admin": _ALL,
    "super_admin": _ALL,
    "org_admin": [p for p in _ALL if p != Permission.DEBUG_ACCESS],
    "farm_manager": _BASE_READ
    + [
        Permission.EVAL_READ,
        Permission.METRICS_READ,
        Permission.DEPT_READ,
    ],
    "logistics_operator": _BASE_READ
    + [
        Permission.EVAL_READ,
        Permission.METRICS_READ,
        Permission.DEPT_READ,
    ],
    "quality_controller": _BASE_READ
    + [
        Permission.EVAL_READ,
        Permission.METRICS_READ,
        Permission.DEPT_READ,
    ],
    "user": _BASE_READ + [Permission.DEPT_READ, Permission.EVAL_READ],
    "member": _BASE_READ + [Permission.DEPT_READ, Permission.EVAL_READ],
    "viewer": [
        Permission.ORG_READ,
        Permission.KB_READ,
        Permission.DOC_READ,
        Permission.CHAT_CREATE,
        Permission.CHAT_READ,
        Permission.DEPT_READ,
        Permission.EVAL_READ,
    ],
}


def _normalize_role_key(user_role: str) -> str:
    return (user_role or "user").strip().lower()


def has_permission(user_role: str, permission: Permission) -> bool:
    """Verifica si el rol posee el permiso requerido."""
    allowed_permissions = ROLE_PERMISSIONS.get(_normalize_role_key(user_role))
    if allowed_permissions is None:
        allowed_permissions = ROLE_PERMISSIONS["user"]
    return permission in allowed_permissions


async def user_is_admin(db: AsyncSession, user_id: object) -> bool:
    """Comprueba si el usuario posee una membresía administrativa activa."""
    return bool(
        await db.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM organization_members AS membership
                    JOIN roles AS role ON role.id = membership.role_id
                    WHERE membership.user_id = :user_id
                      AND membership.active = true
                      AND lower(role.name) IN (
                          'admin', 'super_admin', 'org_admin'
                      )
                )
                """
            ),
            {"user_id": user_id},
        )
    )


# ==========================================
# 2. AUTENTICACIÓN Y RESOLUCIÓN DE TENANT
# ==========================================
# get_current_user vive en identity (único punto de autenticación JWT).


async def get_tenant_context(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
            text(
                "SELECT organization_id FROM tenants WHERE id = :t_id AND active = true"
            ),
            {"t_id": target_tenant_id},
        )

    # 2. Si sólo se provee X-Organization-ID, resolver el Tenant predeterminado
    if target_org_id and not target_tenant_id:
        target_tenant_id = await db.scalar(
            text(
                "SELECT id FROM tenants WHERE organization_id = :org_id AND active = true ORDER BY created_at ASC LIMIT 1"
            ),
            {"org_id": target_org_id},
        )

    if not target_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar la cabecera 'X-Tenant-ID' o 'X-Organization-ID'.",
        )

    # 3. Validar la membresía activa del usuario y obtener su rol
    member_row = (
        (
            await db.execute(
                text("""
                SELECT om.role_id, r.name as role_name
                FROM organization_members om
                JOIN roles r ON om.role_id = r.id
                WHERE om.organization_id = :org_id
                  AND om.user_id = :user_id
                  AND om.active = true
            """),
                {"org_id": target_org_id, "user_id": current_user.id},
            )
        )
        .mappings()
        .first()
    )

    if not member_row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta organización o tu membresía está inactiva.",
        )

    return {
        "user_id": str(current_user.id),
        "organization_id": str(target_org_id),
        "tenant_id": str(target_tenant_id) if target_tenant_id else None,
        "role": member_row["role_name"],
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
                detail=f"Permiso denegado. Se requiere '{self.required_permission.value}'.",
            )
        return True
