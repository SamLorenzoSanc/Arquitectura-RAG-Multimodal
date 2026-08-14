"""Agentic RAG: el agente decide si consultar la base de conocimiento.

Comparación controlada frente al Hybrid RAG (Dense+BM25+RRF).
"""

from __future__ import annotations

import time
from typing import Any

from openai import OpenAI

from services.rag_service import (
    OLLAMA_API_KEY,
    OLLAMA_BASE_URL,
    RAGService,
    Result,
)


def _looks_like_kb(q: str) -> bool:
    """Por defecto casi siempre consultamos KB; omitir solo saludos vacíos."""
    ql = q.strip().lower()
    if len(ql) < 4:
        return False
    greetings = {"hola", "buenas", "hey", "hi", "hello", "qué tal", "que tal"}
    return ql not in greetings


class AgenticRAGService:
    """Agentic RAG (tool-augmented) solo sobre la base documental."""

    ARCHITECTURE = "agentic_tool_rag"

    SYSTEM_SYNTH = """Eres AgroPS, el asistente documental agrícola.
Has usado herramientas de recuperación. Responde SIEMPRE en español.
Cita fuentes de la base de conocimiento cuando las uses.
Si una herramienta falló o no hay evidencia, dilo; no inventes cifras.

Estructura OBLIGATORIA de cada respuesta (usa exactamente estos títulos):
1. Diagnóstico
2. Procedimiento paso a paso
3. Información técnica
4. Herramientas y recambios
5. Precauciones

Contexto de herramientas:
{tool_context}
"""

    def __init__(self, rag: RAGService | None = None):
        self.rag = rag or RAGService()
        self.client = OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)

    def plan_tools(self, question: str) -> list[dict[str, Any]]:
        if _looks_like_kb(question):
            return [
                {
                    "tool": "search_knowledge_base",
                    "reason": "Recuperar normativa/manuales/conocimiento del tenant",
                    "args": {},
                }
            ]
        return [
            {
                "tool": "search_knowledge_base",
                "reason": "Consulta general: recuperar contexto de KB",
                "args": {},
            }
        ]

    async def _tool_search_kb(
        self,
        question: str,
        tenant_id: str,
        collections: list[str] | None,
    ) -> dict[str, Any]:
        retrieval = await self.rag.fetch_context(
            question,
            tenant_id=tenant_id,
            collections=collections,
            use_reranking=False,
            use_query_rewrite=False,
        )
        chunks = retrieval.get("chunks") or []
        summary_parts = []
        for i, ch in enumerate(chunks[:5], start=1):
            src = (ch.metadata or {}).get("source", "doc")
            summary_parts.append(f"[{i}] ({src}) {ch.page_content[:400]}")
        return {
            "ok": True,
            "chunks": chunks,
            "n_chunks": len(chunks),
            "summary": "\n".join(summary_parts) or "Sin fragmentos relevantes.",
            "retrieval": retrieval.get("retrieval"),
            "retrieval_details": retrieval,
        }

    async def answer(
        self,
        question: str,
        *,
        tenant_id: str,
        collections: list[str] | None = None,
        model: str | None = None,
        history: list | None = None,
        organization_name: str = "AgroTech",
    ) -> dict[str, Any]:
        t0 = time.time()
        active_model = model or self.rag.model
        plan = self.plan_tools(question)
        trace: list[dict[str, Any]] = []
        chunks: list[Result] = []
        tool_blocks: list[str] = []
        retrieval_info = None
        retrieval_details = None

        for step in plan:
            tool = step["tool"]
            t_tool = time.time()
            if tool == "search_knowledge_base":
                out = await self._tool_search_kb(question, tenant_id, collections)
                if out.get("chunks"):
                    chunks = out["chunks"]
                retrieval_info = out.get("retrieval")
                retrieval_details = out.get("retrieval_details")
            else:
                out = {"ok": False, "summary": f"Herramienta desconocida: {tool}"}

            latency = (time.time() - t_tool) * 1000
            summary = out.get("summary", "")
            tool_blocks.append(f"### {tool}\n{summary}")
            trace.append(
                {
                    "tool": tool,
                    "reason": step.get("reason"),
                    "ok": bool(out.get("ok")),
                    "latency_ms": round(latency, 1),
                    "summary": summary[:500],
                }
            )

        tool_context = "\n\n".join(tool_blocks) if tool_blocks else "Sin herramientas."
        system = self.SYSTEM_SYNTH.format(tool_context=tool_context)
        messages = [{"role": "system", "content": system}]
        for msg in (history or [])[-6:]:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": question})

        t_gen = time.time()
        response = await self.rag._create_completion(active_model, messages)
        gen_ms = (time.time() - t_gen) * 1000
        answer = response.choices[0].message.content or ""

        related = self.rag.generate_related_questions(question, chunks)

        total_ms = (time.time() - t0) * 1000
        agent_meta = {
            "architecture": self.ARCHITECTURE,
            "label": "Agentic RAG (tool-augmented)",
            "tools_planned": [s["tool"] for s in plan],
            "tools_executed": [t["tool"] for t in trace],
            "agent_trace": trace,
            "organization": organization_name,
            "timings_ms": {
                "generation": round(gen_ms, 1),
                "total": round(total_ms, 1),
            },
        }

        if retrieval_details is None:
            retrieval_details = {"retrieval": retrieval_info or {}, "chunks": chunks}
        retrieval_details["agentic"] = agent_meta
        retrieval_details["architecture"] = self.ARCHITECTURE

        if retrieval_info is None:
            retrieval_info = {
                "original_query": question,
                "rewritten_query": question,
                "retrieved_chunks": len(chunks),
                "rewritten_chunks": 0,
                "merged_chunks": len(chunks),
                "final_chunks": len(chunks),
                "retrieval_k": self.rag.retrieval_k,
                "final_k": self.rag.final_k,
                "reranking": False,
            }
        retrieval_info["architecture"] = self.ARCHITECTURE
        retrieval_info["agent_tools"] = [t["tool"] for t in trace]

        return {
            "answer": answer,
            "chunks": chunks,
            "retrieval": retrieval_info,
            "retrieval_details": retrieval_details,
            "related_questions": related,
            "agent_trace": trace,
            "architecture": self.ARCHITECTURE,
            "latency_ms": round(total_ms, 1),
        }


async def run_hybrid_answer(
    rag: RAGService,
    question: str,
    *,
    tenant_id: str,
    collections: list[str] | None,
    model: str | None,
    history: list | None,
    use_reranking: bool = False,
    use_query_rewrite: bool = False,
) -> dict[str, Any]:
    t0 = time.time()
    result = await rag.answer(
        question=question,
        history=history,
        tenant_id=tenant_id,
        collections=collections,
        model=model,
        use_reranking=use_reranking,
        use_query_rewrite=use_query_rewrite,
    )
    latency = (time.time() - t0) * 1000
    details = result.get("retrieval_details") or {}
    details["architecture"] = "hybrid_dense_bm25_rrf"
    details["label"] = "Hybrid RAG (Dense + BM25 + RRF)"
    result["retrieval_details"] = details
    if result.get("retrieval") is not None:
        result["retrieval"]["architecture"] = "hybrid_dense_bm25_rrf"
    result["architecture"] = "hybrid_dense_bm25_rrf"
    result["latency_ms"] = round(latency, 1)
    result["agent_trace"] = None
    return result


def pack_mode_side(result: dict[str, Any], mode: str) -> dict[str, Any]:
    """Serializa un lado de la comparación para la API."""
    chunks_out = []
    for chunk in result.get("chunks") or []:
        if isinstance(chunk, dict):
            chunks_out.append(chunk)
        else:
            chunks_out.append(
                {
                    "type": getattr(chunk, "type", "chunk"),
                    "page_content": getattr(chunk, "page_content", ""),
                    "metadata": getattr(chunk, "metadata", {}) or {},
                }
            )
    return {
        "mode": mode,
        "architecture": result.get("architecture"),
        "answer": result.get("answer") or "",
        "context": chunks_out,
        "retrieval": result.get("retrieval"),
        "retrieval_details": result.get("retrieval_details"),
        "agent_trace": result.get("agent_trace"),
        "related_questions": result.get("related_questions") or [],
        "latency_ms": result.get("latency_ms"),
    }
