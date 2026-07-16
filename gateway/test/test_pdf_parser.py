import pytest

from parsers.pdf_parser import PdfParser

from pathlib import Path

@pytest.mark.asyncio
async def test_pdf_parser(sample_pdf):

    parser = PdfParser()

    parsed = await parser.parse(sample_pdf)

    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)

    output_file = out_dir / f"{sample_pdf.stem}.md"
    output_file.write_text(
        parsed.markdown,
        encoding="utf-8",
    )

    print(f"\nMarkdown generado en: {output_file.resolve()}")

    assert parsed.filename == sample_pdf.name
    assert parsed.extension == ".pdf"

    assert parsed.markdown
    assert len(parsed.markdown) > 0

    assert parsed.word_count > 0
    assert parsed.character_count > 0

    assert parsed.metadata["mime_type"] == "application/pdf"