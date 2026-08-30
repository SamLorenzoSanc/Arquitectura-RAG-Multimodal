from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from utils.scope import (
    KnowledgeScope,
    resolve_knowledge_collections,
    resolve_knowledge_scope,
)


pytestmark = pytest.mark.unit


def _membership_result(role: str = "member"):
    result = MagicMock()
    result.mappings.return_value.first.return_value = {
        "organization_id": "org-1",
        "tenant_id": "tenant-1",
        "role_name": role,
        "legacy_department_id": None,
    }
    return result


def _departments_result(*ids: str):
    result = MagicMock()
    result.all.return_value = [(item,) for item in ids]
    return result


@pytest.mark.asyncio
async def test_member_scope_uses_department_memberships():
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _membership_result(),
            _departments_result("dept-1", "dept-2"),
        ]
    )

    scope = await resolve_knowledge_scope(
        db,
        user_id="user-1",
        organization_id="org-1",
    )

    assert scope.department_ids == ("dept-1", "dept-2")
    assert scope.is_admin is False


@pytest.mark.asyncio
async def test_member_cannot_select_another_department():
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[_membership_result(), _departments_result("dept-1")]
    )
    db.scalar = AsyncMock(return_value=True)

    with pytest.raises(HTTPException) as exc:
        await resolve_knowledge_scope(
            db,
            user_id="user-1",
            organization_id="org-1",
            department_id="dept-2",
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_explicit_kb_must_belong_to_department_scope():
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=False)
    scope = KnowledgeScope(
        organization_id="org-1",
        tenant_id="tenant-1",
        department_ids=("dept-1",),
        is_admin=False,
    )

    with pytest.raises(HTTPException) as exc:
        await resolve_knowledge_collections(
            db,
            scope=scope,
            knowledge_base_id="kb-other",
        )

    assert exc.value.status_code == 403
