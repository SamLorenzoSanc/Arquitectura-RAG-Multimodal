"""Extracción de preguntas de evaluación a partir de un documento subido."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")
GENERATION_MODEL = os.getenv("RAG_GENERATION_MODEL", "llama3.2:latest")
MAX_CHARS = 9000

EVAL_CATEGORIES = (
    "direct_fact",
    "temporal",
    "relationship",
    "spanning",
    "regulatory_compliance",
    "regulatory_fact",
    "traceability",
)

_CATEGORY_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "traceability",
        (
            "en qué página",
            "qué página",
            "en qué anexo",
            "qué anexo",
            "sección",
            "apartado",
        ),
    ),
    (
        "temporal",
        (
            "cuándo",
            "desde qué año",
            "en qué año",
            "trimestre",
            "fecha",
            "entró en vigor",
            "previst",
        ),
    ),
    (
        "regulatory_compliance",
        (
            "qué requisitos",
            "qué exige",
            "debo cumplir",
            "debe cumplir",
            "condicionalidad",
            "obligaciones",
        ),
    ),
    (
        "spanning",
        (
            "asociado al empleado",
            "asignada a",
            "combina",
            "a partir de",
            "y cuál",
            "y cómo",
        ),
    ),
    (
        "relationship",
        ("cómo se relaciona", "con qué", "asociado", "relación", "vincula", "entre"),
    ),
    (
        "regulatory_fact",
        (
            "según",
            "normativa",
            "directiva",
            "coeficiente",
            "ayuda por hectárea",
            "volumen máximo",
        ),
    ),
    (
        "direct_fact",
        (
            "qué es",
            "cuál es",
            "cuánto",
            "dónde",
            "qué modelo",
            "qué productos",
            "qué mercados",
        ),
    ),
)


def categorize_question(question: str, fallback: str = "direct_fact") -> str:
    text = (question or "").casefold()
    for category, hints in _CATEGORY_HINTS:
        if any(hint in text for hint in hints):
            return category
    return fallback if fallback in EVAL_CATEGORIES else "direct_fact"


def _extract_pdf_text(content: bytes, *, max_pages: int = 12, max_chars: int = MAX_CHARS) -> str:
    from services.pdf_extract import extract_pdf_text

    return extract_pdf_text(content, max_pages=max_pages, max_chars=max_chars)


def extract_text(filename: str, content: bytes, mime_type: str | None = None) -> str:
    name = (filename or "").lower()
    mime = (mime_type or "").lower()
    if name.endswith(
        (".txt", ".md", ".csv", ".json", ".html", ".xml")
    ) or mime.startswith("text/"):
        return content.decode("utf-8", errors="ignore")[:MAX_CHARS]

    if name.endswith(".pdf") or "pdf" in mime:
        return _extract_pdf_text(content, max_pages=12, max_chars=MAX_CHARS)

    from services.video_extract import is_video_file, transcribe_video_text

    if is_video_file(filename, mime_type):
        return transcribe_video_text(content, filename, max_chars=MAX_CHARS)

    return content.decode("utf-8", errors="ignore")[:MAX_CHARS]


def _pack_question(
    question: str,
    *,
    rationale: str = "",
    category: str | None = None,
    keywords: list[str] | None = None,
    reference_answer: str = "",
) -> dict[str, Any]:
    q = re.sub(r"\s+", " ", question).strip()
    if q and not q.endswith("?"):
        q = f"{q}?"
    cat = category if category in EVAL_CATEGORIES else categorize_question(q)
    return {
        "question": q,
        "rationale": (rationale or "").strip(),
        "category": cat,
        "keywords": [
            str(item).strip() for item in (keywords or []) if str(item).strip()
        ][:8],
        "reference_answer": (reference_answer or "").strip(),
        "out_of_knowledge": False,
    }


def is_template_eval_question(
    question: str,
    *,
    rationale: str = "",
    reference_answer: str = "",
) -> bool:
    """Detecta plantillas genéricas del fallback heurístico (no deben aprobarse)."""
    q = (question or "").casefold()
    blob = f"{rationale} {reference_answer}".casefold()
    if "pregunta de evaluación derivada del documento" in blob:
        return True
    patterns = (
        "cuál es el hecho principal descrito en ",
        "qué fechas o plazos relevantes establece ",
        "qué relación existe entre los elementos principales de ",
        "qué procedimiento describe ",
        "qué requisitos de cumplimiento establece ",
        "qué dato normativo concreto recoge ",
        "en qué página, anexo o sección de ",
    )
    return any(p in q for p in patterns)


def heuristic_questions(
    text: str, filename: str, limit: int = 6
) -> list[dict[str, Any]]:
    """Solo preguntas que ya aparecen en el documento (con '?').

    Ya no se inventan plantillas por nombre de archivo: ensuciaban la cola HITL
    y el banco de evaluación.
    """
    _ = filename
    questions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in re.findall(r"[^.!\n]{12,180}\?", text or ""):
        packed = _pack_question(match, rationale="Aparece en el documento")
        if is_template_eval_question(
            packed["question"],
            rationale=packed.get("rationale") or "",
            reference_answer=packed.get("reference_answer") or "",
        ):
            continue
        key = packed["question"].lower()
        if key in seen:
            continue
        seen.add(key)
        questions.append(packed)
        if len(questions) >= limit:
            break
    return questions


def _parse_llm_questions(raw: str) -> list[dict[str, Any]]:
    if not raw:
        return []
    text = raw.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    items = data.get("questions") if isinstance(data, dict) else data
    out: list[dict[str, Any]] = []
    if not isinstance(items, list):
        return []
    for item in items:
        if isinstance(item, str) and item.strip():
            out.append(_pack_question(item))
        elif isinstance(item, dict):
            q = str(item.get("question") or item.get("pregunta") or "").strip()
            if not q:
                continue
            keywords = item.get("keywords") or item.get("palabras_clave") or []
            if isinstance(keywords, str):
                keywords = [
                    part.strip() for part in keywords.split(",") if part.strip()
                ]
            out.append(
                _pack_question(
                    q,
                    rationale=str(
                        item.get("rationale") or item.get("why") or ""
                    ).strip(),
                    category=str(item.get("category") or item.get("categoria") or ""),
                    keywords=keywords if isinstance(keywords, list) else [],
                    reference_answer=str(
                        item.get("reference_answer") or item.get("respuesta") or ""
                    ),
                )
            )
    return out[:8]


def extract_questions_with_llm(text: str, filename: str) -> list[dict[str, Any]]:
    snippet = (text or "").strip()[:MAX_CHARS]
    if len(snippet) < 40:
        return heuristic_questions(snippet, filename)
    client = OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)
    categories = ", ".join(EVAL_CATEGORIES)
    prompt = f"""Eres evaluador de un RAG agrícola canario (PAC, POSEI, SIGPAC, SAT, cadena de frío).
Del documento extrae entre 5 y 8 preguntas respondibles únicamente con su contenido.
Cada pregunta debe pertenecer exactamente a una de estas categorías:
- direct_fact: un dato explícito, nombre, cantidad, ubicación, producto o definición.
- temporal: una fecha, año, trimestre, vigencia, plazo o cambio en el tiempo.
- relationship: relación directa entre dos entidades, perfiles, sistemas o conceptos.
- spanning: respuesta que exige combinar dos o más fragmentos o encadenar relaciones.
- regulatory_compliance: requisitos u obligaciones que una persona o explotación debe cumplir.
- regulatory_fact: importe, límite, coeficiente o regla concreta fijada por una norma.
- traceability: página, anexo, sección o ubicación exacta de la evidencia.

No inventes nombres, cifras, fechas ni respuestas. Evita preguntas duplicadas. La respuesta
de referencia debe ser autosuficiente y estar respaldada literalmente por el documento.
Prohibido generar plantillas genéricas del tipo «hecho principal descrito en <archivo>».
Responde SOLO JSON válido:
{{"questions": [{{"question": "...", "category": "direct_fact", "keywords": ["..."], "reference_answer": "...", "rationale": "por qué evalúa calidad"}}]}}
Categorías permitidas: {categories}

Archivo: {filename}

Documento:
{snippet}
"""
    try:
        response = client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=700,
        )
        raw = response.choices[0].message.content or ""
        parsed = _parse_llm_questions(raw)
        cleaned = [
            item
            for item in parsed
            if not is_template_eval_question(
                item.get("question") or "",
                rationale=item.get("rationale") or "",
                reference_answer=item.get("reference_answer") or "",
            )
        ]
        if cleaned:
            return cleaned
    except Exception:
        logger.exception("Fallo al extraer preguntas con el LLM")
    return heuristic_questions(snippet, filename)


async def extract_document_questions(
    filename: str,
    content: bytes,
    mime_type: str | None = None,
) -> list[dict[str, Any]]:
    import asyncio

    text = extract_text(filename, content, mime_type)
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(extract_questions_with_llm, text, filename),
            timeout=25,
        )
    except Exception:
        return heuristic_questions(text, filename)
