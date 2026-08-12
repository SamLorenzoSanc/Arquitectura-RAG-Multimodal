# Habilita la evaluación diferida de anotaciones de tipos (PEP 563).
from __future__ import annotations

# Módulos estándar para el manejo de UUIDs, fechas y verificación estática de tipos.
import uuid
from datetime import datetime
from typing import TYPE_CHECKING  # Exclusivo para análisis estático de linters e IDEs

# Tipos de columna y funciones SQL de SQLAlchemy.
from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

# Clase base declarativa del proyecto.
from .base import Base

# --- IMPORTACIONES EXCLUSIVAS PARA LINTERS / TYPE CHECKING ---
if TYPE_CHECKING:
    pass


class RevokedToken(Base):
    """
    Modelo ORM que gestiona la lista negra (denylist / blacklist) de tokens de acceso.

    Permite invalidar explícitamente tokens JWT o tokens de sesión antes de que expire
    su tiempo de vida natural (por ejemplo, cuando un usuario cierra sesión o se invalida
    una credencial por seguridad).
    """

    # Nombre de la tabla en la base de datos PostgreSQL.
    __tablename__ = "revoked_tokens"

    # Identificador único de la regla de revocación (Clave Primaria UUIDv4).
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Token revocado o su firma/hash completo en formato texto.
    # - Text: Permite almacenar JWTs extensos o firmas sin restricción de tamaño.
    # - nullable=False: Campo obligatorio.
    token: Mapped[str] = mapped_column(Text, nullable=False)

    # Marca de tiempo que indica cuándo expiraba originalmente el token.
    # Es fundamental para tareas de limpieza (cron jobs) que eliminan registros obsoletos.
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Fecha y hora exacta en que se registró la revocación en la base de datos (NOW()).
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()  # pylint: disable=not-callable
    )
