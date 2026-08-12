"""Cliente Redis para encolar jobs de ingesta y publicar eventos."""

from __future__ import annotations

import json
import logging
import os
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
INGEST_QUEUE = os.getenv("INGEST_QUEUE", "ingest:jobs")
INGEST_EVENTS = os.getenv("INGEST_EVENTS", "ingest:events")
USE_INGEST_QUEUE = os.getenv("USE_INGEST_QUEUE", "false").lower() in {
    "1",
    "true",
    "yes",
}

_redis = None


def ingest_queue_enabled() -> bool:
    return USE_INGEST_QUEUE


def get_redis():
    global _redis
    if _redis is not None:
        return _redis
    try:
        import redis

        _redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        _redis.ping()
        return _redis
    except Exception as exc:
        logger.warning("Redis unavailable (%s); falling back to BackgroundTasks", exc)
        return None


def enqueue_ingest_job(document_id: UUID | str, job_id: UUID | str) -> bool:
    """Encola job. True si se encoló; False si hay que usar BackgroundTasks."""
    if not USE_INGEST_QUEUE:
        return False
    r = get_redis()
    if r is None:
        return False
    payload = json.dumps(
        {
            "document_id": str(document_id),
            "job_id": str(job_id),
        }
    )
    r.lpush(INGEST_QUEUE, payload)
    logger.info("[INGEST QUEUE] enqueued document=%s job=%s", document_id, job_id)
    return True


def publish_ingest_event(event: dict[str, Any]) -> None:
    r = get_redis()
    if r is None:
        return
    raw = json.dumps(event)
    r.publish(INGEST_EVENTS, raw)
