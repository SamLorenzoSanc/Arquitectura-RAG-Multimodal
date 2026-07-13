# services/vector_store.py
from __future__ import annotations

import os
import logging
from pathlib import Path

import chromadb

logger = logging.getLogger(__name__)

# Ruta ÚNICA de Chroma. Ingesta (document_processor) y recuperación
# (rag_service)
CHROMA_PATH = os.getenv(
    "CHROMA_PATH",
    str(Path(__file__).parent.parent / "chroma_db"),
)


class VectorStore:
    def __init__(self, path: str = CHROMA_PATH):
        self.client = chromadb.PersistentClient(path=path)

    def get_collection(self, name: str):
        return self.client.get_or_create_collection(name)

    def add_embedded_chunks(
        self,
        collection_name: str,
        embedded_chunks: list,   # list[EmbeddedChunk]
        base_metadata: dict,     # source, document_id, knowledge_base_id, tenant_id (todo str)
    ) -> int:
        collection = self.get_collection(collection_name)

        ids, documents, embeddings, metadatas = [], [], [], []

        for i, ec in enumerate(embedded_chunks):
            chunk = ec.chunk
            ids.append(f"{base_metadata['document_id']}_{i}")
            # texto que se devolverá como contexto en la recuperación
            documents.append(chunk.original_text)
            embeddings.append(ec.embedding)
            # OJO: Chroma solo acepta str/int/float/bool en metadata; nada de None
            metadatas.append({
                **base_metadata,
                "chunk_index": i,
                "headline": chunk.headline or "",
                "summary": chunk.summary or "",
            })

        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info("Persisted %s chunks in collection %s", len(ids), collection_name)
        return len(ids)