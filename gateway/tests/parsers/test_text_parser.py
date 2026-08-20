from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from parsers.text_parser import TextParser


@pytest.mark.asyncio
async def test_text_parser(sample_txt: Path):
    parser = TextParser()
    parsed = await parser.parse(sample_txt)

    assert parsed.filename == sample_txt.name
    assert parsed.extension == ".txt"
    assert parsed.title == sample_txt.stem
    assert parsed.markdown
    assert len(parsed.markdown) > 0
    assert parsed.word_count > 0
    assert parsed.character_count > 0
    assert parsed.metadata["source"] == str(sample_txt)
    assert parsed.metadata["mime_type"] == "text/plain"
    assert parsed.metadata["parser"] == "native"

    checksum = hashlib.sha256(sample_txt.read_bytes()).hexdigest()
    assert parsed.metadata["checksum"] == checksum


@pytest.mark.asyncio
async def test_text_parser_file_not_found():
    parser = TextParser()
    with pytest.raises(FileNotFoundError):
        await parser.parse(Path("not_exists.txt"))
