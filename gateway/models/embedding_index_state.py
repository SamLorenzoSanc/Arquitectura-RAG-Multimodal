"""Estado de indexación por documento y modelo (pending / indexing / indexed / failed)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class EmbeddingIndexState(Base):
    __tablename__ = "embedding_index_state"
    __table_args__ = (
        UniqueConstraint("document_id", "embedding_model_id", name="ux_index_state_doc_model"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    embedding_model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("embedding_model.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    source_hash: Mapped[str | None] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
