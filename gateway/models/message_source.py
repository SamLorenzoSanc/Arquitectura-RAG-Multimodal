# Habilita la evaluación diferida de anotaciones de tipos (PEP 563).
from __future__ import annotations

# Módulo estándar de Python para el manejo de UUIDs.
import uuid
from typing import TYPE_CHECKING  # Exclusivo para análisis estático de código

# Tipos de columna y claves foráneas en SQLAlchemy.
from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Clase base declarativa del proyecto.
from .base import Base

# --- IMPORTACIONES EXCLUSIVAS PARA LINTERS / TYPE CHECKING ---
# Evita importaciones circulares en tiempo de ejecución mientras proporciona
# tipado estático completo a herramientas como Mypy o el autocompletado de VS Code.
if TYPE_CHECKING:
    from .document import Document
    from .message import Message


class MessageSource(Base):
    """
    Modelo ORM que almacena las fuentes o referencias de contexto utilizadas en un mensaje.

    Típicamente usado en sistemas RAG para rastrear de qué documento y fragmento (chunk)
    provino la información devuelta por el modelo LLM y con qué nivel de relevancia (similarity_score).
    """

    # Nombre de la tabla en PostgreSQL.
    __tablename__ = "message_sources"

    # Identificador único del registro de la fuente (Clave Primaria UUIDv4).
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Clave foránea referenciando al mensaje de la conversación al que pertenece esta fuente.
    # - ondelete="CASCADE": Si el mensaje se borra, sus registros de fuentes también se eliminan.
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE")
    )

    # Clave foránea opcional que apunta al documento original indexado del cual se extrajo la cita.
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id")
    )

    # Identificador del fragmento de texto o vector (chunk) almacenado en la base de datos vectorial (ej. ChromaDB).
    chunk_id: Mapped[str | None] = mapped_column(String(100))

    # Puntuación de similitud semántica (distancia coseno o producto punto)
    # devuelta por la búsqueda vectorial para medir qué tan relevante fue este contexto.
    similarity_score: Mapped[float | None] = mapped_column(Float)
