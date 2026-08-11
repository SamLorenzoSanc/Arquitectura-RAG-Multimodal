"""Métricas puras y reproducibles para la evaluación del RAG."""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal, InvalidOperation


def normalize_text(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", value or "").casefold()
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(value.split())


def precision_at_k(relevant_ids: set[str], retrieved_ids: Sequence[str], k: int) -> float:
    if k <= 0:
        return 0.0
    retrieved = list(retrieved_ids[:k])
    return sum(item in relevant_ids for item in retrieved) / len(retrieved) if retrieved else 0.0


def recall_at_k(relevant_ids: set[str], retrieved_ids: Sequence[str], k: int) -> float:
    if not relevant_ids or k <= 0:
        return 0.0
    return len(relevant_ids.intersection(retrieved_ids[:k])) / len(relevant_ids)


def reciprocal_rank(relevant_ids: set[str], retrieved_ids: Sequence[str]) -> float:
    return next((1.0 / rank for rank, item in enumerate(retrieved_ids, 1) if item in relevant_ids), 0.0)


def ndcg_at_k(relevant_ids: set[str], retrieved_ids: Sequence[str], k: int) -> float:
    if not relevant_ids or k <= 0:
        return 0.0
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, item in enumerate(retrieved_ids[:k], 1)
        if item in relevant_ids
    )
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, min(k, len(relevant_ids)) + 1))
    return dcg / ideal if ideal else 0.0


_NUMBER_RE = re.compile(r"(?<!\w)[+-]?\d[\d .]*(?:,\d+)?(?:\s*%|\s*(?:€|eur|m[³3]|ha))?", re.I)


def extract_numbers(value: str | None) -> list[Decimal]:
    numbers: list[Decimal] = []
    for match in _NUMBER_RE.findall(value or ""):
        token = re.sub(r"(?:€|eur|m[³3]|ha|%)", "", match, flags=re.I).strip().replace(" ", "")
        if "," in token:
            token = token.replace(".", "").replace(",", ".")
        elif token.count(".") > 1 or (token.count(".") == 1 and len(token.rsplit(".", 1)[1]) == 3):
            token = token.replace(".", "")
        try:
            numbers.append(Decimal(token))
        except InvalidOperation:
            continue
    return numbers


def numeric_match(reference: str | None, generated: str | None, tolerance: float = 0.01) -> float:
    expected = extract_numbers(reference)
    if not expected:
        return 1.0
    actual = extract_numbers(generated)
    matched = 0
    used: set[int] = set()
    for target in expected:
        allowed = max(Decimal(str(tolerance)), abs(target) * Decimal(str(tolerance)))
        for index, candidate in enumerate(actual):
            if index not in used and abs(candidate - target) <= allowed:
                used.add(index)
                matched += 1
                break
    return matched / len(expected)


_CITATION_RE = re.compile(
    r"(?:\[(?:\d+|[^\]]+\.(?:pdf|md)(?::p(?:ágina)?\.?\s*\d+)?)\]|"
    r"(?:p(?:ágina)?\.?\s*\d+|anexo\s+[ivxlcdm\d]+))",
    re.I,
)


def citation_accuracy(answer: str | None, available_sources: Iterable[str] = ()) -> float:
    citations = _CITATION_RE.findall(answer or "")
    if not citations:
        return 0.0
    sources = [normalize_text(source) for source in available_sources]
    if not sources:
        return 1.0
    valid = sum(any(source in normalize_text(citation) or normalize_text(citation) in source for source in sources) for citation in citations)
    return valid / len(citations)


_ABSTENTION_PATTERNS = (
    "no dispongo de informacion",
    "no hay informacion suficiente",
    "no puedo determinar",
    "el contexto no contiene",
    "no consta en el contexto",
)


def is_abstention(answer: str | None) -> bool:
    normalized = normalize_text(answer)
    return any(pattern in normalized for pattern in _ABSTENTION_PATTERNS)


def abstention_score(answer: str | None, out_of_knowledge: bool) -> float:
    abstained = is_abstention(answer)
    return float(abstained if out_of_knowledge else not abstained)


def dataset_fingerprint(rows: Iterable[Mapping]) -> str:
    canonical = []
    for row in rows:
        canonical.append(
            {
                "question": normalize_text(str(row.get("question", ""))),
                "reference_answer": str(row.get("reference_answer") or "").strip(),
                "keywords": sorted(normalize_text(str(item)) for item in row.get("keywords", [])),
                "category": str(row.get("category") or "general"),
                "split": str(row.get("split") or "dev"),
                "out_of_knowledge": bool(
                    row.get("out_of_knowledge", row.get("flag_out_of_knowledge", False))
                ),
                "selected_chunk_ids": sorted(map(str, row.get("selected_chunk_ids", []))),
            }
        )
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
