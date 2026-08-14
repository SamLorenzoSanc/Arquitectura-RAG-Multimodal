from __future__ import annotations

import re

from rag.domain.entities import RetrievedChunk


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


def generate_related_questions(
    question: str,
    chunks: list[RetrievedChunk],
    max_questions: int = 5,
) -> list[str]:
    templates = [
        "¿Cuáles son los pasos para resolver un problema de {topic}?",
        "¿Qué herramientas y recambios se necesitan para {topic}?",
        "¿Qué datos técnicos (dosis, tiempos, temperaturas) aplican a {topic}?",
        "¿Cómo diagnosticar y corregir un fallo de {topic}?",
        "¿Qué precauciones de seguridad hay al trabajar {topic}?",
    ]
    seen: set[str] = set()
    out: list[str] = []
    seen.add(" ".join(question.lower().split()))

    topics: list[str] = []
    for chunk in chunks:
        topic = topic_from_chunk(chunk)
        if not topic:
            continue
        key = topic.lower()
        if key in seen:
            continue
        seen.add(key)
        topics.append(topic)

    for i, topic in enumerate(topics):
        candidate = templates[i % len(templates)].format(topic=topic)
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(candidate)
        if len(out) >= max_questions:
            return out

    fallbacks = [
        "Las hojas se están poniendo amarillas: ¿qué puede ser y qué hago?",
        "El riego no llega igual a todas las plantas: ¿cómo lo reviso?",
        "Veo manchas o insectos en la hoja: ¿cómo identifico la plaga y cómo la trato?",
        "¿Cómo deshijo el plátano paso a paso y con qué herramientas?",
        "Las plantas se marchitan con el calor o el viento: ¿qué hago ahora?",
    ]
    for fb in fallbacks:
        if fb.lower() in seen:
            continue
        out.append(fb)
        if len(out) >= max_questions:
            break
    return out
