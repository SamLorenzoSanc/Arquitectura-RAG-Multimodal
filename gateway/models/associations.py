"""Módulo de definición para la relación de muchos a muchos entre documentos y etiquetas.

Este módulo contiene la tabla intermedia de asociación necesaria para vincular
múltiples documentos con múltiples etiquetas (tags) en la base de datos PostgreSQL.
"""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID

from .base import Base

# Tabla de asociación intermedia para la relación de muchos a muchos (Many-to-Many)
document_tags = Table(
    "document_tags",
    Base.metadata,
    # Clave foránea que conecta con la tabla de documentos.
    # Se define como clave primaria compuesta junto con tag_id.
    # El borrado en cascada asegura que si se elimina un documento, se borran sus asociaciones.
    Column(
        "document_id",
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    # Clave foránea que conecta con la tabla de etiquetas.
    # Se define como clave primaria compuesta junto con document_id.
    # El borrado en cascada asegura que si se elimina una etiqueta, se borran sus asociaciones.
    Column(
        "tag_id",
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
