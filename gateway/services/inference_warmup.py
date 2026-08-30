"""Warm-up automático de Ollama al arrancar el gateway.

Evita el cold start de la primera pregunta del chat: carga embedding +
generación en memoria (y en GPU si el contenedor Ollama tiene CUDA).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
EMBED_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "nomic-embed-text")
GEN_MODEL = os.getenv("RAG_GENERATION_MODEL", "llama3.2:latest")
WARMUP_ENABLED = os.getenv("RAG_INFERENCE_WARMUP", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
WARMUP_TIMEOUT = float(os.getenv("RAG_INFERENCE_WARMUP_TIMEOUT", "180"))


async def warmup_ollama(*, force: bool = False) -> dict[str, Any]:
    """Dispara una inferencia mínima de embed + generate. No lanza excepciones."""
    if not force and not WARMUP_ENABLED:
        return {"skipped": True, "reason": "RAG_INFERENCE_WARMUP=false"}

    result: dict[str, Any] = {
        "embedding_model": EMBED_MODEL,
        "generation_model": GEN_MODEL,
        "embedding_ok": False,
        "generation_ok": False,
    }
    timeout = httpx.Timeout(WARMUP_TIMEOUT, connect=10.0)
    try:
        async with httpx.AsyncClient(base_url=OLLAMA_URL, timeout=timeout) as client:
            try:
                emb = await client.post(
                    "/api/embeddings",
                    json={"model": EMBED_MODEL, "prompt": "warmup AgroPS"},
                )
                result["embedding_ok"] = emb.status_code < 400
                result["embedding_status"] = emb.status_code
            except Exception as exc:  # noqa: BLE001
                result["embedding_error"] = str(exc)[:200]
                logger.warning("Warm-up embedding falló: %s", exc)

            try:
                gen = await client.post(
                    "/api/generate",
                    json={
                        "model": GEN_MODEL,
                        "prompt": "Di solo: OK",
                        "stream": False,
                        "keep_alive": os.getenv("OLLAMA_KEEP_ALIVE", "24h"),
                        "options": {"num_predict": 4, "temperature": 0},
                    },
                )
                result["generation_ok"] = gen.status_code < 400
                result["generation_status"] = gen.status_code
            except Exception as exc:  # noqa: BLE001
                result["generation_error"] = str(exc)[:200]
                logger.warning("Warm-up generation falló: %s", exc)
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)[:200]
        logger.warning("Warm-up Ollama no disponible: %s", exc)

    logger.info(
        "Warm-up inferencia: embed=%s gen=%s",
        result.get("embedding_ok"),
        result.get("generation_ok"),
    )
    return result


def schedule_warmup() -> asyncio.Task | None:
    """Lanza el warm-up en background sin bloquear el arranque de FastAPI."""
    if not WARMUP_ENABLED:
        return None

    async def _run() -> None:
        # Pequeña espera: Ollama/init pueden estar aún tirando del modelo.
        await asyncio.sleep(2.0)
        await warmup_ollama()

    return asyncio.create_task(_run(), name="agrops-inference-warmup")
