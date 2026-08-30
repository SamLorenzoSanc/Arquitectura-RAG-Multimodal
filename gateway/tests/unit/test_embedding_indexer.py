from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from services import embedding_indexer as idx


pytestmark = pytest.mark.unit


def test_indexer_defaults():
    assert idx.DEFAULT_BATCH_SIZE == 20
    assert idx.DEFAULT_INTERVAL_SECONDS == 20
    assert "embedding_model" in idx.ENSURE_INDEXER_SQL[0]


@pytest.mark.asyncio
async def test_retry_state_sets_pending(monkeypatch):
    monkeypatch.setattr(idx, "ensure_indexer_schema", AsyncMock())
    db = AsyncMock()
    result = MagicMock()
    result.mappings.return_value.first.return_value = {
        "id": str(uuid4()),
        "status": "pending",
        "attempts": 2,
    }
    db.execute.return_value = result
    row = await idx.retry_state(db, str(uuid4()))
    assert row["status"] == "pending"
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_schedule_indexer_can_be_disabled(monkeypatch):
    monkeypatch.setattr(idx, "INDEXER_ENABLED", False)
    assert idx.schedule_indexer() is None


@pytest.mark.asyncio
async def test_enqueue_document_defaults_to_nomic(monkeypatch):
    monkeypatch.setattr(idx, "ensure_indexer_schema", AsyncMock())
    db = AsyncMock()
    nomic_id = uuid4()
    nomic = MagicMock()
    nomic.scalar.return_value = nomic_id
    actives = MagicMock()
    actives.all.return_value = [(nomic_id,), (uuid4(),)]
    db.execute.side_effect = [nomic, actives, MagicMock()]
    queued = await idx.enqueue_document(
        db, document_id=str(uuid4()), source_hash="abc", force=True
    )
    assert queued == 1
    assert db.execute.await_count == 3


@pytest.mark.asyncio
async def test_enqueue_document_also_queues_exclusive_corpus_model(monkeypatch):
    monkeypatch.setattr(idx, "ensure_indexer_schema", AsyncMock())
    db = AsyncMock()
    nomic_id = uuid4()
    qwen_id = uuid4()
    nomic = MagicMock()
    nomic.scalar.return_value = nomic_id
    actives = MagicMock()
    actives.all.return_value = [(qwen_id,)]
    db.execute.side_effect = [nomic, actives, MagicMock(), MagicMock()]
    queued = await idx.enqueue_document(
        db, document_id=str(uuid4()), source_hash="abc"
    )
    assert queued == 2
    assert db.execute.await_count == 4


@pytest.mark.asyncio
async def test_claim_batch_requires_chunks(monkeypatch):
    db = AsyncMock()
    empty = MagicMock()
    empty.mappings.return_value.all.return_value = []
    db.execute.return_value = empty
    claimed = await idx._claim_batch(db, batch_size=20, lease_minutes=15)
    assert claimed == []
    sql = str(db.execute.await_args_list[0].args[0])
    assert "SKIP LOCKED" in sql
    assert "chunks" in sql.lower()


@pytest.mark.asyncio
async def test_retry_states_skips_empty():
    db = AsyncMock()
    queued = await idx.retry_states(db, [])
    assert queued == 0
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_summarize_index_empty_kbs():
    db = AsyncMock()
    counts = await idx.summarize_index(db, [])
    assert counts["total"] == 0
    assert counts["none"] == 0
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_mark_indexed_for_runtime():
    db = AsyncMock()
    await idx.mark_indexed_for_runtime(
        db,
        document_id=str(uuid4()),
        runtime_model_id="nomic-embed-text",
        source_hash="hash",
    )
    sql = str(db.execute.await_args.args[0])
    assert "indexed" in sql
    assert "runtime_model_id" in sql
