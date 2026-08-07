"""Módulo de configuración base para el ORM de SQLAlchemy.

Este módulo define la clase base declarativa de la cual heredarán todos los
modelos de la base de datos, centralizando el registro de metadatos del proyecto.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa compartida por todos los modelos de la aplicación.

    Actúa como el registro central (`registry`) y contenedor de metadatos
    (`metadata`) de SQLAlchemy. Cada modelo del sistema que herede de esta clase
    será mapeado automáticamente a su respectiva tabla en la base de datos.
    """

    pass
