# Habilita la evaluación pospuesta de anotaciones de tipo (PEP 563),
# permitiendo usar tipos que aún no han sido definidos en el archivo.
from __future__ import annotations

# Función de la librería estándar de Python para generar identificadores únicos universales (UUIDv4) aleatorios.
from uuid import uuid4

# Importación de tipos de SQLAlchemy: String (genérico) y dialecto específico de PostgreSQL para UUID.
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID

# Utilidades de SQLAlchemy 2.0 para la definición moderna de modelos ORM con anotaciones de tipo.
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

# Clase base declarativa del proyecto (normalmente proviene de DeclarativeBase).
from .base import Base


class GraphEdge(Base):
    """
    Modelo ORM que representa una arista/relación (Edge) en un grafo dentro de la base de datos.
    Conecta un nodo de origen (source_node_id) con un nodo de destino (target_node_id)
    mediante una relación nombrada (relation).
    """

    # Nombre explícito de la tabla en la base de datos PostgreSQL.
    __tablename__ = "graph_edges"

    # Identificador único de la arista (Clave Primaria).
    # - UUID(as_uuid=True): Indica a PostgreSQL que use su tipo nativo UUID y lo devuelva como objeto uuid.UUID de Python.
    # - default=uuid4: Genera automáticamente un nuevo UUIDv4 al insertar un nuevo registro si no se proporciona uno.
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Identificador del nodo de origen (origen de la arista).
    # - nullable=False: Campo obligatorio (no puede ser nulo en la base de datos).
    source_node_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    # Identificador del nodo de destino (destino de la arista).
    # - nullable=False: Campo obligatorio.
    target_node_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    # Tipo o nombre de la relación entre los nodos (ej. "PERTENECE_A", "SE_CONECTA_CON").
    # - String(255): Cadena de texto con un límite máximo de 255 caracteres.
    # - nullable=False: Campo obligatorio.
    relation: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
