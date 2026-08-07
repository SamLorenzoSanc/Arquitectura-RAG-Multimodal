# Habilita la evaluación diferida de anotaciones de tipos (PEP 563).
from __future__ import annotations

# Módulos estándar para manejo de UUID, fechas y tipado estático.
import uuid
from datetime import datetime
from typing import TYPE_CHECKING  # Exclusivo para análisis estático de linters / IDEs

# Tipos de columna, restricciones y funciones SQL de SQLAlchemy.
from sqlalchemy import Boolean, DateTime, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Clase base declarativa del proyecto.
from .base import Base

# --- IMPORTACIONES EXCLUSIVAS PARA LINTERS / TYPE CHECKING ---
# Se ejecutan ÚNICAMENTE durante la revisión estática de código (mypy, IDEs).
# Evitan importaciones circulares en tiempo de ejecución.
if TYPE_CHECKING:
    from .department import Department
    from .knowledge_base_permission import KnowledgeBasePermission
    from .organization import Organization
    from .role import Role
    from .user import User


class OrganizationMember(Base):
    """
    Modelo ORM que gestiona la membresía o pertenencia de un usuario dentro de una organización.

    Permite definir qué rol desempeña el usuario, a qué departamento pertenece,
    si su estado está activo dentro de la organización y sus permisos específicos sobre bases de conocimiento.
    """

    # Nombre de la tabla en la base de datos PostgreSQL.
    __tablename__ = "organization_members"

    # Restricción a nivel de tabla: garantiza que un usuario no pueda ser registrado
    # más de una vez dentro de la misma organización.
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)

    # Identificador único del registro de membresía (Clave Primaria UUIDv4).
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Clave foránea vinculada a la organización correspondiente.
    # - ondelete="CASCADE": Si la organización es eliminada, la membresía se borra automáticamente.
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Clave foránea vinculada al usuario.
    # - ondelete="CASCADE": Si el usuario es eliminado de la plataforma, la membresía se elimina automáticamente.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Clave foránea opcional que asigna un departamento específico al miembro.
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id")
    )

    # Clave foránea opcional que asigna un rol de acceso (ej. 'Admin', 'Editor', 'Viewer').
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id")
    )

    # Flag booleano para activar/desactivar el acceso del miembro a la organización (por defecto True).
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Fecha y hora en la que el usuario fue agregado a la organización (servidor SQL: NOW()).
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
