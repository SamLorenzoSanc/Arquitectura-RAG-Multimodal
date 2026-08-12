"""
Paquete de modelos SQLAlchemy 2.0.

Importar todos los modelos aquí garantiza que estén registrados en el
mismo registry antes de que se configuren los mappers. Esto evita errores
de resolución de referencias por nombre (strings) en los relationship().
"""

from .base import Base
from .associations import document_tags

from .organization import Organization
from .department import Department
from .tenant import Tenant
from .role import Role
from .user import User
from .organization_member import OrganizationMember
from .knowledge_base import KnowledgeBase
from .knowledge_base_permission import KnowledgeBasePermission
from .document import Document
from .document_version import DocumentVersion
from .tag import Tag
from .processing_job import ProcessingJob
from .conversation import Conversation
from .message import Message
from .message_source import MessageSource
from .revoked_token import RevokedToken

__all__ = [
    "Base",
    "document_tags",
    "Organization",
    "Department",
    "Tenant",
    "Role",
    "User",
    "OrganizationMember",
    "KnowledgeBase",
    "KnowledgeBasePermission",
    "Document",
    "DocumentVersion",
    "Tag",
    "ProcessingJob",
    "Conversation",
    "Message",
    "MessageSource",
    "RevokedToken",
]
