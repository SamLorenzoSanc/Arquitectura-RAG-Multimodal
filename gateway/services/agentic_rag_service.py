"""Agentic RAG orquestado con LangGraph sobre el híbrido denso + BM25 + RRF.

Por defecto (RAG_AGENT_FAST=true) el chat hace una recuperación y una
generación: plan heurístico, sin grader LLM ni bucle de reescritura.
Con RAG_AGENT_FAST=false vuelve el planificador, el grade y un reintento.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Literal

from openai import OpenAI
from sqlalchemy import select, text

from models.document import Document
from models.knowledge_base import KnowledgeBase
from rag.adapters.outbound.scope import is_uuid, organization_tenant_ids
from services.agent_graph import (
    AGENT_FAST,
    GRADE_PROMPT,
    REWRITE_PROMPT,
    SEARCH_TOOLS,
    compile_agentic_graph,
    heuristic_grade,
    needs_document_grade,
    parse_binary_grade,
)
from services.agent_sql import (
    AgentSqlError,
    execute_agent_select,
    format_sql_rows,
    sql_schema_card,
    validate_agent_select,
)
from services.database import AsyncSessionLocal
from services.rag_service import (
    OLLAMA_API_KEY,
    OLLAMA_BASE_URL,
    RAG_CHAT_MAX_TOKENS,
    RAG_USE_QUERY_REWRITE,
    RAG_USE_RERANKER,
    RAGService,
)

Intent = Literal[
    "chitchat",
    "inventory",
    "regulation",
    "diagnostic",
    "notebook",
    "lookup",
]

INVENTORY_HINTS = (
    "qué documentos",
    "que documentos",
    "documentos hay",
    "indexados",
    "de qué tratan",
    "de que tratan",
    "qué hay en",
    "que hay en",
    "listado de documentos",
    "listado",
)
REGULATION_HINTS = (
    "pac",
    "posei",
    "bcam",
    "normativa",
    "ayuda",
    "hectárea",
    "hectarea",
    "condicionalidad",
    "sigpac",
    "subvención",
    "subvencion",
    "anexo",
    "artículo",
    "articulo",
    "orden apa",
    "boe",
)
DIAGNOSTIC_HINTS = (
    "amarill",
    "plaga",
    "hoja",
    "hojas",
    "enfermedad",
    "riego",
    "gotero",
    "filtro",
    "trips",
    "mildiu",
    "sigatoka",
    "cloro",
    "carencia",
    "síntoma",
    "sintoma",
    "cochinilla",
    "nematodo",
    "podredumbre",
    "sequía",
    "sequia",
    "qué puede ser",
    "que puede ser",
    "qué hago",
    "que hago",
)
NOTEBOOK_HINTS = (
    "cuaderno",
    "incidencia",
    "documentar",
    "anotar un riego",
    "parte de",
)
LOOKUP_HINTS = (
    "vademecum",
    "vademécum",
    "dosis",
    "plazo",
    "ficha",
    "uso autorizado",
    "usos autorizados",
    "materia activa",
    "sustancia",
    "cultivo autorizado",
    "autorizado en",
    "prohibido",
    "importe",
    "prima",
    "porcentaje",
    "tabla",
    "csv",
    "qué dice",
    "que dice",
    "según el",
    "segun el",
    "cuánto",
    "cuanto",
    "cuáles son",
    "cuales son",
)

TOOL_CHUNK_CHARS = max(
    400, int(os.getenv("RAG_AGENT_CHUNK_CHARS", "800" if AGENT_FAST else "1400"))
)
TOOL_CHUNK_N = max(3, int(os.getenv("RAG_AGENT_CHUNK_N", "4" if AGENT_FAST else "8")))
MAX_AGENT_TOOLS = 3
KNOWN_TOOLS = frozenset(
    {
        "search_knowledge_base",
        "search_regulations",
        "diagnose_crop",
        "list_indexed_documents",
        "query_operational_sql",
        "recall_conversation",
    }
)

PLAN_PROMPT = """Eres el planificador de AgroPS. Eliges herramientas ANTES de responder.
Responde SOLO un JSON válido, sin markdown, con esta forma:
{{"reason":"por qué","tools":[{{"name":"search_knowledge_base","query":"...","reason":"..."}}]}}

Herramientas:
- search_knowledge_base: RAG clásico (denso+BM25+RRF) sobre documentos subidos. query opcional.
- query_operational_sql: datos relacionales (documentos, conversaciones, cuaderno). Incluye "sql" (SELECT) o "goal".
- recall_conversation: memoria de chats previos del usuario. query opcional.
- list_indexed_documents: inventario de archivos.
- search_regulations: atajo de search_knowledge_base para PAC/POSEI.
- diagnose_crop: atajo de search_knowledge_base para síntomas.

Reglas:
- Puedes combinar 1 a 3 herramientas.
- Saludo o charla: tools=[].
- Hechos del corpus (POSEI, vademécum, dosis): search_knowledge_base.
- Conteos, listados, fechas del cuaderno, títulos de conversación: query_operational_sql.
- "lo que hablamos antes", "recuerdas": recall_conversation.
- SQL: solo SELECT. Filtra con :tenant_id (y :user_id si aplica). Sin UUID literales.

Esquema SQL:
{schema}

Pregunta: {question}
"""

SYNTH_FAST = """Eres AgroPS. Responde en español en 4-8 frases.
Cita el archivo. No inventes dosis, plazos, ayudas ni cifras.
Si el contexto no cubre la pregunta, dilo en una frase.

Contexto:
{tool_context}
"""

SYNTH_COMMON = """Eres AgroPS, el asistente de campo para agricultores de Canarias.
Has usado herramientas sobre el corpus de la organización. Responde SIEMPRE en español.
Cita el nombre del archivo cuando uses una fuente. No inventes dosis, plazos, ayudas ni cifras.
Si una herramienta falló, dilo en una frase; no copies errores técnicos.
Si los fragmentos no cubren la pregunta, dilo y indica qué falta en el corpus.
Responde a ESTA pregunta del usuario: no rellenes un esquema que no encaje.

Contexto de herramientas:
{tool_context}
"""

SYNTH_BY_INTENT = {
    "inventory": """El usuario pide el inventario del corpus (qué documentos hay y de qué tratan).
Responde con un listado claro: nombre de archivo, tema en una frase y, si hay descripción, úsala.
No uses el esquema de diagnóstico.""",
    "regulation": """Pregunta de normativa, ayudas o condicionalidad (PAC, POSEI, BCAM, SIGPAC).
Estructura:
1. Respuesta directa
2. Evidencia del corpus (artículos, importes, plazos, requisitos; cita el archivo)
3. Condiciones y excepciones que aparezcan en los fragmentos
4. Límites (qué no está en el corpus)

No uses el esquema de diagnóstico de campo.""",
    "lookup": """Consulta factual sobre fichas, vademécum, tablas, dosis, usos o un dato concreto.
Estructura:
1. Respuesta directa a la pregunta (2-8 frases, con las cifras del corpus)
2. Detalle (cultivos, materias activas, dosis, plazos, filas o apartados relevantes)
3. Fuentes (nombre de archivo de cada dato)
4. Límites (si el fragmento está incompleto o hay varias filas, dilo)

No uses el esquema de diagnóstico salvo que el usuario describa un síntoma.""",
    "notebook": """El usuario quiere documentar un riego, una incidencia o el cuaderno de campo.
Explica el procedimiento con los documentos del corpus. Cita el archivo.
Si no hay plantilla, ofrece un procedimiento genérico marcado como orientación.""",
    "diagnostic": """Problema de campo (síntoma, plaga, riego, carencia). Usa exactamente:
1. Diagnóstico
2. Procedimiento paso a paso
3. Información técnica
4. Herramientas y recambios
5. Precauciones

En «Herramientas y recambios» habla de insumos, EPI, goteros, filtros, sondas o
maquinaria de riego, no de recambios industriales genéricos.""",
    "chitchat": """Saludo o pregunta breve. Responde en 2-4 frases, ofrece ayuda sobre el corpus
y no inventes normativa ni dosis.""",
}


def _looks_like_kb(q: str) -> bool:
    ql = q.strip().lower()
    if len(ql) < 4:
        return False
    greetings = {"hola", "buenas", "hey", "hi", "hello", "qué tal", "que tal"}
    return ql not in greetings


def _contains(question: str, hints: tuple[str, ...]) -> bool:
    ql = question.strip().lower()
    return any(hint in ql for hint in hints)


def classify_intent(question: str) -> Intent:
    """Clasifica la pregunta para elegir herramienta y plantilla de respuesta."""
    if not _looks_like_kb(question):
        return "chitchat"
    if _contains(question, INVENTORY_HINTS):
        return "inventory"
    if _contains(question, NOTEBOOK_HINTS):
        return "notebook"
    lookup = _contains(question, LOOKUP_HINTS)
    diagnostic = _contains(question, DIAGNOSTIC_HINTS)
    regulation = _contains(question, REGULATION_HINTS)
    if lookup and not diagnostic and not regulation:
        return "lookup"
    if regulation:
        return "regulation"
    if diagnostic:
        return "diagnostic"
    return "lookup"


def parse_agent_plan(raw: str) -> list[dict[str, Any]] | None:
    """Devuelve None si el JSON no es usable; lista vacía si el agente no usa tools."""
    blob = (raw or "").strip()
    if blob.startswith("```"):
        blob = re.sub(r"^```(?:json)?", "", blob, flags=re.I).strip()
        blob = blob.rstrip("`").strip()
    start = blob.find("{")
    end = blob.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(blob[start : end + 1])
    except json.JSONDecodeError:
        return None
    tools = data.get("tools")
    if not isinstance(tools, list):
        return None
    reason = str(data.get("reason") or "").strip()
    planned: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in tools[:MAX_AGENT_TOOLS]:
        payload = item if isinstance(item, dict) else {"name": item}
        name = str(payload.get("name") or payload.get("tool") or "").strip()
        if name not in KNOWN_TOOLS or name in seen:
            continue
        seen.add(name)
        planned.append(
            {
                "tool": name,
                "reason": str(payload.get("reason") or reason or "Elegida por el agente"),
                "intent": "agent",
                "args": payload,
                "planner": "llm",
            }
        )
    return planned


def _safe_tool_error(exc: BaseException) -> str:
    text = str(exc)
    if any(
        token in text.lower()
        for token in ("vector", "sqlalchemy", "asyncpg", "psycopg", "[sql:")
    ):
        return (
            "No se pudo comparar el corpus con el embedding actual. "
            "Los documentos siguen en PostgreSQL; reindexa con nomic-embed-text si hace falta."
        )
    return "No se pudo consultar el corpus en este momento."


def _meta(chunk: Any) -> dict[str, Any]:
    if isinstance(chunk, dict):
        return chunk.get("metadata") or {}
    return getattr(chunk, "metadata", None) or {}


def _content(chunk: Any) -> str:
    if isinstance(chunk, dict):
        return chunk.get("page_content") or ""
    return getattr(chunk, "page_content", "") or ""


def _chunk_key(chunk: Any) -> str:
    meta = _meta(chunk)
    for key in ("chunk_id", "id", "document_id"):
        value = meta.get(key)
        if value:
            return str(value)
    return str(id(chunk))


def _merge_chunks(existing: list[Any], incoming: list[Any]) -> list[Any]:
    merged = list(existing)
    seen = {_chunk_key(chunk) for chunk in merged}
    for chunk in incoming:
        key = _chunk_key(chunk)
        if key in seen:
            continue
        seen.add(key)
        merged.append(chunk)
    return merged


def _format_chunk_line(index: int, chunk: Any) -> str:
    meta = _meta(chunk)
    src = meta.get("source") or meta.get("title") or "documento"
    page = meta.get("page")
    score = meta.get("score") or meta.get("rrf_score") or meta.get("distance")
    bits = [f"[{index}]", str(src)]
    if page is not None:
        bits.append(f"p.{page}")
    if isinstance(score, (int, float)):
        bits.append(f"score={score:.3f}")
    header = " | ".join(bits)
    body = _content(chunk).strip()
    if len(body) > TOOL_CHUNK_CHARS:
        body = body[:TOOL_CHUNK_CHARS].rstrip() + "…"
    return f"{header}\n{body}"


def chat_retrieval_strategy(*, use_reranking: bool) -> str:
    if use_reranking:
        return "hybrid_expansion_rrf_rerank"
    return "hybrid_expansion_rrf"


class AgenticRAGService:
    """Agentic RAG con grafo LangGraph y herramientas agrarias sobre el corpus."""

    ARCHITECTURE = "agentic_langgraph_rag"

    def __init__(self, rag: RAGService | None = None):
        self.rag = rag or RAGService()
        self.client = OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)
        self._graph = None

    def plan_tools(self, question: str) -> list[dict[str, Any]]:
        intent = classify_intent(question)
        if intent == "chitchat":
            return []
        if intent == "inventory":
            tools = [
                {
                    "tool": "list_indexed_documents",
                    "reason": "Inventariar documentos subidos por el agricultor",
                    "intent": intent,
                    "args": {},
                }
            ]
            if not AGENT_FAST:
                tools.append(
                    {
                        "tool": "search_knowledge_base",
                        "reason": "Recuperar fragmentos para resumir de qué tratan",
                        "intent": intent,
                        "args": {},
                    }
                )
            return tools
        if intent == "notebook":
            return [
                {
                    "tool": "query_operational_sql",
                    "reason": "Leer incidencias del cuaderno de campo",
                    "intent": intent,
                    "args": {
                        "sql": (
                            "SELECT entry_date, title, category, LEFT(body, 180) AS body "
                            "FROM field_notebook_entries "
                            "WHERE user_id = :user_id OR organization_id = :organization_id "
                            "ORDER BY entry_date DESC LIMIT 15"
                        )
                    },
                },
                {
                    "tool": "search_knowledge_base",
                    "reason": "Procedimiento de cuaderno en el corpus",
                    "intent": intent,
                    "args": {},
                },
            ]
        if intent == "regulation":
            return [
                {
                    "tool": "search_regulations",
                    "reason": "Buscar PAC, POSEI o condicionalidad en el corpus",
                    "intent": intent,
                    "args": {},
                }
            ]
        if intent == "diagnostic":
            return [
                {
                    "tool": "diagnose_crop",
                    "reason": "Diagnosticar síntoma o incidencia de campo",
                    "intent": intent,
                    "args": {},
                }
            ]
        return [
            {
                "tool": "search_knowledge_base",
                "reason": "Recuperar normativa, fichas y manuales de la organización",
                "intent": intent,
                "args": {},
            }
        ]

    async def _plan_with_llm(
        self,
        question: str,
        *,
        model: str,
        temperature: float | None = None,
    ) -> list[dict[str, Any]]:
        if AGENT_FAST:
            fallback = self.plan_tools(question)
            for step in fallback:
                step["planner"] = "heuristic"
            return fallback
        messages = [
            {
                "role": "system",
                "content": PLAN_PROMPT.format(
                    schema=sql_schema_card(), question=question
                ),
            },
            {"role": "user", "content": question},
        ]
        try:
            response = await self.rag._create_completion(
                model, messages, temperature=0 if temperature is None else temperature
            )
            raw = response.choices[0].message.content or ""
            parsed = parse_agent_plan(raw)
        except Exception:
            parsed = None
        if parsed is None:
            fallback = self.plan_tools(question)
            for step in fallback:
                step["planner"] = "heuristic"
            return fallback
        if not parsed and classify_intent(question) != "chitchat":
            fallback = self.plan_tools(question)
            for step in fallback:
                step["planner"] = "heuristic"
            return fallback
        return parsed

    def _synth_prompt(self, intent: Intent, tool_context: str) -> str:
        if AGENT_FAST:
            return SYNTH_FAST.format(tool_context=tool_context)
        extra = SYNTH_BY_INTENT.get(intent, SYNTH_BY_INTENT["lookup"])
        return f"{SYNTH_COMMON.format(tool_context=tool_context)}\n{extra}"

    async def _search(
        self,
        question: str,
        tenant_id: str,
        collections: list[str] | None,
        extra_query: str = "",
        *,
        use_reranking: bool | None = None,
        use_query_rewrite: bool | None = None,
    ) -> dict[str, Any]:
        query = f"{question} {extra_query}".strip()
        do_rerank = RAG_USE_RERANKER if use_reranking is None else bool(use_reranking)
        allow_rewrite = (
            RAG_USE_QUERY_REWRITE
            if use_query_rewrite is None
            else bool(use_query_rewrite)
        )
        strategy = chat_retrieval_strategy(use_reranking=do_rerank)
        try:
            retrieval = await self.rag.fetch_context(
                query,
                tenant_id=tenant_id,
                collections=collections,
                use_reranking=do_rerank,
                use_query_rewrite=allow_rewrite,
                retrieval_strategy=strategy,
            )
        except Exception as exc:
            return {
                "ok": False,
                "chunks": [],
                "n_chunks": 0,
                "summary": _safe_tool_error(exc),
                "retrieval": None,
                "retrieval_details": None,
            }

        chunks = retrieval.get("chunks") or []
        summary_parts = [
            _format_chunk_line(i, ch) for i, ch in enumerate(chunks[:TOOL_CHUNK_N], start=1)
        ]
        return {
            "ok": True,
            "chunks": chunks,
            "n_chunks": len(chunks),
            "summary": "\n\n".join(summary_parts) or "Sin fragmentos relevantes.",
            "retrieval": retrieval.get("retrieval"),
            "retrieval_details": retrieval,
        }

    async def _tool_search_kb(
        self,
        question: str,
        tenant_id: str,
        collections: list[str] | None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return await self._search(question, tenant_id, collections, **kwargs)

    async def _tool_search_regulations(
        self,
        question: str,
        tenant_id: str,
        collections: list[str] | None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return await self._search(question, tenant_id, collections, **kwargs)

    async def _tool_diagnose_crop(
        self,
        question: str,
        tenant_id: str,
        collections: list[str] | None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return await self._search(question, tenant_id, collections, **kwargs)

    async def _tool_list_documents(
        self,
        tenant_id: str,
        collections: list[str] | None,
    ) -> dict[str, Any]:
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(Document, KnowledgeBase.name).join(
                    KnowledgeBase, KnowledgeBase.id == Document.knowledge_base_id
                )
                if is_uuid(tenant_id):
                    stmt = stmt.where(
                        Document.tenant_id.in_(organization_tenant_ids(tenant_id))
                    )
                else:
                    stmt = stmt.where(Document.tenant_id == tenant_id)
                if collections:
                    stmt = stmt.where(Document.knowledge_base_id.in_(collections))
                stmt = stmt.order_by(Document.uploaded_at.desc()).limit(40)
                rows = (await session.execute(stmt)).all()
        except Exception as exc:
            return {
                "ok": False,
                "chunks": [],
                "summary": _safe_tool_error(exc),
            }

        if not rows:
            return {
                "ok": True,
                "chunks": [],
                "summary": "No hay documentos indexados en esta organización.",
            }

        lines = []
        for document, kb_name in rows:
            title = (document.title or document.filename or "documento").strip()
            desc = (document.description or "").strip()
            extra = f" — {desc[:140]}" if desc else ""
            lines.append(f"- {title} (base: {kb_name}){extra}")
        return {
            "ok": True,
            "chunks": [],
            "n_chunks": len(lines),
            "summary": "Documentos indexados en la organización:\n" + "\n".join(lines),
        }

    async def _draft_sql(
        self, goal: str, *, model: str, temperature: float | None = None
    ) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "Escribe UN SELECT de PostgreSQL. Sin markdown. "
                    "Usa :tenant_id, :user_id, :organization_id o :conversation_id. "
                    f"{sql_schema_card()}"
                ),
            },
            {"role": "user", "content": goal},
        ]
        response = await self.rag._create_completion(
            model, messages, temperature=0 if temperature is None else temperature
        )
        raw = response.choices[0].message.content or ""
        raw = re.sub(r"^```(?:sql)?", "", raw.strip(), flags=re.I).strip().rstrip("`")
        return validate_agent_select(raw)

    async def _tool_query_sql(
        self,
        question: str,
        *,
        tenant_id: str,
        user_id: str | None,
        organization_id: str | None,
        conversation_id: str | None,
        args: dict[str, Any],
        model: str,
        temperature: float | None,
    ) -> dict[str, Any]:
        sql = str(args.get("sql") or args.get("query") or "").strip()
        goal = str(args.get("goal") or question).strip()
        try:
            if not sql:
                sql = await self._draft_sql(goal, model=model, temperature=temperature)
            async with AsyncSessionLocal() as session:
                rows = await execute_agent_select(
                    session,
                    sql,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    organization_id=organization_id,
                    conversation_id=conversation_id,
                )
                await session.rollback()
        except AgentSqlError as exc:
            return {"ok": False, "chunks": [], "summary": f"SQL rechazado: {exc}"}
        except Exception as exc:
            return {"ok": False, "chunks": [], "summary": _safe_tool_error(exc)}
        preview = sql if len(sql) < 280 else sql[:280] + "…"
        return {
            "ok": True,
            "chunks": [],
            "n_chunks": len(rows),
            "summary": f"SQL:\n{preview}\n\nResultado:\n{format_sql_rows(rows)}",
        }

    async def _tool_recall_conversation(
        self,
        question: str,
        *,
        tenant_id: str,
        user_id: str | None,
        conversation_id: str | None,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        needle = str(args.get("query") or question).strip()
        like = f"%{needle[:80]}%" if needle else "%"
        if not user_id:
            return {
                "ok": False,
                "chunks": [],
                "summary": "No hay usuario para consultar la memoria de conversación.",
            }
        try:
            async with AsyncSessionLocal() as session:
                if conversation_id:
                    result = await session.execute(
                        text(
                            """
                            SELECT m.role, LEFT(m.content, 400) AS content, m.created_at
                            FROM messages m
                            JOIN conversations c ON c.id = m.conversation_id
                            WHERE c.tenant_id = :tenant_id
                              AND c.user_id = :user_id
                              AND c.id = :conversation_id
                              AND m.content ILIKE :needle
                            ORDER BY m.created_at DESC
                            LIMIT 12
                            """
                        ),
                        {
                            "tenant_id": tenant_id,
                            "user_id": user_id,
                            "conversation_id": conversation_id,
                            "needle": like,
                        },
                    )
                else:
                    result = await session.execute(
                        text(
                            """
                            SELECT m.role, LEFT(m.content, 400) AS content, m.created_at
                            FROM messages m
                            JOIN conversations c ON c.id = m.conversation_id
                            WHERE c.tenant_id = :tenant_id
                              AND c.user_id = :user_id
                              AND m.content ILIKE :needle
                            ORDER BY m.created_at DESC
                            LIMIT 12
                            """
                        ),
                        {
                            "tenant_id": tenant_id,
                            "user_id": user_id,
                            "needle": like,
                        },
                    )
                rows = [dict(row) for row in result.mappings().all()]
                if not rows and conversation_id:
                    result = await session.execute(
                        text(
                            """
                            SELECT m.role, LEFT(m.content, 400) AS content, m.created_at
                            FROM messages m
                            JOIN conversations c ON c.id = m.conversation_id
                            WHERE c.tenant_id = :tenant_id
                              AND c.user_id = :user_id
                              AND c.id = :conversation_id
                            ORDER BY m.created_at DESC
                            LIMIT 8
                            """
                        ),
                        {
                            "tenant_id": tenant_id,
                            "user_id": user_id,
                            "conversation_id": conversation_id,
                        },
                    )
                    rows = [dict(row) for row in result.mappings().all()]
        except Exception as exc:
            return {"ok": False, "chunks": [], "summary": _safe_tool_error(exc)}
        if not rows:
            return {
                "ok": True,
                "chunks": [],
                "summary": "No hay mensajes previos relevantes en la memoria.",
            }
        lines = [
            f"- {row.get('role')}: {row.get('content')}"
            for row in reversed(rows)
        ]
        return {
            "ok": True,
            "chunks": [],
            "n_chunks": len(rows),
            "summary": "Memoria de conversación:\n" + "\n".join(lines),
        }

    def _graph_compiled(self):
        if self._graph is None:
            self._graph = compile_agentic_graph(self)
        return self._graph

    async def _grade_documents(self, question: str, context: str) -> str:
        compact = (context or "").strip()
        if not compact or compact in (
            "Sin herramientas.",
            "Sin fragmentos relevantes.",
        ):
            return "no"
        messages = [
            {
                "role": "user",
                "content": GRADE_PROMPT.format(
                    question=question, context=compact[:6000]
                ),
            }
        ]
        try:
            response = await self.rag._create_completion(
                self.rag.model, messages, temperature=0
            )
            parsed = parse_binary_grade(response.choices[0].message.content or "")
        except Exception:
            parsed = None
        if parsed:
            return parsed
        return "yes" if len(compact) > 80 else "no"

    async def _rewrite_question(self, question: str) -> str:
        messages = [
            {"role": "user", "content": REWRITE_PROMPT.format(question=question)}
        ]
        try:
            response = await self.rag._create_completion(
                self.rag.model, messages, temperature=0
            )
            improved = (response.choices[0].message.content or "").strip()
            improved = re.sub(r'^["«]+|["»]+$', "", improved).strip()
            first = improved.splitlines()[0].strip() if improved else ""
            if 8 <= len(first) <= 400:
                return first
        except Exception:
            pass
        return question

    async def _execute_plan(
        self,
        *,
        question: str,
        plan: list[dict[str, Any]],
        tenant_id: str,
        collections: list[str] | None,
        model: str,
        user_id: str | None,
        organization_id: str | None,
        conversation_id: str | None,
        intent: str,
        use_reranking: bool | None,
        use_query_rewrite: bool | None,
        temperature: float | None,
        prior_trace: list[dict[str, Any]] | None = None,
        prior_chunks: list[Any] | None = None,
    ) -> dict[str, Any]:
        trace: list[dict[str, Any]] = list(prior_trace or [])
        chunks: list[Any] = list(prior_chunks or [])
        tool_blocks: list[str] = []
        retrieval_info = None
        retrieval_details = None
        search_kwargs = {
            "use_reranking": use_reranking,
            "use_query_rewrite": use_query_rewrite,
        }
        scope = {
            "tenant_id": tenant_id,
            "user_id": str(user_id) if user_id else None,
            "organization_id": str(organization_id) if organization_id else None,
            "conversation_id": str(conversation_id) if conversation_id else None,
        }
        for step in plan:
            tool = step["tool"]
            args = step.get("args") if isinstance(step.get("args"), dict) else {}
            t_tool = time.time()
            if tool == "list_indexed_documents":
                out = await self._tool_list_documents(tenant_id, collections)
            elif tool == "search_regulations":
                out = await self._tool_search_regulations(
                    str(args.get("query") or question),
                    tenant_id,
                    collections,
                    **search_kwargs,
                )
            elif tool == "diagnose_crop":
                out = await self._tool_diagnose_crop(
                    str(args.get("query") or question),
                    tenant_id,
                    collections,
                    **search_kwargs,
                )
            elif tool == "search_knowledge_base":
                out = await self._tool_search_kb(
                    str(args.get("query") or question),
                    tenant_id,
                    collections,
                    **search_kwargs,
                )
            elif tool == "query_operational_sql":
                out = await self._tool_query_sql(
                    question,
                    tenant_id=tenant_id,
                    user_id=scope["user_id"],
                    organization_id=scope["organization_id"],
                    conversation_id=scope["conversation_id"],
                    args=args,
                    model=model,
                    temperature=temperature,
                )
            elif tool == "recall_conversation":
                out = await self._tool_recall_conversation(
                    question,
                    tenant_id=tenant_id,
                    user_id=scope["user_id"],
                    conversation_id=scope["conversation_id"],
                    args=args,
                )
            else:
                out = {"ok": False, "summary": f"Herramienta desconocida: {tool}"}

            if out.get("chunks"):
                chunks = _merge_chunks(chunks, out["chunks"])
            if out.get("retrieval") is not None:
                retrieval_info = out.get("retrieval")
            if out.get("retrieval_details") is not None:
                retrieval_details = out.get("retrieval_details")

            latency = (time.time() - t_tool) * 1000
            summary = out.get("summary", "")
            tool_blocks.append(f"### {tool}\n{summary}")
            trace.append(
                {
                    "tool": tool,
                    "reason": step.get("reason"),
                    "intent": step.get("intent") or intent,
                    "ok": bool(out.get("ok")),
                    "latency_ms": round(latency, 1),
                    "summary": summary[:800],
                    "n_chunks": out.get("n_chunks") or 0,
                    "planner": step.get("planner") or "heuristic",
                }
            )
        return {
            "trace": trace,
            "chunks": chunks,
            "tool_blocks": tool_blocks,
            "retrieval_info": retrieval_info,
            "retrieval_details": retrieval_details,
        }

    async def graph_generate_query_or_respond(self, state: dict[str, Any]) -> dict[str, Any]:
        question = state.get("active_question") or state["question"]
        intent = classify_intent(question)
        plan = await self._plan_with_llm(
            question, model=state["model"], temperature=state.get("temperature")
        )
        if int(state.get("rewrite_count") or 0) > 0 and not any(
            step.get("tool") in SEARCH_TOOLS for step in plan
        ):
            plan = [
                {
                    "tool": "search_knowledge_base",
                    "reason": "Reintento tras un grade negativo",
                    "intent": intent,
                    "args": {"query": question},
                    "planner": "rewrite_loop",
                }
            ]
        return {"intent": intent, "plan": plan, "active_question": question}

    async def graph_retrieve(self, state: dict[str, Any]) -> dict[str, Any]:
        executed = await self._execute_plan(
            question=state.get("active_question") or state["question"],
            plan=state.get("plan") or [],
            tenant_id=state["tenant_id"],
            collections=state.get("collections"),
            model=state["model"],
            user_id=state.get("user_id"),
            organization_id=state.get("organization_id"),
            conversation_id=state.get("conversation_id"),
            intent=state.get("intent") or "lookup",
            use_reranking=state.get("use_reranking"),
            use_query_rewrite=False if AGENT_FAST else state.get("use_query_rewrite"),
            temperature=state.get("temperature"),
            prior_trace=state.get("trace"),
        )
        grade = "yes"
        context = "\n\n".join(executed["tool_blocks"])
        t_grade = time.time()
        should_grade = needs_document_grade(state.get("plan"))
        if should_grade and not AGENT_FAST:
            grade = await self._grade_documents(state["question"], context)
            grade_planner = "langgraph"
        else:
            grade = heuristic_grade(len(executed.get("chunks") or []), context)
            grade_planner = "heuristic"
        if should_grade:
            executed["trace"].append(
                {
                    "tool": "grade_documents",
                    "reason": f"Relevancia del contexto: {grade}",
                    "intent": state.get("intent") or "lookup",
                    "ok": True,
                    "latency_ms": round((time.time() - t_grade) * 1000, 1),
                    "summary": grade,
                    "n_chunks": len(executed.get("chunks") or []),
                    "planner": grade_planner,
                }
            )
        return {**executed, "grade": grade}

    async def graph_rewrite_question(self, state: dict[str, Any]) -> dict[str, Any]:
        current = state.get("active_question") or state["question"]
        t0 = time.time()
        improved = await self._rewrite_question(current)
        trace = list(state.get("trace") or [])
        trace.append(
            {
                "tool": "rewrite_question",
                "reason": "El grader marcó el contexto como irrelevante",
                "intent": state.get("intent") or "lookup",
                "ok": True,
                "latency_ms": round((time.time() - t0) * 1000, 1),
                "summary": improved[:800],
                "n_chunks": 0,
                "planner": "langgraph",
            }
        )
        return {
            "active_question": improved,
            "rewrite_count": int(state.get("rewrite_count") or 0) + 1,
            "trace": trace,
            "plan": [],
        }

    async def graph_generate_answer(self, state: dict[str, Any]) -> dict[str, Any]:
        intent = state.get("intent") or classify_intent(state["question"])
        tool_context = (
            "\n\n".join(state.get("tool_blocks") or []) or "Sin herramientas."
        )
        system = self._synth_prompt(intent, tool_context[:4500])
        messages = [{"role": "system", "content": system}]
        history_n = 2 if AGENT_FAST else 6
        for msg in (state.get("history") or [])[-history_n:]:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": state["question"]})
        t_gen = time.time()
        response = await self.rag._create_completion(
            state["model"],
            messages,
            temperature=state.get("temperature"),
            max_tokens=RAG_CHAT_MAX_TOKENS if AGENT_FAST else None,
        )
        answer = response.choices[0].message.content or ""
        chunks = state.get("chunks") or []
        related = self.rag.generate_related_questions(state["question"], chunks)
        return {
            "answer": answer,
            "related_questions": related,
            "gen_ms": (time.time() - t_gen) * 1000,
            "intent": intent,
        }

    def _result_from_graph_state(
        self,
        state: dict[str, Any],
        *,
        t0: float,
        use_reranking: bool | None,
        organization_name: str,
        question: str,
    ) -> dict[str, Any]:
        plan = state.get("plan") or []
        trace = state.get("trace") or []
        chunks = state.get("chunks") or []
        retrieval_info = state.get("retrieval_info")
        retrieval_details = state.get("retrieval_details")
        intent = state.get("intent") or classify_intent(question)
        total_ms = (time.time() - t0) * 1000
        strategy = chat_retrieval_strategy(
            use_reranking=RAG_USE_RERANKER if use_reranking is None else bool(use_reranking)
        )
        agent_meta = {
            "architecture": self.ARCHITECTURE,
            "label": (
                "Agentic RAG (LangGraph: recuperar o responder; grade y reescritura)"
            ),
            "intent": intent,
            "retrieval_strategy": strategy,
            "tools_planned": [step["tool"] for step in plan],
            "tools_executed": [item["tool"] for item in trace],
            "planner": "langgraph",
            "grade": state.get("grade"),
            "rewritten_query": state.get("active_question") or question,
            "agent_trace": trace,
            "organization": organization_name,
            "timings_ms": {
                "generation": round(float(state.get("gen_ms") or 0), 1),
                "total": round(total_ms, 1),
            },
        }
        if retrieval_details is None:
            retrieval_details = {"retrieval": retrieval_info or {}, "chunks": chunks}
        retrieval_details["agentic"] = agent_meta
        retrieval_details["architecture"] = self.ARCHITECTURE
        retrieval_details["chunks"] = chunks
        if retrieval_info is None:
            retrieval_info = {
                "original_query": question,
                "rewritten_query": state.get("active_question") or question,
                "retrieved_chunks": len(chunks),
                "rewritten_chunks": 0,
                "merged_chunks": len(chunks),
                "final_chunks": len(chunks),
                "retrieval_k": self.rag.retrieval_k,
                "final_k": self.rag.final_k,
                "reranking": bool(
                    RAG_USE_RERANKER if use_reranking is None else use_reranking
                ),
            }
        retrieval_info["architecture"] = self.ARCHITECTURE
        retrieval_info["agent_tools"] = [item["tool"] for item in trace]
        retrieval_info["intent"] = intent
        retrieval_info["strategy"] = strategy
        return {
            "answer": state.get("answer") or "",
            "chunks": chunks,
            "retrieval": retrieval_info,
            "retrieval_details": retrieval_details,
            "related_questions": state.get("related_questions") or [],
            "agent_trace": trace,
            "architecture": self.ARCHITECTURE,
            "latency_ms": round(total_ms, 1),
        }

    async def answer(
        self,
        question: str,
        *,
        tenant_id: str,
        collections: list[str] | None = None,
        model: str | None = None,
        history: list | None = None,
        organization_name: str = "AgroPS",
        conversation_id: str | None = None,
        user_id: str | None = None,
        organization_id: str | None = None,
        use_reranking: bool | None = None,
        use_query_rewrite: bool | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        t0 = time.time()
        active_model = model or self.rag.model
        initial = {
            "question": question,
            "active_question": question,
            "tenant_id": tenant_id,
            "collections": collections,
            "model": active_model,
            "history": history or [],
            "organization_name": organization_name,
            "conversation_id": str(conversation_id) if conversation_id else None,
            "user_id": str(user_id) if user_id else None,
            "organization_id": str(organization_id) if organization_id else None,
            "use_reranking": use_reranking,
            "use_query_rewrite": use_query_rewrite,
            "temperature": temperature,
            "rewrite_count": 0,
            "trace": [],
            "plan": [],
            "tool_blocks": [],
            "chunks": [],
        }
        final = await self._graph_compiled().ainvoke(initial)
        return self._result_from_graph_state(
            final,
            t0=t0,
            use_reranking=use_reranking,
            organization_name=organization_name,
            question=question,
        )


async def run_hybrid_answer(
    rag: RAGService,
    question: str,
    *,
    tenant_id: str,
    collections: list[str] | None,
    model: str | None,
    history: list | None,
    use_reranking: bool | None = None,
    use_query_rewrite: bool | None = None,
    retrieval_strategy: str | None = None,
    temperature: float | None = None,
) -> dict[str, Any]:
    t0 = time.time()
    do_rerank = RAG_USE_RERANKER if use_reranking is None else bool(use_reranking)
    strategy = retrieval_strategy or chat_retrieval_strategy(use_reranking=do_rerank)
    result = await rag.answer(
        question=question,
        history=history,
        tenant_id=tenant_id,
        collections=collections,
        model=model,
        use_reranking=use_reranking,
        use_query_rewrite=use_query_rewrite,
        retrieval_strategy=strategy,
        temperature=temperature,
    )
    latency = (time.time() - t0) * 1000
    details = result.get("retrieval_details") or {}
    details["architecture"] = "hybrid_expansion_rrf"
    details["label"] = "Hybrid RAG (Dense + BM25 + RRF + expansión léxica)"
    result["retrieval_details"] = details
    if result.get("retrieval") is not None:
        result["retrieval"]["architecture"] = "hybrid_expansion_rrf"
        result["retrieval"]["strategy"] = strategy
    result["architecture"] = "hybrid_expansion_rrf"
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
