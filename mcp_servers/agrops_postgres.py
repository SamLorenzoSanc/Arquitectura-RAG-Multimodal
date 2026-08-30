"""Servidor MCP stdio: PostgreSQL/pgvector de AgroPS en solo lectura."""

from __future__ import annotations

import json
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

MAX_ROWS = 50
STATEMENT_TIMEOUT_MS = 8_000

_COMMENT_LINE = re.compile(r"--[^\n]*")
_COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)
_STRING_LITERAL = re.compile(r"'(?:''|[^'])*'|\$\$.*?\$\$", re.DOTALL)
_IDENT = re.compile(r"\b([A-Za-z_][\w$]*)\b")
_SELECT_STAR_EMBEDDINGS = re.compile(
    r"\bselect\s+(?:[\w.]+\s*,\s*)*\*\s+from\s+(?:[\w.]+\s*,\s*)*embeddings\b"
    r"|\bfrom\s+embeddings\b[\s\S]*\bselect\s+\*",
    re.IGNORECASE,
)
_FROM_EMBEDDINGS = re.compile(
    r"\b(?:from|join)\s+(?:public\.)?embeddings\b",
    re.IGNORECASE,
)
_STAR = re.compile(r"(?<![\w.])\*(?!\s*\))", re.IGNORECASE)
_VECTOR_DIMS = re.compile(r"\bvector_dims\s*\(", re.IGNORECASE)
_VECTOR_COL = re.compile(
    r"(?<!vector_dims\()(?:(?<=[\s,(])|(?<=^))(?:[\w]+\.)?vector(?=\s*(?:,|$|\s+as\s|\s+from\s|\s*\)))",
    re.IGNORECASE,
)
_FORBIDDEN = re.compile(
    r"\b("
    r"insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|"
    r"vacuum|reindex|cluster|comment|merge|call|prepare|deallocate|discard|"
    r"listen|notify|unlisten|lock|load|refresh|do|"
    r"set\s+role|set\s+session|reset\s+role|security\s+label"
    r")\b",
    re.IGNORECASE,
)
_ALLOWED_HEAD = re.compile(r"^(select|with|explain|show)\b", re.IGNORECASE)
_WITH_WRITE = re.compile(
    r"\)\s*(insert|update|delete|merge)\b",
    re.IGNORECASE,
)


class SqlGuardError(ValueError):
    """SQL rechazado por la política de solo lectura."""


def strip_sql_comments(sql: str) -> str:
    cleaned = _COMMENT_BLOCK.sub(" ", sql or "")
    cleaned = _COMMENT_LINE.sub(" ", cleaned)
    return cleaned.strip()


def _first_keyword(sql: str) -> str:
    match = _IDENT.search(sql)
    return (match.group(1) if match else "").lower()


def validate_readonly_sql(sql: str) -> str:
    """Normaliza y valida una sentencia de solo lectura.

    Devuelve el SQL limpio (sin comentarios, sin `;` final) listo para ejecutar.
    """
    if not sql or not str(sql).strip():
        raise SqlGuardError("La consulta está vacía.")

    cleaned = strip_sql_comments(str(sql))
    if not cleaned:
        raise SqlGuardError("La consulta está vacía.")

    statements = [part.strip() for part in cleaned.split(";") if part.strip()]
    if len(statements) != 1:
        raise SqlGuardError("Solo se admite una sentencia SQL.")
    statement = statements[0]

    if not _ALLOWED_HEAD.match(statement):
        raise SqlGuardError(
            "Solo se permiten SELECT, WITH (lectura), EXPLAIN o SHOW."
        )

    structural = _STRING_LITERAL.sub("''", statement)
    forbidden = _FORBIDDEN.search(structural)
    if forbidden:
        raise SqlGuardError(
            f"Operación no permitida en modo solo lectura: {forbidden.group(1).upper()}."
        )

    if _first_keyword(statement) == "with" and _WITH_WRITE.search(structural):
        raise SqlGuardError("WITH de escritura no está permitido.")

    if _would_dump_embedding_vector(structural):
        raise SqlGuardError(
            "No se puede devolver embeddings.vector (4096 dims). "
            "Usa vector_dims(vector) o omite la columna."
        )

    return statement


def _would_dump_embedding_vector(sql: str) -> bool:
    if _VECTOR_DIMS.search(sql) and not _VECTOR_COL.search(
        _VECTOR_DIMS.sub(" ", sql)
    ):
        # Solo aparece dentro de vector_dims(...)
        if not (_FROM_EMBEDDINGS.search(sql) and _STAR.search(sql)):
            return False

    if _VECTOR_COL.search(sql):
        return True

    if _FROM_EMBEDDINGS.search(sql) and _STAR.search(sql):
        return True

    if _SELECT_STAR_EMBEDDINGS.search(sql):
        return True

    return False


def sanitize_cell(value, *, max_list: int = 16):
    """Oculta vectores que se hayan colado en el resultado."""
    if isinstance(value, (list, tuple)):
        if value and all(isinstance(item, (int, float)) for item in value):
            if len(value) > max_list:
                return f"[vector dim={len(value)} omitido]"
        if len(value) > MAX_ROWS:
            return list(value[:MAX_ROWS]) + [f"… +{len(value) - MAX_ROWS} items"]
        return [sanitize_cell(item) for item in value]
    if isinstance(value, memoryview):
        return f"[bytea {len(value)} bytes omitidos]"
    if isinstance(value, (bytes, bytearray)):
        return f"[bytea {len(value)} bytes omitidos]"
    if isinstance(value, str) and len(value) > 1_200:
        return value[:1_200] + "…"
    return value


def sanitize_row(row: dict) -> dict:
    out = {}
    for key, value in row.items():
        if str(key).lower() in {"vector", "embedding", "embeddings"}:
            if isinstance(value, (list, tuple)):
                out[key] = f"[vector dim={len(value)} omitido]"
            else:
                out[key] = "[vector omitido]"
            continue
        out[key] = sanitize_cell(value)
    return out


sys.path.insert(0, str(Path(__file__).resolve().parent))

import psycopg
from mcp.server.fastmcp import FastMCP
from psycopg.rows import dict_row


mcp = FastMCP(
    "agrops-postgres",
    instructions=(
        "Consulta de solo lectura sobre el Postgres de AgroPS (chunks, documentos, "
        "estado de indexación). Nunca pide ni devuelve embeddings.vector. "
        "corpus_stats usa estimaciones de pg_class (reltuples), no COUNT(*) sobre vectores."
    ),
)

_HOST_REWRITE = re.compile(r"@postgres(?=[:/])")
_LOCK = threading.Lock()
_CONN: psycopg.Connection | None = None

# Una sola ida a pg_catalog + agregados baratos. Evita COUNT(*) sobre embeddings.vector.
CORPUS_STATS_SQL = """
SELECT
  (SELECT GREATEST(reltuples, 0)::bigint
     FROM pg_class WHERE oid = to_regclass('public.documents')) AS documents,
  (SELECT GREATEST(reltuples, 0)::bigint
     FROM pg_class WHERE oid = to_regclass('public.chunks')) AS chunks,
  (SELECT GREATEST(reltuples, 0)::bigint
     FROM pg_class WHERE oid = to_regclass('public.embeddings')) AS embeddings,
  (SELECT GREATEST(reltuples, 0)::bigint
     FROM pg_class WHERE oid = to_regclass('public.embedding_index_state')) AS index_state_rows,
  (
    SELECT COALESCE(
      json_agg(json_build_object('status', status, 'n', n) ORDER BY status),
      '[]'::json
    )
    FROM (
      SELECT status, COUNT(*)::int AS n
      FROM embedding_index_state
      GROUP BY status
    ) states
  ) AS index_states,
  (
    SELECT COALESCE(
      json_agg(
        json_build_object(
          'slug', slug,
          'runtime_model_id', runtime_model_id,
          'dimensions', dimensions,
          'status', status
        )
        ORDER BY slug
      ),
      '[]'::json
    )
    FROM embedding_model
  ) AS embedding_models
"""

LIST_TABLES_SQL = """
SELECT
  n.nspname AS table_schema,
  c.relname AS table_name,
  CASE c.relkind
    WHEN 'r' THEN 'BASE TABLE'
    WHEN 'p' THEN 'PARTITIONED TABLE'
    WHEN 'v' THEN 'VIEW'
    WHEN 'm' THEN 'MATERIALIZED VIEW'
    ELSE c.relkind::text
  END AS table_type,
  GREATEST(c.reltuples, 0)::bigint AS estimated_rows
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = %s
  AND c.relkind IN ('r', 'p', 'v', 'm')
  AND NOT c.relisrowsecurity
ORDER BY 3, 2
"""

DESCRIBE_TABLE_SQL = """
SELECT
  a.attname AS column_name,
  pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
  t.typname AS udt_name,
  NOT a.attnotnull AS is_nullable
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_type t ON t.oid = a.atttypid
WHERE n.nspname = %s
  AND c.relname = %s
  AND a.attnum > 0
  AND NOT a.attisdropped
ORDER BY a.attnum
"""


def _dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def rewrite_dsn(raw: str) -> str:
    """Convierte DSN de Compose/SQLAlchemy en uno usable desde el host."""
    dsn = (raw or "").strip()
    for prefix in (
        "postgresql+asyncpg://",
        "postgresql+psycopg2://",
        "postgresql+psycopg://",
    ):
        if dsn.startswith(prefix):
            dsn = "postgresql://" + dsn[len(prefix) :]
            break
    dsn = _HOST_REWRITE.sub("@localhost", dsn)
    parsed = urlparse(dsn)
    if parsed.hostname == "postgres":
        dsn = urlunparse(parsed._replace(netloc=_localhost_netloc(parsed)))
    return dsn


def database_dsn() -> str:
    """DSN alcanzable desde el host de Cursor (no el hostname Docker `postgres`)."""
    raw = (
        os.environ.get("MCP_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or ""
    ).strip()
    if raw:
        return rewrite_dsn(raw)

    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    db = os.environ.get("POSTGRES_DB", "agrops")
    host = os.environ.get("MCP_PG_HOST", "localhost")
    port = os.environ.get("MCP_PG_PORT", "5432")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def _localhost_netloc(parsed) -> str:
    port = f":{parsed.port}" if parsed.port else ""
    auth = ""
    if parsed.username:
        auth = parsed.username
        if parsed.password is not None:
            auth += f":{parsed.password}"
        auth += "@"
    return f"{auth}localhost{port}"


def _connection() -> psycopg.Connection:
    """Reutiliza una conexión de solo lectura durante la vida del proceso MCP."""
    global _CONN
    with _LOCK:
        if _CONN is None or _CONN.closed:
            _CONN = psycopg.connect(
                database_dsn(),
                connect_timeout=8,
                row_factory=dict_row,
                autocommit=True,
                options=(
                    "-c default_transaction_read_only=on "
                    f"-c statement_timeout={int(STATEMENT_TIMEOUT_MS)}"
                ),
            )
        assert _CONN is not None
        return _CONN


def _reset_connection() -> None:
    global _CONN
    with _LOCK:
        if _CONN is not None:
            try:
                _CONN.close()
            except psycopg.Error:
                pass
            _CONN = None


def _execute(
    sql: str,
    params: tuple | dict | None = None,
    *,
    limit: int = MAX_ROWS,
    isolated: bool = True,
):
    cleaned = validate_readonly_sql(sql)
    try:
        conn = _connection()
        with conn.cursor() as cur:
            if isolated:
                cur.execute("BEGIN READ ONLY")
            try:
                if params is None:
                    cur.execute(cleaned)
                else:
                    cur.execute(cleaned, params)
                if cur.description is None:
                    if isolated:
                        cur.execute("ROLLBACK")
                    return {"rows": [], "row_count": 0, "columns": [], "truncated": False}
                columns = [col.name for col in cur.description]
                fetched = cur.fetchmany(limit + 1)
                truncated = len(fetched) > limit
                rows = [sanitize_row(dict(row)) for row in fetched[:limit]]
                if isolated:
                    cur.execute("ROLLBACK")
                result: dict[str, Any] = {
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "truncated": truncated,
                }
                if truncated:
                    result["note"] = f"Resultado recortado a {limit} filas."
                return result
            except Exception:
                if isolated:
                    try:
                        cur.execute("ROLLBACK")
                    except psycopg.Error:
                        pass
                raise
    except psycopg.Error:
        _reset_connection()
        raise


@mcp.tool()
def list_tables(schema: str = "public") -> str:
    """Lista tablas/vistas de un esquema con filas estimadas (pg_class, sin information_schema)."""
    payload = _execute(LIST_TABLES_SQL, (schema,), limit=200, isolated=False)
    return _dumps(payload)


@mcp.tool()
def describe_table(table: str, schema: str = "public") -> str:
    """Columnas y tipos desde pg_catalog (más rápido que information_schema)."""
    payload = _execute(DESCRIBE_TABLE_SQL, (schema, table), limit=200, isolated=False)
    return _dumps(payload)


@mcp.tool()
def corpus_stats() -> str:
    """Resumen del corpus RAG en una sola consulta.

    documents/chunks/embeddings salen de pg_class.reltuples (estimación de ANALYZE),
    no de COUNT(*) sobre la columna vector. Los estados de índice sí se cuentan
    en caliente (tabla pequeña, índice por status).
    """
    try:
        payload = _execute(CORPUS_STATS_SQL, limit=1, isolated=False)
        row = (payload.get("rows") or [{}])[0]
        return _dumps(
            {
                "counts_are_estimates": True,
                "documents": row.get("documents"),
                "chunks": row.get("chunks"),
                "embeddings": row.get("embeddings"),
                "index_state_rows": row.get("index_state_rows"),
                "index_states": row.get("index_states") or [],
                "embedding_models": row.get("embedding_models") or [],
            }
        )
    except Exception as exc:
        return _dumps({"error": str(exc)})


@mcp.tool()
def execute_readonly_sql(sql: str) -> str:
    """Ejecuta una sentencia SELECT/WITH/EXPLAIN/SHOW en transacción READ ONLY.

    Máximo 50 filas. Prohibido devolver embeddings.vector.
    """
    try:
        return _dumps(_execute(sql, isolated=True))
    except SqlGuardError as exc:
        return _dumps({"error": str(exc)})
    except psycopg.Error as exc:
        return _dumps({"error": f"PostgreSQL: {exc}"})


if __name__ == "__main__":
    mcp.run(transport="stdio")
