import asyncio

from sqlalchemy import text

from services.database import AsyncSessionLocal


async def test():

    async with AsyncSessionLocal() as db:

        result = await db.execute(text("SELECT version()"))

        print(result.scalar())


asyncio.run(test())