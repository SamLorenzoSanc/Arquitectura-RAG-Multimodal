"""Resolución de URL de inferencia (Ollama detrás de inference-service).

Si INFERENCE_URL está definido, el gateway usa ese proxy OpenAI-compatible
en lugar de hablar con Ollama directamente (aísla GPU/latencia).
"""

from __future__ import annotations

import os


def resolve_llm_base_url() -> str:
    inference = os.getenv("INFERENCE_URL", "").rstrip("/")
    if inference:
        return f"{inference}/v1"
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
