# Habilita la evaluación diferida de anotaciones de tipos (PEP 563).
from __future__ import annotations

# Módulos para manejo de UUIDs, fechas y verificación estática de tipos.
import uuid
from datetime import datetime
from typing import TYPE_CHECKING  # Exclusivo para análisis estático de linters e IDEs

# Tipos de columna y claves foráneas de SQLAlchemy.
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Clase base declarativa del proyecto.
from .base import Base

# --- IMPORTACIONES EXCLUSIVAS PARA LINTERS / TYPE CHECKING ---
# Se ejecutan ÚNICAMENTE durante la revisión estática de código (mypy, pyright, VS Code).
# Evita importaciones circulares en tiempo de ejecución.
if TYPE_CHECKING:
    from .document import Document
    from .tenant import Tenant


class ProcessingJob(Base):
    """
    Modelo ORM que monitorea las tareas de procesamiento de documentos (ETL / Ingestión RAG).

    Registra el ciclo de vida del procesamiento (pendiente, en progreso, completado, fallido),
    marcas de tiempo de inicio y fin, errores encontrados, número de chunks generados
    y los modelos de IA involucrados.
    """

    # Nombre de la tabla en la base de datos PostgreSQL.
    __tablename__ = "processing_jobs"

    # Identificador único del trabajo de procesamiento (Clave Primaria UUIDv4).
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Clave foránea opcional que vincula el trabajo con una organización o tenant.
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id")
    )

    # Clave foránea que apunta al documento original que se está procesando.
    # - ondelete="CASCADE": Si el documento es eliminado, su historial de procesamiento también se elimina.
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE")
    )

    # Estado actual de la tarea (ej. 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED').
    status: Mapped[str] = mapped_column(String(20), nullable=False)

    # Marca de tiempo con zona horaria de cuándo comenzó a ejecutarse la tarea.
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Marca de tiempo con zona horaria de cuándo finalizó la tarea (con éxito o error).
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Detalle de la traza de error o mensaje de fallo si el estado pasa a 'FAILED'.
    error_message: Mapped[str | None] = mapped_column(Text)

    # Contador de fragmentos de texto (chunks) generados e insertados en la base de datos vectorial.
    chunks_generated: Mapped[int] = mapped_column(Integer, default=0)

    # Nombre o versión del modelo de embeddings utilizado (ej. "text-embedding-3-small", "bge-m3").
    embedding_model: Mapped[str | None] = mapped_column(String(100))

    # Nombre o versión del modelo LLM utilizado durante el procesamiento si aplica (ej. "gpt-4o-mini").
    llm_model: Mapped[str | None] = mapped_column(String(100))
