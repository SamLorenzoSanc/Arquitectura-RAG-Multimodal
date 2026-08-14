from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from models.tenant import Tenant


def is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except (TypeError, ValueError):
        return False


def organization_tenant_ids(tenant_id):
    org_id = (
        select(Tenant.organization_id).where(Tenant.id == tenant_id).scalar_subquery()
    )
    return select(Tenant.id).where(Tenant.organization_id == org_id)


def dataset_row_text(row: dict) -> str:
    parts: list[str] = []
    name = row.get("dataset_name")
    if name:
        parts.append(str(name))
    for key in ("prompt", "expected_response", "response"):
        value = row.get(key)
        if value:
            parts.append(str(value))
    ctx = row.get("context")
    if isinstance(ctx, list):
        for item in ctx:
            if isinstance(item, dict):
                parts.append(str(item.get("page_content") or item.get("text") or ""))
            elif item:
                parts.append(str(item))
    elif ctx:
        parts.append(str(ctx))
    return "\n".join(part for part in parts if part)
