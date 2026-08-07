"""Módulo de persistencia para los fragmentos de texto (chunks).

Este módulo define la entidad de base de datos para almacenar los bloques o
fragmentos extraídos de los documentos procesados, incluyendo metadatos como
posiciones, titulares, resúmenes y su relación con los embeddings.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Chunk(Base):
    """Modelo de SQLAlchemy que representa un fragmento de texto (chunk).

    Esta clase almacena las divisiones lógicas de un documento para facilitar
    los procesos de indexación, recuperación y generación aumentada (RAG),
    manteniendo la referencia a su documento origen y a su embedding.
    """

    __tablename__ = "chunks"

    # Identificador único del fragmento (UUIDv4)
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Identificador del documento al que pertenece el fragmento.
    # Si el documento origen se elimina, este fragmento se borra en cascada.
    document_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Índice de posición secuencial del fragmento dentro del documento original
    position: Mapped[int] = mapped_column(Integer)

    # Encabezado, título o sección contextual del fragmento
    headline: Mapped[str] = mapped_column(Text)

    # Resumen breve del contenido de este fragmento específico
    summary: Mapped[str] = mapped_column(Text)

    # Cuerpo de texto o contenido completo del fragmento
    content: Mapped[str] = mapped_column(Text)
