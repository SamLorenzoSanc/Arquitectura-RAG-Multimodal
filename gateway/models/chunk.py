from __future__ import annotations

from uuid import uuid4

from sqlalchemy import Integer
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from .base import Base


class Chunk(Base):

    __tablename__ = "chunks"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    document_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    position: Mapped[int] = mapped_column(Integer)

    headline: Mapped[str] = mapped_column(Text)

    summary: Mapped[str] = mapped_column(Text)

    content: Mapped[str] = mapped_column(Text)

    document = relationship(
        "Document",
        back_populates="chunks",
    )

    embedding = relationship(
        "Embedding",
        uselist=False,
        back_populates="chunk",
        cascade="all, delete-orphan",
    )

    entities = relationship(
        "Entity",
        back_populates="chunk",
        cascade="all, delete-orphan",
    )