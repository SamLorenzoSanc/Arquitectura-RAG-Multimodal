"""Módulo de persistencia para la gestión de documentos principales.

Este módulo define la entidad central de documentos del sistema, manejando sus metadatos,
su pertenencia a inquilinos y bases de conocimiento, su control de versiones y sus
asociaciones con etiquetas y trabajos de procesamiento.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import (
    TYPE_CHECKING,
)  # Para análisis estático de tipos sin importaciones circulares

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
    Column,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .associations import document_tags
from .base import Base

# Bloque exclusivo para linters y editores de código (Pylance/Mypy)
if TYPE_CHECKING:
    from .tenant import Tenant
    from .knowledge_base import KnowledgeBase
    from .user import User
    from .document_version import DocumentVersion
    from .processing_job import ProcessingJob
    from .message_source import MessageSource
    from .tag import Tag


class Document(Base):
    """Modelo de SQLAlchemy que representa un documento dentro del sistema.

    Actúa como la entidad central para el almacenamiento de archivos, vinculando
    el documento con su propietario, el inquilino (tenant) aislado y la base
    de conocimiento correspondiente para los flujos de trabajo de ingesta de datos.
    """

    __tablename__ = "documents"

    # Identificador único del documento (UUIDv4)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Identificador del inquilino (Tenant) para entornos multi-tenant (Opcional)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
    )

    # Identificador de la base de conocimiento asociada al documento (Opcional)
    knowledge_base_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id"),
    )

    # Identificador del usuario propietario del documento (Opcional)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
    )

    # Nombre original del archivo (ej. 'reporte.pdf', máx. 255 caracteres)
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Título descriptivo personalizado para el documento (Opcional)
    title: Mapped[str | None] = mapped_column(String(255))

    # Descripción o notas adicionales sobre el contenido del documento (Opcional)
    description: Mapped[str | None] = mapped_column(Text)

    # Tipo MIME del archivo para identificar su formato (ej. 'application/pdf', Opcional)
    mime_type: Mapped[str | None] = mapped_column(String(100))

    # Ruta de almacenamiento o URI única donde reside el archivo físico (S3, File System, etc.)
    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Tamaño del archivo expresado en bytes utilizando un entero de precisión grande (Opcional)
    size: Mapped[int | None] = mapped_column(BigInteger)

    # Contador o indicador del número de versión actual del documento (Por defecto 1)
    current_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    file_hash = Column(String(64), nullable=False, index=True)
    # Fecha y hora con zona horaria del registro del archivo, automatizado por el motor SQL (NOW)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
