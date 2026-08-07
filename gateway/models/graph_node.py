# Permite la evaluación diferida de anotaciones de tipos (PEP 563)
from __future__ import annotations

# Función para generar UUIDs aleatorios (UUIDv4)
from uuid import uuid4

# Tipos de datos de SQLAlchemy y dialecto de PostgreSQL
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID

# Herramientas de mapeo ORM para SQLAlchemy 2.0
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

# Clase base compartida por los modelos
from .base import Base


class GraphNode(Base):
    """
    Modelo ORM que representa un nodo en una estructura de datos de tipo Grafo.

    Soporta arquitectura multitenant y bases de conocimiento aisladas,
    además de definir relaciones dirigidas (entrantes y salientes) hacia 'GraphEdge'.
    """

    # Nombre de la tabla correspondiente en la base de datos PostgreSQL
    __tablename__ = "graph_nodes"

    # Clave primaria única del nodo (UUIDv4 generado automáticamente si no se provee)
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Identificador del cliente/organización (Soporte Multi-tenancy)
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    # Identificador de la base de conocimiento específica a la que pertenece el nodo
    knowledge_base_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    # Etiqueta o nombre del nodo (ej. "Empresa", "Juan Pérez", "Python")
    label: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Categoría o tipo de nodo (ej. "ENTIDAD", "DOCUMENTO", "CONCEPTO")
    node_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # --- RELACIONES DEL GRAFO ---

    # Aristas salientes: Conexiones donde este nodo actúa como ORIGEN (source_node_id).
    # - cascade="all, delete-orphan": Si se borra este nodo, sus aristas salientes se eliminan automáticamente.
    outgoing_edges = relationship(
        "GraphEdge",
        foreign_keys="GraphEdge.source_node_id",
        cascade="all, delete-orphan",
    )

    # Aristas entrantes: Conexiones donde este nodo actúa como DESTINO (target_node_id).
    # - cascade="all, delete-orphan": Si se borra este nodo, sus aristas entrantes se eliminan automáticamente.
    incoming_edges = relationship(
        "GraphEdge",
        foreign_keys="GraphEdge.target_node_id",
        cascade="all, delete-orphan",
    )
