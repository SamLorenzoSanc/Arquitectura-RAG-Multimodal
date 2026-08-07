# Habilita la evaluación diferida de anotaciones de tipos (PEP 563).
from __future__ import annotations

# Módulo estándar para generar UUIDs aleatorios (v4) y manejo de tipos.
import uuid
from uuid import uuid4
from typing import TYPE_CHECKING  # Exclusivo para análisis estático de linters e IDEs

# Tipos de datos de SQLAlchemy y dialecto específico de PostgreSQL.
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

# Clase base declarativa del proyecto.
from .base import Base

# --- IMPORTACIONES EXCLUSIVAS PARA LINTERS / TYPE CHECKING ---
# Reservado para cuando agregues referencias o relaciones explicitas (relationship)
# a modelos de entidades (ej. Entity).
if TYPE_CHECKING:
    pass


class Relationship(Base):
    """
    Modelo ORM que representa una relación o arista dirigida entre dos entidades en un Grafo.

    Conecta una entidad de origen (`source_entity_id`) con una entidad de destino (`target_entity_id`)
    mediante una etiqueta o tipo de vínculo (`relation`).
    """

    # Nombre explícito de la tabla en la base de datos PostgreSQL.
    __tablename__ = "relationships"

    # Identificador único de la relación (Clave Primaria UUIDv4).
    # - UUID(as_uuid=True): Fuerza a PostgreSQL a usar su tipo nativo UUID y lo convierte a uuid.UUID en Python.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Identificador único de la entidad que actúa como origen del enlace.
    # - nullable=False: Campo obligatorio en la base de datos.
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    # Identificador único de la entidad que actúa como destino del enlace.
    # - nullable=False: Campo obligatorio en la base de datos.
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    # Etiqueta o tipo de la relación semántica (ej. "PERTENECE_A", "TRABAJA_EN", "UBICADO_EN").
    relation: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
