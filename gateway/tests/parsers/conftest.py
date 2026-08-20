from pathlib import Path
from uuid import uuid4

import pytest

from parsers.base import ParsingContext

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture
def sample_pdf() -> Path:
    return FIXTURES / "sample1.pdf"


@pytest.fixture
def sample_docx() -> Path:
    return FIXTURES / "sample.docx"


@pytest.fixture
def sample_txt() -> Path:
    return FIXTURES / "sample.txt"


@pytest.fixture
def sample_md() -> Path:
    return FIXTURES / "sample.md"


@pytest.fixture
def sample_png() -> Path:
    return FIXTURES / "sample.png"


@pytest.fixture
def parsing_context() -> ParsingContext:
    return ParsingContext(
        tenant_id=uuid4(),
        organization_id=uuid4(),
        department_id=uuid4(),
        member_id=uuid4(),
        uploaded_by=uuid4(),
        language="es",
        tags=["agro", "tfm"],
    )
