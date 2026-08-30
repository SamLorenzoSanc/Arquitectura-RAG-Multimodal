from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import Any

from openai import OpenAI

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")
RAG_MAX_TOKENS = int(os.getenv("RAG_MAX_TOKENS", "1536"))
RAG_CHAT_MAX_TOKENS = int(os.getenv("RAG_CHAT_MAX_TOKENS", "256"))
RAG_NUM_CTX = int(os.getenv("RAG_NUM_CTX", "2048"))
RAG_TEMPERATURE = float(os.getenv("RAG_TEMPERATURE", "0"))
RAG_KEEP_ALIVE = os.getenv("RAG_KEEP_ALIVE", "24h")


class OllamaLlmAdapter:
    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        api_key: str = OLLAMA_API_KEY,
        temperature: float = RAG_TEMPERATURE,
        max_tokens: int = RAG_MAX_TOKENS,
        keep_alive: str = RAG_KEEP_ALIVE,
    ):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.keep_alive = keep_alive

    async def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        temp = self.temperature if temperature is None else float(temperature)
        tokens = self.max_tokens if max_tokens is None else int(max_tokens)
        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=model,
            messages=messages,
            temperature=temp,
            max_tokens=tokens,
            extra_body={
                "keep_alive": self.keep_alive,
                "options": {"num_ctx": RAG_NUM_CTX, "num_predict": tokens},
            },
        )
        return response.choices[0].message.content or ""

    async def stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        on_token: Callable[[str], Awaitable[None] | None] | None = None,
    ) -> str:
        temp = self.temperature if temperature is None else float(temperature)
        tokens = self.max_tokens if max_tokens is None else int(max_tokens)
        queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _run() -> None:
            try:
                stream = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=tokens,
                    stream=True,
                    extra_body={
                        "keep_alive": self.keep_alive,
                        "options": {"num_ctx": RAG_NUM_CTX, "num_predict": tokens},
                    },
                )
                for chunk in stream:
                    choice = chunk.choices[0] if chunk.choices else None
                    delta = (
                        (choice.delta.content or "")
                        if choice and choice.delta
                        else ""
                    )
                    if delta:
                        loop.call_soon_threadsafe(queue.put_nowait, ("token", delta))
                loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
            except Exception as exc:  # noqa: BLE001
                loop.call_soon_threadsafe(queue.put_nowait, ("error", exc))

        worker = asyncio.create_task(asyncio.to_thread(_run))
        parts: list[str] = []
        while True:
            kind, payload = await queue.get()
            if kind == "token":
                parts.append(str(payload))
                if on_token is not None:
                    maybe = on_token(str(payload))
                    if maybe is not None and hasattr(maybe, "__await__"):
                        await maybe  # type: ignore[misc]
            elif kind == "done":
                break
            elif kind == "error":
                await worker
                raise payload
        await worker
        return "".join(parts)

    async def parse(
        self, model: str, messages: list[dict[str, str]], response_format: Any
    ) -> Any:
        completion = await asyncio.to_thread(
            self.client.beta.chat.completions.parse,
            model=model,
            messages=messages,
            response_format=response_format,
        )
        return completion.choices[0].message.parsed


class OllamaEmbeddingAdapter:
    def __init__(
        self,
        model: str,
        base_url: str = OLLAMA_BASE_URL,
        api_key: str = OLLAMA_API_KEY,
    ):
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    async def embed(self, text: str) -> list[float]:
        response = await asyncio.to_thread(
            self.client.embeddings.create,
            model=self.model,
            input=[text],
        )
        return list(response.data[0].embedding)
