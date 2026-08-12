"""Módulo de persistencia para la gestión de departamentos.

Este módulo define el modelo de datos para los departamentos que pertenecen
a una organización, gestionando sus miembros y aplicando restricciones únicas.
"""

from __future__ import annotations

import uuid
from typing import (
    TYPE_CHECKING,
)  # Para análisis estático de tipos sin importaciones circulares

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

# Bloque exclusivo para linters y editores de código (Pylance/Mypy)
if TYPE_CHECKING:
    from .organization import Organization
    from .organization_member import OrganizationMember


class Department(Base):
    """Modelo de SQLAlchemy que representa un departamento de una organización.

    Permite agrupar a los miembros del equipo en áreas específicas de trabajo,
    asegurando que no existan nombres duplicados dentro de la misma organización.
    """

    __tablename__ = "departments"

    # Restricción única compuesta: evita nombres de departamento duplicados en una misma organización
    __table_args__ = (UniqueConstraint("organization_id", "name"),)

    # Identificador único del departamento (UUIDv4)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Identificador de la organización a la que pertenece el departamento.
    # Si la organización se elimina, el departamento se borra en cascada.
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Nombre del departamento (ej. 'Recursos Humanos', máx. 150 caracteres)
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    # Descripción detallada de las funciones o propósito del departamento (Opcional)
    description: Mapped[str | None] = mapped_column(Text)
