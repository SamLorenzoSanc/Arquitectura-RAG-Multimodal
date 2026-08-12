# Habilita la evaluación diferida de anotaciones de tipos (PEP 563).
from __future__ import annotations

# Módulos para manejo de UUIDs y análisis estático de tipos.
import uuid
from typing import TYPE_CHECKING  # Exclusivo para análisis estático de linters / IDEs

# Tipos de columna, restricciones y claves foráneas de SQLAlchemy.
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Clase base declarativa del proyecto.
from .base import Base

# --- IMPORTACIONES EXCLUSIVAS PARA LINTERS / TYPE CHECKING ---
# Se ejecutan ÚNICAMENTE durante el análisis estático de código (mypy, pyright, VS Code).
# Evita importaciones circulares en tiempo de ejecución.
if TYPE_CHECKING:
    from .organization import Organization
    from .organization_member import OrganizationMember


class Role(Base):
    """
    Modelo ORM que gestiona los roles de usuario (ej. 'Administrador', 'Editor', 'Lector').

    Permite definir perfiles de permisos personalizados asignables a miembros dentro
    de una organización específica.
    """

    # Nombre de la tabla física en la base de datos PostgreSQL.
    __tablename__ = "roles"

    # Restricción a nivel de tabla: garantiza que no existan dos roles con el mismo nombre
    # dentro de una misma organización (el nombre de rol es único por organización).
    __table_args__ = (UniqueConstraint("organization_id", "name"),)

    # Identificador único del rol (Clave Primaria UUIDv4).
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Clave foránea opcional que vincula el rol a una organización específica.
    # - nullable=True: Permite roles globales del sistema si organización es None.
    # - ondelete="CASCADE": Si se elimina la organización, sus roles personalizados también se borran.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE")
    )

    # Nombre identificador del rol (máximo 100 caracteres, obligatorio).
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Descripción opcional sobre los permisos o el propósito de este rol.
    description: Mapped[str | None] = mapped_column(Text)
