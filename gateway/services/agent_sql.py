"""SQL de solo lectura para el agente: SELECT acotado al tenant.

No es un text-to-SQL libre. El modelo propone un SELECT; aquí se valida
tabla, verbo y ámbito antes de ejecutarlo.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

ALLOWED_TABLES = frozenset(
    {
        "documents",
        "chunks",
        "knowledge_bases",
        "conversations",
        "messages",
        "field_notebook_entries",
    }
)
ALLOWED_BINDS = frozenset(
    {"tenant_id", "user_id", "organization_id", "conversation_id"}
)
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|grant|revoke|copy|"
    r"truncate|vacuum|comment|do|call|execute|prepare|set|into|"
    r"returning|pg_|information_schema|dblink|lo_|session_user|"
    r"current_user|current_setting)\b",
    re.I,
)
FROM_JOIN = re.compile(r"\b(?:from|join)\s+([a-zA-Z_][\w.]*)", re.I)
LIMIT_RE = re.compile(r"\blimit\s+(\d+)\b", re.I)
BIND_RE = re.compile(r"(?<!:):([a-zA-Z_][\w]*)")
SCOPED_TABLES = frozenset(
    {"documents", "knowledge_bases", "conversations", "chunks", "messages"}
)


class AgentSqlError(ValueError):
    pass


def _tables(sql: str) -> set[str]:
    found: set[str] = set()
    for raw in FROM_JOIN.findall(sql):
        found.add(raw.split(".")[-1].lower())
    return found


def validate_agent_select(sql: str) -> str:
    cleaned = (sql or "").strip().rstrip(";").strip()
    if not cleaned:
        raise AgentSqlError("La consulta SQL está vacía.")
    if ";" in cleaned:
        raise AgentSqlError("Solo se admite una sentencia.")
    if not re.match(r"^\s*select\b", cleaned, re.I):
        raise AgentSqlError("Solo se permiten consultas SELECT.")
    if FORBIDDEN.search(cleaned):
        raise AgentSqlError("La consulta usa una operación o catálogo no permitido.")
    tables = _tables(cleaned)
    if not tables:
        raise AgentSqlError("No se reconoció ninguna tabla en el FROM/JOIN.")
    unknown = tables - ALLOWED_TABLES
    if unknown:
        raise AgentSqlError(f"Tabla no permitida: {', '.join(sorted(unknown))}.")
    if "chunks" in tables and "documents" not in tables:
        raise AgentSqlError("chunks debe ir con JOIN documents para filtrar el tenant.")
    if "messages" in tables and "conversations" not in tables:
        raise AgentSqlError(
            "messages debe ir con JOIN conversations para filtrar el tenant."
        )
    if tables & SCOPED_TABLES and ":tenant_id" not in cleaned:
        raise AgentSqlError("La consulta debe filtrar con :tenant_id.")
    if "field_notebook_entries" in tables and not (
        ":user_id" in cleaned or ":organization_id" in cleaned
    ):
        raise AgentSqlError(
            "El cuaderno debe filtrar con :user_id o :organization_id."
        )
    binds = set(BIND_RE.findall(cleaned))
    extra = binds - ALLOWED_BINDS
    if extra:
        raise AgentSqlError(f"Parámetro no permitido: {', '.join(sorted(extra))}.")
    if LIMIT_RE.search(cleaned):
        cleaned = LIMIT_RE.sub(
            lambda match: f"LIMIT {min(int(match.group(1)), 50)}", cleaned
        )
    else:
        cleaned = f"{cleaned} LIMIT 25"
    return cleaned


def sql_schema_card() -> str:
    return """Tablas permitidas (solo SELECT). Usa los binds :tenant_id, :user_id,
:organization_id, :conversation_id. Nunca escribas literales de UUID.

documents(id, tenant_id, knowledge_base_id, filename, title, description, mime_type, uploaded_at)
knowledge_bases(id, tenant_id, name, description)
chunks(id, document_id, content, headline, position) — JOIN documents d ON d.id = chunks.document_id WHERE d.tenant_id = :tenant_id
conversations(id, tenant_id, user_id, title, created_at)
messages(id, conversation_id, role, content, created_at) — JOIN conversations c ON c.id = messages.conversation_id WHERE c.tenant_id = :tenant_id AND c.user_id = :user_id
field_notebook_entries(id, user_id, organization_id, entry_date, title, body, category)
"""


def format_sql_rows(rows: list[dict[str, Any]], limit: int = 25) -> str:
    if not rows:
        return "La consulta no devolvió filas."
    lines = []
    for index, row in enumerate(rows[:limit], start=1):
        parts = []
        for key, value in row.items():
            text_value = "" if value is None else str(value)
            if len(text_value) > 180:
                text_value = text_value[:180].rstrip() + "…"
            parts.append(f"{key}={text_value}")
        lines.append(f"{index}. " + " · ".join(parts))
    return "\n".join(lines)


async def execute_agent_select(
    db: AsyncSession,
    sql: str,
    *,
    tenant_id: str,
    user_id: str | None = None,
    organization_id: str | None = None,
    conversation_id: str | None = None,
) -> list[dict[str, Any]]:
    cleaned = validate_agent_select(sql)
    params = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "organization_id": organization_id,
        "conversation_id": conversation_id,
    }
    used = {key: value for key, value in params.items() if f":{key}" in cleaned}
    try:
        await db.execute(text("SET LOCAL statement_timeout = '3000'"))
    except Exception:
        pass
    result = await db.execute(text(cleaned), used)
    return [dict(row) for row in result.mappings().all()]
