"""Eventos de progreso del chat (SSE) para mostrar el razonamiento en vivo."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


def sse_encode(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


async def emit(callback: ProgressCallback | None, event_type: str, **data: Any) -> None:
    if callback is None:
        return
    payload = {"type": event_type, **data}
    result = callback(payload)
    if result is not None and hasattr(result, "__await__"):
        await result  # type: ignore[misc]
