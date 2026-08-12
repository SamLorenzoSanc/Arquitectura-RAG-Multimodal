"""Inference microservice: embeddings + generación LLM vía Ollama.

Expone API compatible OpenAI en :50051 para que el gateway orqueste
sin acoplar GPU/latencia. Equivalente al contrato protos/inference.proto.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")
DEFAULT_EMBED_MODEL = os.getenv("DEFAULT_EMBED_MODEL", "qwen3-embedding:latest")
DEFAULT_CHAT_MODEL = os.getenv("DEFAULT_CHAT_MODEL", "llama3.2:latest")

app = FastAPI(title="AgroPS Inference Service", version="1.0.0")
client = OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)


class EmbedBody(BaseModel):
    model: str | None = None
    input: str | list[str]


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatBody(BaseModel):
    model: str | None = None
    messages: list[ChatMessage]
    temperature: float = 0.0
    max_tokens: int | None = 256


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "inference", "ollama": OLLAMA_BASE_URL}


@app.post("/v1/embeddings")
def embeddings(body: EmbedBody) -> dict[str, Any]:
    model = body.model or DEFAULT_EMBED_MODEL
    try:
        resp = client.embeddings.create(model=model, input=body.input)
        return resp.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ollama embed error: {exc}") from exc


@app.post("/v1/chat/completions")
def chat_completions(body: ChatBody) -> dict[str, Any]:
    model = body.model or DEFAULT_CHAT_MODEL
    try:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [m.model_dump() for m in body.messages],
            "temperature": body.temperature,
        }
        if body.max_tokens is not None:
            kwargs["max_tokens"] = body.max_tokens
        resp = client.chat.completions.create(**kwargs)
        return resp.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ollama generate error: {exc}") from exc


@app.post("/rpc/Embed")
def rpc_embed(body: EmbedBody) -> dict[str, Any]:
    """Fachada estilo gRPC Embed (JSON)."""
    data = embeddings(body)
    vectors = [d["embedding"] for d in data.get("data", [])]
    return {"model": body.model or DEFAULT_EMBED_MODEL, "embeddings": vectors}


@app.post("/rpc/Generate")
def rpc_generate(body: ChatBody) -> dict[str, Any]:
    data = chat_completions(body)
    choice = (data.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content") or ""
    usage = data.get("usage") or {}
    return {
        "model": body.model or DEFAULT_CHAT_MODEL,
        "content": content,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
    }
