"""Reindexa todos los documentos con el embedding por defecto (nomic-embed-text)."""

from __future__ import annotations

import asyncio

from sqlalchemy import text

from services.database import AsyncSessionLocal
from services.embedding_reindex import reindex_embeddings
from services.rag_service import DEFAULT_EMBEDDING_MODEL


async def main() -> None:
    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            text(
                """
                SELECT DISTINCT tenant_id::text
                FROM documents
                WHERE tenant_id IS NOT NULL
                """
            )
        )
        tenants = [row[0] for row in rows if row[0]]
        if not tenants:
            print("No hay documentos que reindexar.")
            return
        print(f"Modelo: {DEFAULT_EMBEDDING_MODEL}")
        for tenant_id in tenants:
            result = await reindex_embeddings(
                db,
                tenant_id=tenant_id,
                models=[DEFAULT_EMBEDDING_MODEL],
            )
            print(
                f"tenant {tenant_id}: {result.get('chunks', 0)} chunks "
                f"{result.get('models', {})}"
            )


if __name__ == "__main__":
    asyncio.run(main())
