# Habilita la evaluación diferida de anotaciones de tipos (PEP 563).
from __future__ import annotations

# Módulos para manejo de UUIDs, fechas y tipado estático.
import uuid
from datetime import datetime
from typing import TYPE_CHECKING  # Exclusivo para análisis estático de linters / IDEs

# Tipos de columna, restricciones y claves foráneas de SQLAlchemy.
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Clase base declarativa del proyecto.
from .base import Base

# --- IMPORTACIONES EXCLUSIVAS PARA LINTERS / TYPE CHECKING ---
# Se ejecutan ÚNICAMENTE durante el análisis estático de código (mypy, pyright, VS Code).
# Evita importaciones circulares en tiempo de ejecución.
if TYPE_CHECKING:
    from .conversation import Conversation
    from .document import Document
    from .knowledge_base import KnowledgeBase
    from .organization import Organization
    from .processing_job import ProcessingJob


class Tenant(Base):
    """
    Modelo ORM que representa un Tenant (Inquilino / Entorno aislado) dentro de una Organización.

    Sirve como la frontera de aislamiento multi-inquilino (Multitenancy), agrupando sus propias
    bases de conocimiento, documentos, conversaciones, trabajos de procesamiento y claves API.
    """

    # Nombre de la tabla física en la base de datos PostgreSQL.
    __tablename__ = "tenants"

    # Restricción a nivel de tabla: garantiza que el nombre del tenant sea único
    # dentro de una misma organización.
    __table_args__ = (UniqueConstraint("organization_id", "name"),)

    # Identificador único del tenant (Clave Primaria UUIDv4).
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Clave foránea vinculada a la organización madre.
    # - ondelete="CASCADE": Si se elimina la organización, sus tenants también se eliminan.
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Nombre del tenant / entorno (máximo 150 caracteres, obligatorio).
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    # Descripción opcional sobre la finalidad de este tenant.
    description: Mapped[str | None] = mapped_column(Text)

    # Clave de API por defecto o UUID asignado al tenant.
    api_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)

    # Flag booleano para activar o desactivar el acceso al tenant (por defecto True).
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Marca de tiempo de creación registrada automáticamente por el servidor SQL (NOW()).
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()  # pylint: disable=not-callable
    )
