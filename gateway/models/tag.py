# Habilita la evaluación diferida de anotaciones de tipos (PEP 563).
from __future__ import annotations

# Módulos para manejo de UUIDs y análisis estático de tipos.
import uuid
from typing import TYPE_CHECKING  # Exclusivo para análisis estático de linters / IDEs

# Tipos de columna de SQLAlchemy.
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Tabla intermedia de asociación y clase base declarativa del proyecto.
from .associations import document_tags
from .base import Base

# --- IMPORTACIONES EXCLUSIVAS PARA LINTERS / TYPE CHECKING ---
# Se ejecutan ÚNICAMENTE durante el análisis estático de código (mypy, pyright, VS Code).
# Evita importaciones circulares en tiempo de ejecución.
if TYPE_CHECKING:
    from .document import Document


class Tag(Base):
    """
    Modelo ORM que representa una etiqueta (Tag) para categorización de contenidos.

    Permite clasificar y agrupar documentos mediante una relación muchos-a-muchos (N:M)
    gestionada a través de la tabla de asociación `document_tags`.
    """

    # Nombre de la tabla física en la base de datos PostgreSQL.
    __tablename__ = "tags"

    # Identificador único de la etiqueta (Clave Primaria UUIDv4).
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Nombre único identificativo de la etiqueta (máximo 100 caracteres, obligatorio).
    # - unique=True: Evita que existan etiquetas duplicadas en la base de datos.
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
