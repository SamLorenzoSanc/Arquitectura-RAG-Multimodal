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
    split: str = "dev"
    out_of_knowledge: bool = False
    metadata: dict = Field(default_factory=dict)


def load_tests(
    path: str | Path | None = None, split: str | None = None
) -> list[TestQuestion]:
    """Carga los bancos actual y anterior, elimina duplicados y filtra el split."""
    sources = [Path(path or TEST_FILE)]
    uses_default_bank = path is None and TEST_FILE == DEFAULT_TEST_FILE
    if uses_default_bank and LEGACY_TEST_FILE.exists():
        sources.append(LEGACY_TEST_FILE)

    tests: list[TestQuestion] = []
    seen: set[str] = set()
    row_index = 0
    for source in sources:
        raw = source.read_text(encoding="utf-8-sig")
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
