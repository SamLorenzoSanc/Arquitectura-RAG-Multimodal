# Habilita la evaluación diferida de anotaciones de tipos (PEP 563).
from __future__ import annotations

# Módulos estándar para manejo de UUID, fechas y análisis estático de tipos.
import uuid
from datetime import datetime
from typing import TYPE_CHECKING  # Exclusivo para análisis estático de linters / IDEs

# Tipos de columna, restricciones y funciones SQL de SQLAlchemy.
from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Clase base declarativa del proyecto.
from .base import Base

# --- IMPORTACIONES EXCLUSIVAS PARA LINTERS / TYPE CHECKING ---
# Se ejecutan ÚNICAMENTE durante el análisis estático de código (mypy, pyright, VS Code).
# Evita importaciones circulares en tiempo de ejecución.
if TYPE_CHECKING:
    from .department import Department
    from .organization_member import OrganizationMember
    from .role import Role
    from .tenant import Tenant


class Organization(Base):
    """
    Modelo ORM que representa una Organización o Entidad Principal dentro del sistema.

    Actúa como el contenedor raíz para la estructura empresarial, agrupando departamentos,
    tenants (inquilinos/entornos aislados), roles personalizados y los miembros asociados.
    """

    # Nombre de la tabla física en la base de datos PostgreSQL.
    __tablename__ = "organizations"

    # Identificador único de la organización (Clave Primaria UUIDv4).
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Nombre oficial o comercial de la organización (máximo 200 caracteres, obligatorio).
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Descripción opcional o detallada sobre la organización.
    description: Mapped[str | None] = mapped_column(Text)

    # URL o representación en texto (ej. Base64) del logotipo de la organización.
    logo: Mapped[str | None] = mapped_column(Text)

    # Estado de la organización (activa/inactiva). Permite deshabilitar el acceso global.
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Marca de tiempo de creación registrada automáticamente por el servidor SQL (NOW()).
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()  # pylint: disable=not-callable
    )
