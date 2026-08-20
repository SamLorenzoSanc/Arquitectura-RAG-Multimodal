from rag.composition import build_rag_container


class CatalogIngest:
    """Fachada de catálogo que dispara el caso de uso hexagonal IngestDocument."""

    async def after_upload(self, tenant_id: str) -> None:
        await build_rag_container().ingest.execute(str(tenant_id))
