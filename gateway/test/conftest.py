from pathlib import Path

import pytest


FIXTURES = Path(__file__).parent / "fixtures"


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