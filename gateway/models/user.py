from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # owner_id en documents
    documents: Mapped[list["Document"]] = relationship(back_populates="owner")
    # created_by en knowledge_bases
    created_knowledge_bases: Mapped[list["KnowledgeBase"]] = relationship(back_populates="creator")
    # uploaded_by en document_versions
    uploaded_versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="uploader")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user")
    memberships: Mapped[list["OrganizationMember"]] = relationship(back_populates="user")
    api_logs: Mapped[list["ApiLog"]] = relationship(back_populates="user")