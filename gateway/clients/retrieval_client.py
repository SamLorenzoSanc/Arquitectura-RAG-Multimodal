"""Cliente HTTP del retrieval-service (Dense aislado del chat)."""

from __future__ import annotations

import os
from typing import Any

import httpx

RETRIEVAL_URL = os.getenv("RETRIEVAL_URL", "").rstrip("/")
USE_RETRIEVAL_SERVICE = os.getenv("USE_RETRIEVAL_SERVICE", "false").lower() in {
    "1",
    "true",
    "yes",
}


def retrieval_service_enabled() -> bool:
    return USE_RETRIEVAL_SERVICE and bool(RETRIEVAL_URL)


async def retrieve_remote(
    question: str,
    tenant_id: str,
    collections: list[str] | None = None,
    retrieval_k: int = 10,
    final_k: int = 5,
) -> dict[str, Any]:
    if not retrieval_service_enabled():
        raise RuntimeError("Retrieval service disabled")
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{RETRIEVAL_URL}/v1/retrieve",
            json={
                "question": question,
                "tenant_id": tenant_id,
                "collections": collections or [],
                "retrieval_k": retrieval_k,
                "final_k": final_k,
            },
        )
        resp.raise_for_status()
        return resp.json()
