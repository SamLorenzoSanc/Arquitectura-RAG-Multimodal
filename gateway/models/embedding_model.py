"""Catálogo de modelos de embedding (activos / inactivos)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class EmbeddingModel(Base):
    __tablename__ = "embedding_model"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    runtime_model_id: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False, default=768)
    max_input_tokens: Mapped[int | None] = mapped_column(Integer)
    chunk_max_tokens: Mapped[int | None] = mapped_column(Integer)
    chunk_overlap: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="inactive")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
