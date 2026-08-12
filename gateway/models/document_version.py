"""Módulo de persistencia para el control de versiones de documentos.

Este módulo define la entidad de base de datos encargada de registrar el historial
de cambios de los documentos, almacenando metadatos sobre archivos, rutas físicas
y los usuarios responsables de cada carga.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import (
    TYPE_CHECKING,
)  # Para análisis estático de tipos sin importaciones circulares

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

# Bloque exclusivo para linters y editores de código (Pylance/Mypy)
if TYPE_CHECKING:
    from .document import Document
    from .user import User


class DocumentVersion(Base):
    """Modelo de SQLAlchemy que representa una versión específica de un documento.

    Mantiene un registro ordenado y único de las iteraciones de cada archivo,
    permitiendo la auditoría de quién subió el archivo y en qué momento.
    """

    __tablename__ = "document_versions"

    # Restricción única compuesta: asegura que no existan números de versión duplicados para el mismo documento
    __table_args__ = (UniqueConstraint("document_id", "version"),)

    # Identificador único de la versión del documento (UUIDv4)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Identificador del documento principal al que pertenece esta versión.
    # El borrado en cascada limpia las versiones si el documento origen es eliminado.
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
    )

    # Número secuencial de la versión (ej. 1, 2, 3)
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Nombre original del archivo cargado (Máx 255 caracteres)
    filename: Mapped[str | None] = mapped_column(String(255))

    # Ruta o URI de almacenamiento (ej. bucket de S3 o sistema de archivos local)
    storage_path: Mapped[str | None] = mapped_column(Text)

    # Identificador del usuario que realizó la carga de esta versión específica
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
    )

    # Fecha y hora con zona horaria en la que se registró la subida de la versión
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
