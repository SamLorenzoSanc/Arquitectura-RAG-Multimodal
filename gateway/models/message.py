# Habilita la evaluación diferida de anotaciones de tipos (PEP 563).
from __future__ import annotations

# Módulos para manejo de UUIDs y marcas de tiempo (datetime).
import uuid
from datetime import datetime
from typing import TYPE_CHECKING  # Exclusivo para análisis estático de código

# Tipos de columna, restricciones y funciones SQL en SQLAlchemy.
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Clase base declarativa del proyecto.
from .base import Base

# --- IMPORTACIONES EXCLUSIVAS PARA LINTERS / TYPE CHECKING ---
# Evita importaciones circulares en tiempo de ejecución mientras habilita
# autocompletado y validación estática en Mypy / Pyright / VS Code.
if TYPE_CHECKING:
    from .conversation import Conversation
    from .message_source import MessageSource


class Message(Base):
    """
    Modelo ORM que representa un mensaje individual dentro de una conversación.

    Registra el rol del emisor (ej. 'user', 'assistant', 'system'), el contenido del texto,
    el conteo de tokens de la llamada al LLM y la relación con las fuentes RAG utilizadas.
    """

    # Nombre de la tabla en la base de datos PostgreSQL.
    __tablename__ = "messages"

    # Identificador único del mensaje (Clave Primaria UUIDv4).
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Clave foránea que vincula el mensaje con su conversación contenedora.
    # - ondelete="CASCADE": Si se borra la conversación, sus mensajes se eliminan automáticamente.
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE")
    )

    # Rol del emisor en la interacción con el LLM (ej. "user", "assistant", "system").
    role: Mapped[str] = mapped_column(String(20), nullable=False)

    # Contenido de texto del mensaje. Tipo Text para soportar respuestas extensas.
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Número de tokens del prompt de entrada consumidos en la API del LLM.
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)

    # Número de tokens de la respuesta generada por el LLM.
    completion_tokens: Mapped[int | None] = mapped_column(Integer)

    # Fecha y hora de creación generada automáticamente por el servidor SQL (NOW()).
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
