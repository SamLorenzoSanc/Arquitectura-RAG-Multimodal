from __future__ import annotations

import re

from rag.domain.entities import RetrievedChunk

TEMPLATES = [
    "¿Qué dice el corpus exactamente sobre {topic}?",
    "¿Hay dosis, plazos, importes o requisitos ligados a {topic}?",
    "¿Qué documentos de la organización cubren {topic}?",
    "¿Cómo se aplica {topic} en Canarias (PAC, POSEI o ficha de uso)?",
    "¿Qué precauciones o límites aparecen para {topic}?",
]

FALLBACKS = [
    "Las hojas se están poniendo amarillas: ¿qué puede ser y qué hago?",
    "El riego no llega igual a todas las plantas: ¿cómo lo reviso?",
    "Veo manchas o insectos en la hoja: ¿cómo identifico la plaga y cómo la trato?",
    "¿Cómo deshijo el plátano paso a paso y con qué herramientas?",
    "Las plantas se marchitan con el calor o el viento: ¿qué hago ahora?",
]


def _norm(text: str) -> str:
    return " ".join((text or "").lower().split())


def _meta_id(chunk: RetrievedChunk, key: str) -> str:
    value = (chunk.metadata or {}).get(key)
    return str(value).strip() if value else ""


def topic_from_chunk(chunk: RetrievedChunk) -> str | None:
    meta = chunk.metadata or {}
    for key in ("headline", "title", "source"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            topic = value.replace(".pdf", "").replace("_", " ").strip()
            if len(topic) >= 4:
                return topic[:80]
    text = (chunk.page_content or "").replace("\n", " ").strip()
    if not text:
        return None
    first = re.split(r"[.?!\n]", text, maxsplit=1)[0].strip()
    words = [w for w in first.split() if len(w) > 2][:8]
    topic = " ".join(words).strip(" -:;,")
    return topic[:80] if len(topic) >= 4 else None


def select_related_neighbors(
    neighbors: list[RetrievedChunk],
    *,
    exclude_chunk_ids: set[str],
    exclude_document_ids: set[str],
    limit: int,
) -> list[RetrievedChunk]:
    """Vecinos ya ordenados por distancia coseno; se excluye el ítem actual."""
    if limit <= 0:
        return []
    picked: list[RetrievedChunk] = []
    seen_docs: set[str] = set()

    def take(chunk: RetrievedChunk, *, skip_docs: bool) -> bool:
        chunk_id = _meta_id(chunk, "chunk_id")
        document_id = _meta_id(chunk, "document_id")
        if chunk_id and chunk_id in exclude_chunk_ids:
            return False
        if skip_docs and document_id and document_id in exclude_document_ids:
            return False
        if document_id and document_id in seen_docs:
            return False
        if document_id:
            seen_docs.add(document_id)
        picked.append(chunk)
        return len(picked) >= limit

    for chunk in neighbors:
        if take(chunk, skip_docs=True):
            return picked
    for chunk in neighbors:
        if take(chunk, skip_docs=False):
            return picked
    return picked


def questions_from_neighbors(
    question: str,
    neighbors: list[RetrievedChunk],
    max_questions: int,
) -> list[str]:
    if max_questions <= 0:
        return []
    seen = {_norm(question)}
    out: list[str] = []
    for i, chunk in enumerate(neighbors):
        topic = topic_from_chunk(chunk)
        if not topic or _norm(topic) in seen:
            continue
        seen.add(_norm(topic))
        candidate = TEMPLATES[i % len(TEMPLATES)].format(topic=topic)
        if _norm(candidate) in seen:
            continue
        seen.add(_norm(candidate))
        out.append(candidate)
        if len(out) >= max_questions:
            return out
    for fallback in FALLBACKS:
        if _norm(fallback) in seen:
            continue
        out.append(fallback)
        if len(out) >= max_questions:
            break
    return out


def generate_related_questions(
    question: str,
    chunks: list[RetrievedChunk],
    max_questions: int = 5,
    neighbors: list[RetrievedChunk] | None = None,
) -> list[str]:
    """Preguntas relacionadas por k-NN coseno (vecinos densos), no por RRF.

    `neighbors` debe venir de una búsqueda densa (embed + distancia coseno).
    Se excluyen los chunks/documentos ya usados en la respuesta, como
    `excludeLessonId` en un buscador de ítems similares.
    """
    if max_questions <= 0:
        return []
    pool = neighbors if neighbors is not None else chunks
    exclude_chunk_ids = {_meta_id(chunk, "chunk_id") for chunk in chunks} - {""}
    exclude_document_ids = {_meta_id(chunk, "document_id") for chunk in chunks} - {""}
    related = select_related_neighbors(
        pool,
        exclude_chunk_ids=exclude_chunk_ids,
        exclude_document_ids=exclude_document_ids,
        limit=max_questions,
    )
    return questions_from_neighbors(question, related, max_questions)
