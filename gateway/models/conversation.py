"""Módulo de persistencia para el histórico de conversaciones.

Este módulo define el modelo de datos de las conversaciones del sistema,
actuando como el contenedor principal para agrupar mensajes e integrar
múltiples inquilinos (tenants), usuarios y bases de conocimiento.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Conversation(Base):
    """Modelo de SQLAlchemy que representa una sesión de conversación.

    Estructura el historial de interacciones permitiendo el aislamiento por
    inquilino (tenant), la asignación de un usuario y el contexto de una
    base de conocimiento específica.
    """

    __tablename__ = "conversations"

    # Identificador único de la conversación (UUIDv4)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Identificador del inquilino (Tenant) para entornos multi-tenant (Opcional)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
    )

    # Identificador del usuario propietario de la conversación (Opcional)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
    )

    # Contexto de la base de conocimiento (Knowledge Base) utilizada en la sesión (Opcional)
    knowledge_base_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id"),
    )

    # Título descriptivo o resumen corto generado para la conversación (Máx 255 caracteres)
    title: Mapped[str | None] = mapped_column(String(255))

    # Fecha y hora de creación, asignada automáticamente por la base de datos (NOW)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # Fecha y hora de la última modificación, actualizada automáticamente en cada UPDATE
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )
