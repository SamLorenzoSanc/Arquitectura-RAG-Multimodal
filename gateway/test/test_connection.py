import pytest
from sqlalchemy import text

from services.database import AsyncSessionLocal


@pytest.mark.anyio
async def test_connection():

    async with AsyncSessionLocal() as db:
        result = await db.execute(text("SELECT version()"))
        assert result.scalar() is not None