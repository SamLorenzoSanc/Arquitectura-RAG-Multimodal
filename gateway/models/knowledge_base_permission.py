from __future__ import annotations

import uuid

from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class KnowledgeBasePermission(Base):
    __tablename__ = "knowledge_base_permissions"
    __table_args__ = (UniqueConstraint("knowledge_base_id", "member_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    knowledge_base_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_bases.id", ondelete="CASCADE")
    )
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organization_members.id", ondelete="CASCADE")
    )
    permission: Mapped[str] = mapped_column(String(20), nullable=False)

    knowledge_base: Mapped["KnowledgeBase | None"] = relationship(back_populates="permissions")
    member: Mapped["OrganizationMember | None"] = relationship(back_populates="kb_permissions")