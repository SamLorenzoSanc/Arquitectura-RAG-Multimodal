from __future__ import annotations

import asyncio
import pickle
import re
import time
from pathlib import Path
from threading import Lock

from rank_bm25 import BM25Okapi
from sqlalchemy import select, text

from models.chunk import Chunk
from models.document import Document
from rag.adapters.outbound.scope import (
    is_uuid,
    organization_tenant_ids,
    dataset_row_text,
)
from rag.domain.entities import RetrievedChunk
from rag.domain.lexicon import tokenize
from services.database import AsyncSessionLocal


class Bm25LexicalIndex:
    INDEX_VERSION = 2

    def __init__(self, index_dir: str | Path | None = None):
        self.index_dir = Path(
            index_dir
            or Path(__file__).resolve().parents[3] / "services" / "bm25_indexes"
        )
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, tuple[float, BM25Okapi, list[dict]]] = {}
        self._lock = Lock()

    @staticmethod
    def _safe_filename(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", value)

    def _path(self, tenant_id: str) -> Path:
        return self.index_dir / f"tenant_{self._safe_filename(str(tenant_id))}.pkl"

    def invalidate(self, tenant_id: str | None = None) -> None:
        if tenant_id is None:
            self._cache.clear()
            for path in self.index_dir.glob("tenant_*.pkl"):
                path.unlink(missing_ok=True)
            return
        self._cache.pop(str(tenant_id), None)
        self._path(tenant_id).unlink(missing_ok=True)

    async def rebuild(self, tenant_id: str) -> None:
        loaded = await self._build_from_db(tenant_id)
        if loaded is None:
            return
        bm25, documents, mtime = loaded
        self._cache[str(tenant_id)] = (mtime, bm25, documents)

    async def retrieve(
        self,
        question: str,
        tenant_id: str,
        collections: list[str] | None,
        *,
        k: int,
    ) -> list[RetrievedChunk]:
        t0 = time.time()
        bm25, documents = await self._get_index(tenant_id)
        if bm25 is None:
            return []
        query_tokens = tokenize(question)
        if not query_tokens:
            return []
        scores = bm25.get_scores(query_tokens)
        latency_ms = (time.time() - t0) * 1000
        allowed = set(map(str, collections)) if collections else None
        ranked_indices = sorted(
            range(len(documents)),
            key=lambda i: float(scores[i]),
            reverse=True,
        )
        results: list[RetrievedChunk] = []
        for idx in ranked_indices:
            meta = documents[idx]
            score = float(scores[idx])
            if score <= 0:
                continue
            kb_id = str(meta.get("knowledge_base_id") or "")
            if allowed is not None and kb_id not in allowed:
                continue
            results.append(
                RetrievedChunk(
                    page_content=meta["text"],
                    metadata={
                        **meta,
                        "bm25_score": score,
                        "retrieval_source": "bm25",
                        "bm25_latency_ms": latency_ms,
                    },
                )
            )
            if len(results) >= k:
                break
        return results

    async def _get_index(self, tenant_id: str):
        path = self._path(tenant_id)
        mtime = path.stat().st_mtime if path.exists() else None
        cache = self._cache.get(str(tenant_id))
        if cache and mtime is not None and cache[0] == mtime:
            return cache[1], cache[2]
        with self._lock:
            loaded = await asyncio.to_thread(self._load_file, tenant_id)
        if loaded is None:
            loaded = await self._build_from_db(tenant_id)
            if loaded is None:
                return None, []
        bm25, documents, loaded_mtime = loaded
        self._cache[str(tenant_id)] = (loaded_mtime, bm25, documents)
        return bm25, documents

    def _load_file(self, tenant_id: str):
        path = self._path(tenant_id)
        if not path.exists():
            return None
        try:
            with path.open("rb") as fh:
                payload = pickle.load(fh)
            if not isinstance(payload, dict) or "documents" not in payload:
                return None
            if payload.get("version") != self.INDEX_VERSION:
                return None
            documents = payload["documents"]
            corpus = [tokenize(d["text"]) for d in documents]
            if not corpus:
                return None
            return BM25Okapi(corpus), documents, path.stat().st_mtime
        except Exception:
            return None

    async def _build_from_db(self, tenant_id: str):
        stmt = (
            select(Chunk, Document)
            .join(Document, Document.id == Chunk.document_id)
            .order_by(Document.id, Chunk.position)
        )
        if is_uuid(tenant_id):
            stmt = stmt.where(
                Document.tenant_id.in_(organization_tenant_ids(tenant_id))
            )
        else:
            stmt = stmt.where(Document.tenant_id == tenant_id)
        documents = []
        async with AsyncSessionLocal() as session:
            rows = (await session.execute(stmt)).all()
            for chunk, document in rows:
                text = "\n".join(
                    part
                    for part in [chunk.headline, chunk.summary, chunk.content]
                    if part
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
            if is_uuid(tenant_id):
                try:
                    ds_rows = (
                        await session.execute(
                            text(
                                """
                                SELECT r.id::text AS id,
                                       r.tenant_id::text AS tenant_id,
                                       COALESCE(r.knowledge_base_id::text, '') AS knowledge_base_id,
                                       COALESCE(d.name, 'dataset') AS dataset_name,
                                       r.prompt, r.expected_response, r.response, r.context
                                FROM rag_dataset_rows r
                                JOIN rag_datasets d ON d.id = r.dataset_id
                                WHERE r.tenant_id IN (
                                  SELECT t2.id FROM tenants t2
                                  WHERE t2.organization_id = (
                                    SELECT t.organization_id FROM tenants t
                                    WHERE t.id = CAST(:tenant AS uuid)
                                  )
                                )
                                """
                            ),
                            {"tenant": tenant_id},
                        )
                    ).mappings().all()
                except Exception:
                    await session.rollback()
                    ds_rows = []
                for row in ds_rows:
                    body = dataset_row_text(row)
                    if not body.strip():
                        continue
                    documents.append(
                        {
                            "chunk_id": f"dataset:{row['id']}",
                            "document_id": f"dataset:{row['id']}",
                            "tenant_id": row["tenant_id"],
                            "knowledge_base_id": row["knowledge_base_id"] or None,
                            "source": f"dataset:{row['dataset_name']}",
                            "type": "dataset",
                            "position": 0,
                            "text": body,
                        }
                    )
        if not documents:
            return None
        payload = {
            "version": self.INDEX_VERSION,
            "tenant_id": str(tenant_id),
            "documents": documents,
            "created_at": time.time(),
        }
        path = self._path(tenant_id)
        tmp_path = path.with_suffix(".tmp")
        await asyncio.to_thread(self._dump, tmp_path, payload)
        tmp_path.replace(path)
        corpus = [tokenize(d["text"]) for d in documents]
        if not corpus:
            return None
        return BM25Okapi(corpus), documents, path.stat().st_mtime

    @staticmethod
    def _dump(tmp_path: Path, payload: dict) -> None:
        with tmp_path.open("wb") as fh:
            pickle.dump(payload, fh, protocol=pickle.HIGHEST_PROTOCOL)
