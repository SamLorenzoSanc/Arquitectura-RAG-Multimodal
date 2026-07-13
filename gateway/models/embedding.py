from __future__ import annotations

from uuid import uuid4

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from .base import Base


class Embedding(Base):

    __tablename__ = "embeddings"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    chunk_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    model: Mapped[str] = mapped_column(Text)

    vector: Mapped[str] = mapped_column(Text)

    chunk = relationship(
        "Chunk",
        back_populates="embedding",
    )