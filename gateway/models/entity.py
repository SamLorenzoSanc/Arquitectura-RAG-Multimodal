from __future__ import annotations

from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from .base import Base


class Entity(Base):

    __tablename__ = "entities"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    chunk_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    label: Mapped[str] = mapped_column(String)

    entity_type: Mapped[str] = mapped_column(String)

    chunk = relationship(
        "Chunk",
        back_populates="entities",
    )

    outgoing = relationship(
        "Relationship",
        foreign_keys="Relationship.source_entity_id",
    )

    incoming = relationship(
        "Relationship",
        foreign_keys="Relationship.target_entity_id",
    )