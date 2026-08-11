import json
import os
from pathlib import Path
from pydantic import BaseModel, Field
from services.evaluation_metrics import normalize_text

TEST_FILE = Path(os.getenv("EVALUATION_DATASET_PATH", Path(__file__).parent / "tests.jsonl"))


class TestQuestion(BaseModel):
    """A test question with expected keywords and reference answer."""

    question: str = Field(description="La pregunta que hay que plantear al sistema RAG")
    keywords: list[str] = Field(description="Palabras clave que deben aparecer en el contexto recuperado")
    reference_answer: str = Field(description="La respuesta de referencia a esta pregunta")
    category: str = Field(description="Categoría de la pregunta (p. ej., hecho directo, abarcante, temporal)")
    split: str = "dev"
    out_of_knowledge: bool = False
    metadata: dict = Field(default_factory=dict)


def load_tests(path: str | Path | None = None, split: str | None = None) -> list[TestQuestion]:
    """Carga JSON o JSONL, elimina duplicados y permite filtrar dev/holdout."""
    source = Path(path or TEST_FILE)
    raw = source.read_text(encoding="utf-8-sig")
    try:
        parsed = json.loads(raw)
        rows = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]

    tests: list[TestQuestion] = []
    seen: set[str] = set()
    for index, data in enumerate(rows):
        key = normalize_text(data.get("question", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        data = dict(data)
        data.setdefault("split", "holdout" if index % 5 == 4 else "dev")
        item = TestQuestion(**data)
        if split in {"dev", "holdout"} and item.split != split:
            continue
        tests.append(item)
    return tests
