from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from parsers.docx_parser import DocxParser


@pytest.mark.asyncio
async def test_docx_parser(sample_docx: Path):

    parser = DocxParser()

    parsed = await parser.parse(sample_docx)

    print("\n" + "=" * 80)
    print("DOCX PARSER OUTPUT")
    print("=" * 80)

    print(parsed.markdown[:3000])

    print("=" * 80)


    # Guardar resultado

    out = Path("out")
    out.mkdir(exist_ok=True)

    output_file = out / f"{sample_docx.stem}.md"

    output_file.write_text(
        parsed.markdown,
        encoding="utf-8",
    )


    print(
        f"\nMarkdown generado: {output_file.resolve()}"
    )

    assert parsed.filename == sample_docx.name

    assert parsed.extension == ".docx"

    assert parsed.title == sample_docx.stem


    assert parsed.markdown

    assert len(parsed.markdown) > 0


    assert parsed.word_count > 0

    assert parsed.character_count > 0

    assert parsed.metadata["source"] == str(sample_docx)

    assert parsed.metadata["mime_type"] in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    )


    assert "parser" in parsed.metadata

    checksum = hashlib.sha256(
        sample_docx.read_bytes()
    ).hexdigest()


    assert parsed.metadata["checksum"] == checksum