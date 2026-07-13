from __future__ import annotations

from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from .base import Base


class GraphNode(Base):

    __tablename__ = "graph_nodes"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    knowledge_base_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    label: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    node_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    outgoing_edges = relationship(
        "GraphEdge",
        foreign_keys="GraphEdge.source_node_id",
        cascade="all, delete-orphan",
    )

    incoming_edges = relationship(
        "GraphEdge",
        foreign_keys="GraphEdge.target_node_id",
        cascade="all, delete-orphan",
    )