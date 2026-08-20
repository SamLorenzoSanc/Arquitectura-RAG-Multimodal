import json
from pathlib import Path
from pydantic import BaseModel, Field

TEST_FILE = str(Path(__file__).parent / "tests.jsonl")


class TestQuestion(BaseModel):
    """A test question with expected keywords and reference answer."""

    question: str = Field(description="La pregunta que hay que plantear al sistema RAG")
    keywords: list[str] = Field(description="Palabras clave que deben aparecer en el contexto recuperado")
    reference_answer: str = Field(description="La respuesta de referencia a esta pregunta")
    category: str = Field(description="Categoría de la pregunta (p. ej., hecho directo, abarcante, temporal)")
    source_file: str = ""
    page: str = ""
    split: str = "dev"


def load_tests() -> list[TestQuestion]:
    """Load test questions from JSONL file."""
    tests = []
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line.strip())
            tests.append(TestQuestion(**data))
    return tests
