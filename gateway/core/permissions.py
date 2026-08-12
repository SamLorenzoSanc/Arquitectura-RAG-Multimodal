# app/core/permissions.py
from enum import Enum
from typing import List, Dict

class Role(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"

class Permission(str, Enum):
    # Knowledge Base
    KB_CREATE = "kb:create"
    KB_READ = "kb:read"
    KB_UPDATE = "kb:update"
    KB_DELETE = "kb:delete"
    
    # Documentos
    DOC_UPLOAD = "doc:upload"
    DOC_READ = "doc:read"
    DOC_DELETE = "doc:delete"
    
    # Chat
    CHAT_CREATE = "chat:create"
    CHAT_READ = "chat:read"
    
    # Organización
    MEMBER_MANAGE = "member:manage"
    ORG_SETTINGS = "org:settings"

# Definición de la matriz de permisos por rol
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.OWNER: list(Permission), # Todos los permisos
    
    Role.ADMIN: [
        Permission.KB_CREATE, Permission.KB_READ, Permission.KB_UPDATE, Permission.KB_DELETE,
        Permission.DOC_UPLOAD, Permission.DOC_READ, Permission.DOC_DELETE,
        Permission.CHAT_CREATE, Permission.CHAT_READ,
        Permission.MEMBER_MANAGE
    ],
    
    Role.MEMBER: [
        Permission.KB_READ,
        Permission.DOC_UPLOAD, Permission.DOC_READ,
        Permission.CHAT_CREATE, Permission.CHAT_READ
    ],
    
    Role.VIEWER: [
        Permission.KB_READ,
        Permission.DOC_READ,
        Permission.CHAT_CREATE, Permission.CHAT_READ
    ]
}

def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, [])