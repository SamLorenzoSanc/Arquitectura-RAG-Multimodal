# models/knowledge_base.py
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    chroma_collection: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="knowledge_bases")
    creator: Mapped["User | None"] = relationship(back_populates="created_knowledge_bases")
    documents: Mapped[list["Document"]] = relationship(back_populates="knowledge_base")
    permissions: Mapped[list["KnowledgeBasePermission"]] = relationship(back_populates="knowledge_base")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="knowledge_base")