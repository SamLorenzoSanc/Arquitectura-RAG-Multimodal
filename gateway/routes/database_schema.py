from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.security import get_current_user, user_is_admin
from models.user import User
from services.database import get_db

router = APIRouter(prefix="/database", tags=["Database"])

async def require_database_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Limita la introspección del esquema a administradores activos."""
    if not await user_is_admin(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden consultar el esquema de PostgreSQL.",
        )
    return current_user


@router.get("/schema")
async def get_database_schema(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_database_admin),
):
    """Devuelve metadatos del esquema actual sin exponer datos de las tablas."""
    table_rows = (
        (
            await db.execute(
                text(
                    """
                    SELECT
                        namespace.nspname AS schema_name,
                        relation.relname AS table_name,
                        relation.reltuples::bigint AS estimated_rows,
                        pg_total_relation_size(relation.oid)::bigint AS total_bytes
                    FROM pg_class AS relation
                    JOIN pg_namespace AS namespace
                      ON namespace.oid = relation.relnamespace
                    WHERE relation.relkind IN ('r', 'p')
                      AND namespace.nspname NOT IN (
                          'pg_catalog', 'information_schema'
                      )
                      AND namespace.nspname NOT LIKE 'pg_toast%'
                    ORDER BY namespace.nspname, relation.relname
                    """
                )
            )
        )
        .mappings()
        .all()
    )

    column_rows = (
        (
            await db.execute(
                text(
                    """
                    SELECT
                        column_info.table_schema AS schema_name,
                        column_info.table_name,
                        column_info.column_name,
                        column_info.data_type,
                        column_info.udt_name,
                        column_info.is_nullable = 'YES' AS nullable,
                        column_info.column_default,
                        column_info.ordinal_position,
                        EXISTS (
                            SELECT 1
                            FROM information_schema.table_constraints AS constraint_info
                            JOIN information_schema.key_column_usage AS key_info
                              ON constraint_info.constraint_name = key_info.constraint_name
                             AND constraint_info.constraint_schema = key_info.constraint_schema
                            WHERE constraint_info.constraint_type = 'PRIMARY KEY'
                              AND key_info.table_schema = column_info.table_schema
                              AND key_info.table_name = column_info.table_name
                              AND key_info.column_name = column_info.column_name
                        ) AS primary_key
                    FROM information_schema.columns AS column_info
                    WHERE column_info.table_schema NOT IN (
                        'pg_catalog', 'information_schema'
                    )
                    ORDER BY
                        column_info.table_schema,
                        column_info.table_name,
                        column_info.ordinal_position
                    """
                )
            )
        )
        .mappings()
        .all()
    )

    relation_rows = (
        (
            await db.execute(
                text(
                    """
                    SELECT
                        source_usage.constraint_name,
                        source_usage.table_schema AS source_schema,
                        source_usage.table_name AS source_table,
                        source_usage.column_name AS source_column,
                        target_usage.table_schema AS target_schema,
                        target_usage.table_name AS target_table,
                        target_usage.column_name AS target_column
                    FROM information_schema.table_constraints AS constraint_info
                    JOIN information_schema.key_column_usage AS source_usage
                      ON constraint_info.constraint_name = source_usage.constraint_name
                     AND constraint_info.constraint_schema = source_usage.constraint_schema
                    JOIN information_schema.constraint_column_usage AS target_usage
                      ON constraint_info.constraint_name = target_usage.constraint_name
                     AND constraint_info.constraint_schema = target_usage.constraint_schema
                    WHERE constraint_info.constraint_type = 'FOREIGN KEY'
                    ORDER BY
                        source_usage.table_schema,
                        source_usage.table_name,
                        source_usage.ordinal_position
                    """
                )
            )
        )
        .mappings()
        .all()
    )

    index_rows = (
        (
            await db.execute(
                text(
                    """
                    SELECT schemaname AS schema_name, tablename AS table_name,
                           indexname AS index_name, indexdef AS definition
                    FROM pg_indexes
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY schemaname, tablename, indexname
                    """
                )
            )
        )
        .mappings()
        .all()
    )

    tables_by_id = {}
    for row in table_rows:
        table_id = f"{row['schema_name']}.{row['table_name']}"
        tables_by_id[table_id] = {
            "id": table_id,
            "schema": row["schema_name"],
            "name": row["table_name"],
            "estimated_rows": max(row["estimated_rows"] or 0, 0),
            "total_bytes": row["total_bytes"] or 0,
            "columns": [],
            "indexes": [],
        }

    for row in column_rows:
        table = tables_by_id.get(f"{row['schema_name']}.{row['table_name']}")
        if table is not None:
            table["columns"].append(
                {
                    "name": row["column_name"],
                    "data_type": row["data_type"],
                    "database_type": row["udt_name"],
                    "nullable": bool(row["nullable"]),
                    "default": row["column_default"],
                    "primary_key": bool(row["primary_key"]),
                    "position": row["ordinal_position"],
                }
            )

    for row in index_rows:
        table = tables_by_id.get(f"{row['schema_name']}.{row['table_name']}")
        if table is not None:
            table["indexes"].append(
                {
                    "name": row["index_name"],
                    "definition": row["definition"],
                }
            )

    relations = [
        {
            "name": row["constraint_name"],
            "source_table": f"{row['source_schema']}.{row['source_table']}",
            "source_column": row["source_column"],
            "target_table": f"{row['target_schema']}.{row['target_table']}",
            "target_column": row["target_column"],
        }
        for row in relation_rows
    ]

    return {
        "database": await db.scalar(text("SELECT current_database()")),
        "postgres_version": await db.scalar(text("SHOW server_version")),
        "tables": list(tables_by_id.values()),
        "relations": relations,
    }
