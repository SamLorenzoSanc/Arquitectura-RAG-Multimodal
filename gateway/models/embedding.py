"""Módulo de persistencia para embeddings vectoriales.

Este módulo define la entidad de base de datos para almacenar y consultar
los vectores generados por modelos de lenguaje (LLMs), integrando SQLAlchemy
con la extensión pgvector de PostgreSQL para búsquedas de similitud semántica.
"""

from __future__ import annotations

from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Embedding(Base):
    """Modelo de SQLAlchemy que representa los embeddings vectoriales.

    Esta clase almacena las representaciones vectoriales de los fragmentos de
    texto (chunks) generadas por modelos de Inteligencia Artificial (LLMs),
    permitiendo realizar búsquedas de similitud semántica en PostgreSQL.
    """

    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint("chunk_id", "model", name="ux_embeddings_chunk_model"),
    )

    # Identificador único del registro de embedding (UUIDv4)
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Relación uno a uno con la tabla de fragmentos (chunks)
    # Si el chunk se elimina, este embedding se borra en cascada
    chunk_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Nombre o versión del modelo de embedding utilizado (ej. 'llama3')
    model: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Vector numérico de alta dimensionalidad (fijado en 4096 dimensiones)
    vector: Mapped[list[float]] = mapped_column(
        Vector(4096),
        nullable=False,
    )


# Índice especializado para optimizar las búsquedas vectoriales aproximadas
Index(
    "ix_embeddings_vector",
    Embedding.vector,
    postgresql_using="hnsw",  # Algoritmo HNSW para búsquedas rápidas (ANN)
    postgresql_with={
        "m": 16,  # Número máximo de conexiones por nodo en el grafo
        "ef_construction": 64,  # Tamaño de la lista dinámica para la construcción del grafo
    },
    postgresql_ops={
        "vector": "vector_cosine_ops"
    },  # Optimizado para distancia de coseno
)
