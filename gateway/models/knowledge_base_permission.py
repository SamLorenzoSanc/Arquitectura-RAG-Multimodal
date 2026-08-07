# Permite evaluar las anotaciones de tipos de forma diferida (PEP 563).
# Útil para declarar tipos que se definen más adelante o evitar importaciones circulares en los tipos.
from __future__ import annotations

# Módulo estándar de Python para trabajar con identificadores únicos universales (UUID).
import uuid

# Importación de tipos de columna y restricciones generales de SQLAlchemy.
from sqlalchemy import String, ForeignKey, UniqueConstraint

from typing import (
    TYPE_CHECKING,
)  # Para análisis estático de tipos sin importaciones circulares

# Tipo de dato UUID específico para el dialecto de PostgreSQL.
from sqlalchemy.dialects.postgresql import UUID

# Utilidades de SQLAlchemy 2.0 para declarar tipos mapeados y relaciones ORM.
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Clase base declarativa del proyecto de la cual heredan todos los modelos.
from .base import Base

# Bloque exclusivo para linters y editores de código (Pylance/Mypy)
if TYPE_CHECKING:
    from .organization_member import OrganizationMember
    from .knowledge_base import KnowledgeBase


class KnowledgeBasePermission(Base):
    """
    Modelo ORM que gestiona los permisos de los miembros sobre las bases de conocimiento.
    Funciona como una tabla intermedia de permisos en un esquema de control de acceso.
    """

    # Nombre explícito de la tabla en la base de datos PostgreSQL.
    __tablename__ = "knowledge_base_permissions"

    # Identificador único de la regla de permiso (Clave Primaria UUIDv4 generada automáticamente).
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Clave foránea hacia la tabla 'knowledge_bases'.
    # - ondelete="CASCADE": Si la base de conocimiento se elimina, este registro de permiso también se borra automáticamente.
    knowledge_base_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_bases.id", ondelete="CASCADE")
    )

    # Tipo o nivel de permiso (ej. "read", "write", "admin").
    # Campo obligatorio (nullable=False) con un límite máximo de 20 caracteres.
    permission: Mapped[str] = mapped_column(String(20), nullable=False)
