# Habilita la evaluación diferida de anotaciones de tipos (PEP 563),
# lo que permite referenciar tipos mediante cadenas o antes de su definición explícita.
from __future__ import annotations

# Importación de módulos para manejo de tipos estándar (UUID y datetime).
import uuid
from datetime import datetime
from typing import TYPE_CHECKING  # Para importaciones exclusivas de análisis estático

# Módulos de SQLAlchemy para la definición de columnas, restricciones y funciones del servidor SQL.
from sqlalchemy import String, Text, DateTime, ForeignKey, text, Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Clase base declarativa del proyecto.
from .base import Base

# --- IMPORTACIONES EXCLUSIVAS PARA LINTERS / TYPE CHECKING ---
# Este bloque se ejecuta ÚNICAMENTE durante la revisión estática de código (mypy, IDEs, linters).
# No se ejecuta durante la corrida normal de Python, evitando importaciones circulares.
if TYPE_CHECKING:
    from .conversation import Conversation
    from .document import Document
    from .knowledge_base_permission import KnowledgeBasePermission
    from .tenant import Tenant
    from .user import User


class KnowledgeBase(Base):
    """
    Modelo ORM que representa una Base de Conocimiento (Knowledge Base).

    Centraliza los documentos cargados, colecciones en bases de datos vectoriales (ChromaDB),
    las conversaciones asociadas y los permisos de acceso de los usuarios por organización (tenant).
    """

    # Nombre de la tabla física en la base de datos PostgreSQL.
    __tablename__ = "knowledge_bases"

    # Identificador único de la base de conocimiento (Clave Primaria).
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Clave foránea referenciando al Tenant (Organización o Cliente propietario).
    # - ondelete="CASCADE": Si el Tenant se elimina, esta base de conocimiento también se borra.
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )

    # Nombre identificativo de la base de conocimiento (máximo 200 caracteres).
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Descripción opcional o detallada de la base de conocimiento (tipo de texto largo).
    description: Mapped[str | None] = mapped_column(Text)

    use_case: Mapped[str | None] = mapped_column(String(80))

    # Identificador único de la colección en la base de datos vectorial Chroma (ChromaDB).
    # - unique=True: Garantiza que no existan dos bases de conocimiento apuntando a la misma colección.
    chroma_collection: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )

    # Clave foránea opcional que guarda el id del usuario creador.
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )

    # Fecha y hora de creación del registro.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
