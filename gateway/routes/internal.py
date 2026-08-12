"""Rutas internas entre microservicios (token compartido)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from routes.documents import _run_processing
from services.queue_service import INGEST_EVENTS, get_redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["Internal"])

INTERNAL_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "agrops-internal")


def _check_token(x_internal_token: str | None) -> None:
    if not x_internal_token or x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal token",
        )


class ProcessBody(BaseModel):
    job_id: UUID | None = None


@router.post("/documents/{document_id}/process")
async def process_document_internal(
    document_id: UUID,
    body: ProcessBody | None = None,
    x_internal_token: str | None = Header(default=None),
):
    """Invocado por ingest-worker tras BRPOP de Redis."""
    _check_token(x_internal_token)
    job_id = body.job_id if body and body.job_id else document_id
    await _run_processing(document_id, job_id)
    return {
        "status": "completed",
        "document_id": str(document_id),
        "job_id": str(job_id),
    }


@router.get("/ingest/events")
async def ingest_events_sse(
    x_internal_token: str | None = Header(default=None),
):
    """SSE de progreso de ingesta (Redis pub/sub ingest:events)."""
    _check_token(x_internal_token)
    r = get_redis()
    if r is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    async def event_stream():
        pubsub = r.pubsub()
        pubsub.subscribe(INGEST_EVENTS)
        try:
            yield f"data: {json.dumps({'type': 'ingest.subscribed'})}\n\n"
            while True:
                message = await asyncio.to_thread(
                    pubsub.get_message,
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if message and message.get("type") == "message":
                    data = message.get("data")
                    yield f"data: {data}\n\n"
                else:
                    yield ": keepalive\n\n"
                    await asyncio.sleep(0.05)
        finally:
            try:
                pubsub.unsubscribe(INGEST_EVENTS)
                pubsub.close()
            except Exception:
                pass

    return StreamingResponse(event_stream(), media_type="text/event-stream")
