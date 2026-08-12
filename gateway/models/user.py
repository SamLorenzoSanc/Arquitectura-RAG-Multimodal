# Habilita la evaluación diferida de anotaciones de tipos (PEP 563).
from __future__ import annotations

# Módulos para manejo de UUIDs, fechas y tipado estático.
import uuid
from datetime import datetime
from typing import TYPE_CHECKING  # Exclusivo para análisis estático de linters / IDEs

# Tipos de columna y funciones SQL de SQLAlchemy.
from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Clase base declarativa del proyecto.
from .base import Base

# --- IMPORTACIONES EXCLUSIVAS PARA LINTERS / TYPE CHECKING ---
# Se ejecutan ÚNICAMENTE durante el análisis estático de código (mypy, pyright, VS Code).
# Evita importaciones circulares en tiempo de ejecución.
if TYPE_CHECKING:
    from .conversation import Conversation
    from .document import Document
    from .document_version import DocumentVersion
    from .knowledge_base import KnowledgeBase
    from .organization_member import OrganizationMember


class User(Base):
    """
    Modelo ORM que representa a un Usuario dentro del sistema.

    Almacena la identidad del usuario, sus credenciales autenticadas y actúa
    como actor principal en la creación de documentos, bases de conocimiento,
    versiones, conversaciones, registros de API y membresías en organizaciones.
    """

    # Nombre de la tabla física en la base de datos PostgreSQL.
    __tablename__ = "users"

    # Identificador único del usuario (Clave Primaria UUIDv4).
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Nombre completo o de pantalla del usuario (máximo 100 caracteres, obligatorio).
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Correo electrónico de inicio de sesión (máximo 255 caracteres, obligatorio).
    # - unique=True: Impide el registro de múltiples cuentas con la misma dirección email.
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Hash seguro de la contraseña (ej. Argon2, bcrypt, PBKDF2).
    # - Text: Permite almacenar hashes extensos de forma segura sin truncamiento.
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)

    # Flag booleano para activar o desactivar la cuenta del usuario (por defecto True).
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Fecha y hora de creación del registro generada por el servidor SQL (NOW()).
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()  # pylint: disable=not-callable
    )

    # Fecha y hora de la última modificación (se actualiza automáticamente en cada UPDATE).
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),  # pylint: disable=not-callable
        onupdate=func.now(),  # pylint: disable=not-callable
    )
