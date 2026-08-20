import json
import os
from pathlib import Path
from typing import Any, Mapping
from pydantic import BaseModel, Field
from services.evaluation_metrics import normalize_text

DEFAULT_TEST_FILE = Path(__file__).parent / "tests.jsonl"
TEST_FILE = Path(os.getenv("EVALUATION_DATASET_PATH", DEFAULT_TEST_FILE))
LEGACY_TEST_FILE = Path(__file__).parent.parent / "routes" / "tests.jsonl"


class TestQuestion(BaseModel):
    """A test question with expected keywords and reference answer."""

    question: str = Field(description="La pregunta que hay que plantear al sistema RAG")
    keywords: list[str] = Field(
        description="Palabras clave que deben aparecer en el contexto recuperado"
    )
    reference_answer: str = Field(
        description="La respuesta de referencia a esta pregunta"
    )
    category: str = Field(
        description="Categoría de la pregunta (p. ej., hecho directo, abarcante, temporal)"
    )
    source_file: str = ""
    page: str = ""
    split: str = "dev"
    out_of_knowledge: bool = False
    metadata: dict = Field(default_factory=dict)


def _dump_bank_row(item: TestQuestion) -> dict[str, Any]:
    row: dict[str, Any] = {
        "question": item.question,
        "keywords": list(item.keywords or []),
        "reference_answer": item.reference_answer or "",
        "category": item.category or "direct_fact",
    }
    if item.source_file:
        row["source_file"] = item.source_file
    if item.page:
        row["page"] = item.page
    if item.split:
        row["split"] = item.split
    if item.out_of_knowledge:
        row["out_of_knowledge"] = True
    if item.metadata:
        row["metadata"] = item.metadata
    return row


def upsert_test_question_jsonl(
    *,
    question: str,
    keywords: list[str],
    reference_answer: str,
    category: str,
    source_file: str = "",
    path: str | Path | None = None,
) -> bool:
    """Añade o actualiza una pregunta HITL en el JSONL del banco."""
    text = (question or "").strip()
    if not text:
        return False
    target = Path(path or TEST_FILE)
    key = normalize_text(text)
    incoming = TestQuestion(
        question=text,
        keywords=[str(item).strip() for item in keywords if str(item).strip()][:8],
        reference_answer=(reference_answer or "").strip(),
        category=(category or "direct_fact").strip() or "direct_fact",
        source_file=(source_file or "").strip(),
        split="dev",
        metadata={"source": "hitl", "validated": True},
    )
    existing = load_tests(target) if target.exists() else []
    replaced = False
    out: list[TestQuestion] = []
    for item in existing:
        if normalize_text(item.question) != key:
            out.append(item)
            continue
        meta = dict(item.metadata or {})
        meta.update(incoming.metadata)
        out.append(
            item.model_copy(
                update={
                    "keywords": incoming.keywords or item.keywords,
                    "reference_answer": incoming.reference_answer
                    or item.reference_answer,
                    "category": incoming.category or item.category,
                    "source_file": incoming.source_file or item.source_file,
                    "metadata": meta,
                }
            )
        )
        replaced = True
    if not replaced:
        out.append(incoming)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for item in out:
            handle.write(json.dumps(_dump_bank_row(item), ensure_ascii=False) + "\n")
    return True


def load_tests(
    path: str | Path | None = None, split: str | None = None
) -> list[TestQuestion]:
    """Carga el banco de oro versionado en JSON/JSONL."""
    sources = [Path(path or TEST_FILE)]
    uses_default_bank = path is None and TEST_FILE == DEFAULT_TEST_FILE
    if uses_default_bank and LEGACY_TEST_FILE.exists():
        sources.append(LEGACY_TEST_FILE)

    tests: list[TestQuestion] = []
    seen: set[str] = set()
    row_index = 0
    for source in sources:
        if not source.exists():
            continue
        raw = source.read_text(encoding="utf-8-sig").strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
            rows = parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            rows = [json.loads(line) for line in raw.splitlines() if line.strip()]

        for data in rows:
            key = normalize_text(data.get("question", ""))
            if not key or key in seen:
                row_index += 1
                continue
            seen.add(key)
            data = dict(data)
            data.setdefault("split", "holdout" if row_index % 5 == 4 else "dev")
            item = TestQuestion(**data)
            row_index += 1
            if split in {"dev", "holdout"} and item.split != split:
                continue
            tests.append(item)
    return tests


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def merge_test_banks(
    file_tests: list[TestQuestion],
    db_rows: list[Mapping[str, Any]] | None = None,
) -> list[TestQuestion]:
    """Une el JSONL local con las preguntas anotadas en PostgreSQL.

    Si la misma pregunta está en ambos sitios, se conserva una sola entrada
    enriquecida (keywords, respuesta de referencia y chunks esperados).
    """
    merged: list[TestQuestion] = []
    index_by_question: dict[str, int] = {}

    for item in file_tests:
        key = normalize_text(item.question)
        if not key or key in index_by_question:
            continue
        metadata = dict(item.metadata or {})
        metadata.setdefault("source", "file")
        merged.append(item.model_copy(update={"metadata": metadata}))
        index_by_question[key] = len(merged) - 1

    for row in db_rows or []:
        question = str(row.get("question") or "").strip()
        key = normalize_text(question)
        if not key:
            continue

        keywords = [
            str(item) for item in _as_list(row.get("keywords")) if str(item).strip()
        ]
        chunk_ids = [
            str(item)
            for item in _as_list(row.get("selected_chunk_ids"))
            if str(item).strip()
        ]
        expected = row.get("expected_chunk_id")
        if expected and str(expected) not in chunk_ids:
            chunk_ids.append(str(expected))

        extra_meta = row.get("metadata") or {}
        if isinstance(extra_meta, str):
            try:
                extra_meta = json.loads(extra_meta)
            except json.JSONDecodeError:
                extra_meta = {}
        if not isinstance(extra_meta, dict):
            extra_meta = {}

        if key in index_by_question:
            current = merged[index_by_question[key]]
            metadata = dict(current.metadata or {})
            metadata.update(extra_meta)
            if chunk_ids:
                metadata["expected_chunk_ids"] = chunk_ids
                metadata["source"] = "merged"
            else:
                metadata.setdefault("source", "file")
            if row.get("flag_different_info"):
                metadata["different_info"] = True
            merged[index_by_question[key]] = current.model_copy(
                update={
                    "keywords": current.keywords or keywords,
                    "reference_answer": current.reference_answer
                    or (row.get("reference_answer") or ""),
                    "out_of_knowledge": current.out_of_knowledge
                    or bool(row.get("flag_out_of_knowledge")),
                    "metadata": metadata,
                }
            )
            continue

        metadata = dict(extra_meta)
        if chunk_ids:
            metadata["expected_chunk_ids"] = chunk_ids
        if row.get("flag_different_info"):
            metadata["different_info"] = True
        metadata.setdefault("source", "annotated")

        merged.append(
            TestQuestion(
                question=question,
                keywords=keywords,
                reference_answer=row.get("reference_answer") or "",
                category=row.get("category") or "general",
                split=row.get("split") or "dev",
                out_of_knowledge=bool(row.get("flag_out_of_knowledge")),
                metadata=metadata,
            )
        )
        index_by_question[key] = len(merged) - 1

    return merged
