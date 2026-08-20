from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from parsers.markdown_parser import MarkdownParser


@pytest.mark.asyncio
async def test_markdown_parser(sample_md: Path):
    parser = MarkdownParser()
    parsed = await parser.parse(sample_md)

    assert parsed.filename == sample_md.name
    assert parsed.extension == ".md"
    assert parsed.title == sample_md.stem
    assert parsed.markdown
    assert len(parsed.markdown) > 0
    assert parsed.word_count > 0
    assert parsed.character_count > 0
    assert parsed.metadata["source"] == str(sample_md)
    assert parsed.metadata["mime_type"] == "text/markdown"
    assert parsed.metadata["parser"] == "native"

    checksum = hashlib.sha256(sample_md.read_bytes()).hexdigest()
    assert parsed.metadata["checksum"] == checksum
