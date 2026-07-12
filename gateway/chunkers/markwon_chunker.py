async def process(
    self,
    document: Document,
):

    parser = self.parser_factory.create(
        Path(document.storage_path)
    )

    parsed = await parser.parse(
        Path(document.storage_path)
    )

    markdown = self.markdown_service.clean(
        parsed.markdown
    )

    chunks = self.chunker.chunk(
        markdown
    )

    embeddings = await self.embedding_service.embed(
        chunks
    )

    await self.graph_service.ingest(
        chunks
    )