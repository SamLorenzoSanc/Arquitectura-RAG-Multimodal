from __future__ import annotations

import asyncio
import logging
import pickle
import re
import time
import unicodedata
from pathlib import Path

from dotenv import load_dotenv
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from rank_bm25 import BM25Okapi
from tenacity import retry, wait_exponential
from sqlalchemy import select

from models.document import Document
from models.chunk import Chunk as ChunkModel
from models.embedding import Embedding
from parsers.base import ParsingContext
from parsers.factory import FileParserFactory
from services.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

MODEL = "llama3"
EMBEDDING_MODEL = "qwen3-embedding:latest"
wait_strategy = wait_exponential(multiplier=1, min=2, max=60)

# Debe coincidir con RAGService.bm25_index_dir.
BM25_INDEX_DIR = Path(__file__).resolve().parent / "bm25_indexes"
BM25_INDEX_DIR.mkdir(parents=True, exist_ok=True)

client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)


class ChunkMetadata(BaseModel):
    """Esquema restringido al LLM: solo genera el título y el resumen."""

    headline: str = Field(
        description="Un título breve de 3 a 5 palabras para este fragmento"
    )
    summary: str = Field(description="Resumen de 1 a 2 oraciones del fragmento")


class ProcessedChunk(BaseModel):
    """Objeto interno que une el texto original con la metadata generada."""

    headline: str
    summary: str
    original_text: str


class IngestService:
    def __init__(self, session):
        self.session = session
        self.parser_factory = FileParserFactory()

    @staticmethod
    def _normalize_text(text: str | None) -> str:
        text = text or ""
        text = unicodedata.normalize("NFKC", text).lower()
        return "".join(
            c
            for c in unicodedata.normalize("NFKD", text)
            if not unicodedata.combining(c)
        )

    @classmethod
    def _tokenize(cls, text: str | None) -> list[str]:
        normalized = cls._normalize_text(text)
        return re.findall(r"[^\W_]+(?:[-/][^\W_]+)*", normalized, flags=re.UNICODE)

    @staticmethod
    def _safe_filename(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", value)

    @classmethod
    def _bm25_path(cls, tenant_id: str) -> Path:
        return BM25_INDEX_DIR / f"tenant_{cls._safe_filename(str(tenant_id))}.pkl"

    async def _rebuild_bm25_index(self, tenant_id: str):
        """Regenera el índice BM25 del tenant después de una ingesta exitosa."""
        stmt = (
            select(ChunkModel, Document)
            .join(Document, Document.id == ChunkModel.document_id)
            .where(Document.tenant_id == tenant_id)
            .order_by(Document.id, ChunkModel.position)
        )

        result_proxy = await self.session.execute(stmt)
        rows = result_proxy.all()

        documents = []
        for chunk, document in rows:
            text = "\n".join(
                part for part in [chunk.headline, chunk.summary, chunk.content] if part
            )
            documents.append(
                {
                    "chunk_id": str(chunk.id),
                    "document_id": str(document.id),
                    "tenant_id": str(document.tenant_id),
                    "knowledge_base_id": str(document.knowledge_base_id),
                    "source": document.filename,
                    "type": document.mime_type,
                    "position": chunk.position,
                    "text": text,
                }
            )

        if not documents:
            path = self._bm25_path(tenant_id)
            if path.exists():
                path.unlink()
            return

        corpus = [self._tokenize(item["text"]) for item in documents]
        # Construir aquí valida que el corpus sea tokenizable y deja explícita
        # la implementación Okapi BM25 usada por el experimento.
        BM25Okapi(corpus)

        payload = {
            "version": 1,
            "tenant_id": str(tenant_id),
            "documents": documents,
            "created_at": time.time(),
        }
        path = self._bm25_path(tenant_id)
        tmp_path = path.with_suffix(".tmp")
        with tmp_path.open("wb") as fh:
            pickle.dump(payload, fh, protocol=pickle.HIGHEST_PROTOCOL)
        tmp_path.replace(path)

        print(
            f"   [BM25 INDEX] Tenant {tenant_id}: "
            f"{len(documents)} chunks indexados en {path}"
        )

    async def process(self, document: Document) -> int:
        print("\n" + "=" * 80)
        print(f"[INICIO INGESTA] Procesando Documento ID: {document.id}")
        print(f"Archivo: '{document.filename}' | Ruta: '{document.storage_path}'")
        print("=" * 80)

        # PASO 1: PARSING
        print("\n=== PASO 1: Parsing del Documento (LlamaParse API) ===")
        file_path = Path(document.storage_path)
        parser = self.parser_factory.create(file_path)
        context = self.build_context(document)
        parsed = await parser.parse(file_path, context)

        print(f"   [PARSER] Caracteres extraídos: {len(parsed.markdown)}")
        if len(parsed.markdown) < 10:
            print(f"   [ALERTA PARSER] Texto extremadamente corto: '{parsed.markdown}'")

        output_dir = Path(__file__).parent / "extracted_md"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_filename = f"{Path(document.filename).stem}_{document.id}.md"
        output_file_path = output_dir / output_filename
        output_file_path.write_text(parsed.markdown, encoding="utf-8")
        print(f"   [DISK PERSIST] Markdown extraído: {output_file_path.resolve()}")

        # PASO 2: CHUNKING + ENRIQUECIMIENTO
        print("\n=== PASO 2: Fragmentación (Python) y Enriquecimiento (LLM) ===")
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False,
        )
        header_splits = markdown_splitter.split_text(parsed.markdown)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
        )
        raw_chunks = text_splitter.split_documents(header_splits)
        print(f"   [PYTHON CHUNKER] Fragmentos generados: {len(raw_chunks)}")

        tasks = [self._enrich_chunk(chunk.page_content) for chunk in raw_chunks]
        enriched_chunks: list[ProcessedChunk] = await asyncio.gather(*tasks)

        # PASO 3 & 4: EMBEDDINGS + PERSISTENCIA
        print("\n=== PASO 3 & 4: Embeddings & PostgreSQL ===")
        await self.create_embeddings_and_save(document=document, chunks=enriched_chunks)

        # PASO 5: ÍNDICE LÉXICO BM25
        print("\n=== PASO 5: Actualización del índice BM25 ===")
        await self._rebuild_bm25_index(str(document.tenant_id))

        print("\n" + "=" * 80)
        print(f"[FIN INGESTA] Documento '{document.filename}' completado con éxito.")
        print("=" * 80 + "\n")
        return len(enriched_chunks)

    @retry(wait=wait_strategy)
    async def _enrich_chunk(self, chunk_text: str) -> ProcessedChunk:
        prompt = f"""
        Analiza el siguiente texto y extrae:
        1. Un título breve (headline) de 3 a 5 palabras.
        2. Un resumen sintético (summary) de 1 o 2 frases.

        Texto:
        """
        {chunk_text}
        """

        Responde únicamente en español.
        """
        response = await client.beta.chat.completions.parse(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format=ChunkMetadata,
        )
        parsed = response.choices[0].message.parsed
        headline = parsed.headline if parsed else "Sin título"
        summary = parsed.summary if parsed else "Sin resumen"
        return ProcessedChunk(
            headline=headline,
            summary=summary,
            original_text=chunk_text,
        )

    async def create_embeddings_and_save(
        self,
        document: Document,
        chunks: list[ProcessedChunk],
    ):
        if not chunks:
            print("   [EMBEDDINGS] No hay chunks para procesar.")
            return

        texts_to_embed = [
            f"{chunk.headline}\n\n{chunk.summary}\n\n{chunk.original_text}"
            for chunk in chunks
        ]

        all_vectors = []
        BATCH_SIZE = 10
        print(
            f"   [EMBEDDINGS ASYNC] Generando vectores con '{EMBEDDING_MODEL}' "
            f"para {len(texts_to_embed)} fragmentos..."
        )

        for i in range(0, len(texts_to_embed), BATCH_SIZE):
            batch = texts_to_embed[i : i + BATCH_SIZE]
            response = await client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
            )
            vectors_in_batch = [emb.embedding for emb in response.data]
            all_vectors.extend(vectors_in_batch)
            print(
                f"   [EMBEDDINGS BATCH {i // BATCH_SIZE + 1}] "
                f"Vectores: {len(vectors_in_batch)} | "
                f"Dimensión: {len(vectors_in_batch[0])}"
            )

        print("\n   [DB PERSISTENCE] Preparando registros...")
        chunk_models = []
        for position, chunk in enumerate(chunks):
            db_chunk = ChunkModel(
                document_id=document.id,
                position=position,
                headline=chunk.headline,
                summary=chunk.summary,
                content=chunk.original_text,
            )
            self.session.add(db_chunk)
            chunk_models.append(db_chunk)

        await self.session.flush()

        for db_chunk, vector in zip(chunk_models, all_vectors):
            db_embedding = Embedding(
                chunk_id=db_chunk.id,
                model=EMBEDDING_MODEL,
                vector=vector,
            )
            self.session.add(db_embedding)

        await self.session.commit()
        print(
            f"   [DB COMMIT SUCCESS] Guardados {len(chunk_models)} Chunks "
            f"y {len(all_vectors)} Embeddings correctamente."
        )

    def build_context(self, document: Document) -> ParsingContext:
        return ParsingContext(
            tenant_id=document.tenant_id,
            organization_id=None,
            department_id=None,
            member_id=document.owner_id,
            uploaded_by=document.owner_id,
            language="es",
            tags=[],
        )
