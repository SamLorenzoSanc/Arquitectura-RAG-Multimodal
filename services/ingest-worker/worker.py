"""Ingest worker: consume cola Redis y dispara el pipeline de documentos.

Flujo:
  1. Gateway encola JSON {document_id, job_id} en ingest:jobs
  2. Worker hace BRPOP y llama al endpoint interno del API
  3. El API ejecuta IngestService existente (chunk→embed→pgvector)
  4. Publica evento en ingest:events para SSE/WebSocket del gateway
"""

from __future__ import annotations

import json
import os
import time

import httpx
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
API_INTERNAL_URL = os.getenv("API_INTERNAL_URL", "http://api:8000").rstrip("/")
INTERNAL_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "agrops-internal")
QUEUE = os.getenv("INGEST_QUEUE", "ingest:jobs")
EVENTS = os.getenv("INGEST_EVENTS", "ingest:events")
BLOCK_SECONDS = int(os.getenv("INGEST_BRPOP_TIMEOUT", "5"))


def publish(r: redis.Redis, event: dict) -> None:
    r.publish(EVENTS, json.dumps(event))
    r.lpush(f"{EVENTS}:log", json.dumps(event))
    r.ltrim(f"{EVENTS}:log", 0, 199)


def process_job(r: redis.Redis, raw: str) -> None:
    job = json.loads(raw)
    document_id = job["document_id"]
    job_id = job.get("job_id") or document_id
    publish(
        r,
        {
            "type": "ingest.started",
            "document_id": document_id,
            "job_id": job_id,
            "ts": time.time(),
        },
    )
    url = f"{API_INTERNAL_URL}/api/v1/internal/documents/{document_id}/process"
    headers = {"X-Internal-Token": INTERNAL_TOKEN}
    try:
        with httpx.Client(timeout=600.0) as client:
            resp = client.post(url, headers=headers, json={"job_id": job_id})
        if resp.status_code >= 400:
            publish(
                r,
                {
                    "type": "ingest.failed",
                    "document_id": document_id,
                    "job_id": job_id,
                    "error": resp.text[:500],
                    "ts": time.time(),
                },
            )
            return
        body = resp.json() if resp.content else {}
        publish(
            r,
            {
                "type": "ingest.completed",
                "document_id": document_id,
                "job_id": job_id,
                "chunks": body.get("chunks"),
                "ts": time.time(),
            },
        )
    except Exception as exc:
        publish(
            r,
            {
                "type": "ingest.failed",
                "document_id": document_id,
                "job_id": job_id,
                "error": str(exc),
                "ts": time.time(),
            },
        )


def main() -> None:
    print(f"[ingest-worker] listening {QUEUE} via {REDIS_URL}", flush=True)
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    while True:
        item = r.brpop(QUEUE, timeout=BLOCK_SECONDS)
        if not item:
            continue
        _, payload = item
        print(f"[ingest-worker] job={payload[:200]}", flush=True)
        process_job(r, payload)


if __name__ == "__main__":
    main()
