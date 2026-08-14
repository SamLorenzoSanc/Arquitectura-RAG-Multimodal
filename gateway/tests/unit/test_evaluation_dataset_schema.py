import pytest
from unittest.mock import AsyncMock

from services.evaluation_dataset import safe_rollback


@pytest.mark.asyncio
async def test_safe_rollback_ignores_rollback_errors():
    db = AsyncMock()
    db.rollback = AsyncMock(side_effect=RuntimeError("already closed"))
    await safe_rollback(db)
    db.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_safe_rollback_accepts_none():
    await safe_rollback(None)
