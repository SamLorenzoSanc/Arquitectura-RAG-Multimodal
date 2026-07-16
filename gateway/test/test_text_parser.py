from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from parsers.text_parser import TextParser

@pytest.mark.asyncio
async def test_text_parser(sample_txt: Path):

    parser = TextParser()

    parsed = await parser.parse(sample_txt)

    print("\n" + "=" * 80)
    print("TEXT PARSER OUTPUT")
    print("=" * 80)

    print(parsed.markdown)

    print("=" * 80)

    out = Path("out")
    out.mkdir(exist_ok=True)

    output_file = out / f"{sample_txt.stem}.md"

    output_file.write_text(
        parsed.markdown,
        encoding="utf-8",
    )

    print(
        f"\nMarkdown generado: {output_file.resolve()}"
    )

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

    checksum = hashlib.sha256(
        sample_txt.read_bytes()
    ).hexdigest()


    assert parsed.metadata["checksum"] == checksum