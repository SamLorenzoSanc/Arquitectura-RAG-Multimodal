"""Progreso en memoria de la ingesta documental (un proceso API)."""

from __future__ import annotations

from typing import Any

_PROGRESS: dict[str, dict[str, Any]] = {}

TERMINAL = frozenset({"completed", "failed"})


def set_progress(document_id: str, **fields: Any) -> dict[str, Any]:
    current = dict(_PROGRESS.get(str(document_id)) or {})
    current.update(fields)
    current["document_id"] = str(document_id)
    if "percent" in current:
        current["percent"] = max(0, min(100, int(current["percent"] or 0)))
    _PROGRESS[str(document_id)] = current
    return current


def get_progress(document_id: str) -> dict[str, Any] | None:
    snap = _PROGRESS.get(str(document_id))
    return dict(snap) if snap else None


def clear_progress(document_id: str) -> None:
    _PROGRESS.pop(str(document_id), None)
