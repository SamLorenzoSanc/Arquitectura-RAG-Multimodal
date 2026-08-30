"""Servidor MCP stdio: herramientas de solo lectura sobre el gateway AgroPS."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "agrops",
    instructions=(
        "Cliente de solo lectura del gateway AgroPS (FastAPI). "
        "Úsalo para salud, retrieve híbrido, índice documental y config RAG. "
        "No genera respuestas de chat ni modifica el corpus."
    ),
)

_TOKEN: str | None = os.environ.get("AGROPS_MCP_TOKEN") or None
_CLIENT: httpx.Client | None = None


def _base_url() -> str:
    return os.environ.get("AGROPS_BASE_URL", "http://localhost:8000").rstrip("/")


def _api() -> str:
    return f"{_base_url()}/api/v1"


def _client() -> httpx.Client:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = httpx.Client(timeout=httpx.Timeout(30.0, read=120.0))
    return _CLIENT


def _dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def _clip_text(value: Any, limit: int = 400) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def _clip_chunk(chunk: Any) -> Any:
    if not isinstance(chunk, dict):
        return chunk
    out = dict(chunk)
    for key in ("page_content", "content", "text", "summary"):
        if key in out:
            out[key] = _clip_text(out[key])
    metadata = out.get("metadata")
    if isinstance(metadata, dict):
        meta = dict(metadata)
        for key in ("page_content", "content", "text", "snippet"):
            if key in meta:
                meta[key] = _clip_text(meta[key], 280)
        out["metadata"] = meta
    return out


def _clip_retrieve(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    out = dict(payload)
    for key in (
        "chunks",
        "dense_original",
        "dense_rewritten",
        "bm25_original",
        "bm25_rewritten",
        "candidates",
    ):
        items = out.get(key)
        if isinstance(items, list):
            out[key] = [_clip_chunk(item) for item in items[:12]]
    rewritten = out.get("rewritten_query")
    if isinstance(rewritten, str):
        out["rewritten_query"] = _clip_text(rewritten, 500)
    return out


def _login() -> str:
    email = os.environ.get("AGROPS_MCP_EMAIL", "").strip()
    password = os.environ.get("AGROPS_MCP_PASSWORD", "")
    if not email or not password:
        raise RuntimeError(
            "Configura AGROPS_MCP_EMAIL y AGROPS_MCP_PASSWORD en .env, "
            "o AGROPS_MCP_TOKEN con un JWT válido."
        )
    response = _client().post(
        f"{_api()}/auth/login",
        json={"email": email, "password": password},
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"Login falló ({response.status_code}): {response.text[:500]}"
        )
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("El login no devolvió access_token.")
    return str(token)


def _token(*, force: bool = False) -> str:
    global _TOKEN
    if force or not _TOKEN:
        env_token = os.environ.get("AGROPS_MCP_TOKEN", "").strip()
        _TOKEN = env_token or _login()
    return _TOKEN


def _request(
    method: str,
    path: str,
    *,
    auth: bool = True,
    timeout: float | None = None,
    **kwargs: Any,
) -> Any:
    url = f"{_api()}{path}"
    headers = dict(kwargs.pop("headers", {}) or {})
    if auth:
        headers["Authorization"] = f"Bearer {_token()}"

    def send() -> httpx.Response:
        return _client().request(
            method,
            url,
            headers=headers,
            timeout=timeout,
            **kwargs,
        )

    response = send()
    if auth and response.status_code == 401 and not os.environ.get("AGROPS_MCP_TOKEN"):
        headers["Authorization"] = f"Bearer {_token(force=True)}"
        response = send()
    if response.status_code >= 400:
        raise RuntimeError(
            f"{method} {path} -> {response.status_code}: {response.text[:800]}"
        )
    if not response.content:
        return None
    try:
        return response.json()
    except json.JSONDecodeError:
        return {"raw": response.text[:2_000]}


@mcp.tool()
def health() -> str:
    """Comprueba si el gateway AgroPS responde (GET /api/v1/health)."""
    return _dumps(_request("GET", "/health", auth=False))


@mcp.tool()
def ready() -> str:
    """Readiness: gateway + PostgreSQL (GET /api/v1/health/ready)."""
    return _dumps(_request("GET", "/health/ready", auth=False))


@mcp.tool()
def whoami() -> str:
    """Usuario autenticado con las credenciales MCP (GET /api/v1/auth/me)."""
    return _dumps(_request("GET", "/auth/me"))


@mcp.tool()
def runtime_config() -> str:
    """Config RAG congelada del runtime (modelos, k, flags)."""
    return _dumps(_request("GET", "/chat/evaluation/runtime-config"))


@mcp.tool()
def list_knowledge_bases() -> str:
    """Lista las bases de conocimiento visibles para el usuario MCP."""
    return _dumps(_request("GET", "/knowledge/"))


@mcp.tool()
def list_documents(knowledge_base_id: str) -> str:
    """Lista documentos de una knowledge base (metadatos e index_states)."""
    return _dumps(
        _request(
            "GET",
            "/documents",
            params={"knowledge_base_id": knowledge_base_id},
        )
    )


@mcp.tool()
def index_tasks(
    knowledge_base_id: str,
    status: str | None = None,
    q: str = "",
    limit: int = 50,
) -> str:
    """Tareas del indexador de embeddings para una knowledge base."""
    params: list[tuple[str, str | int]] = [
        ("knowledge_base_id", knowledge_base_id),
        ("limit", max(1, min(limit, 200))),
    ]
    if status:
        params.append(("status", status))
    if q:
        params.append(("q", q))
    return _dumps(_request("GET", "/documents/index-tasks", params=params))


@mcp.tool()
def retrieve(question: str, knowledge_base_id: str | None = None) -> str:
    """Ejecuta retrieval híbrido (dense + BM25 + RRF) sin generar respuesta LLM.

    Consume embeddings/Ollama. Recorta el texto de los chunks para el contexto.
    """
    body: dict[str, Any] = {"question": question}
    if knowledge_base_id:
        body["knowledge_base_id"] = knowledge_base_id
    payload = _request("POST", "/chat/retrieve", json=body, timeout=120.0)
    return _dumps(_clip_retrieve(payload))


@mcp.tool()
def evaluation_experiments() -> str:
    """Historial de experimentos de evaluación (metadatos, sin traces completos)."""
    payload = _request("GET", "/chat/evaluation/experiments")
    if isinstance(payload, list) and len(payload) > 20:
        payload = payload[:20]
    return _dumps(payload)


if __name__ == "__main__":
    mcp.run(transport="stdio")
