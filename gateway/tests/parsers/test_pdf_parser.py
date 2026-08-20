from pathlib import Path
from unittest.mock import MagicMock

import pytest

from parsers.pdf_parser import PdfParser


@pytest.fixture
def mocked_converter_result():
    markdown = "# Documento PDF\n\nContenido extraído"

    document = MagicMock()
    document.export_to_markdown.return_value = markdown

    result = MagicMock()
    result.document = document

    return result, markdown


@pytest.mark.asyncio
async def test_parse_pdf_success(
    sample_pdf,
    parsing_context,
    mocked_converter_result,
):
    parser = PdfParser()

    fake_result, markdown = mocked_converter_result

    parser.converter.convert = MagicMock(return_value=fake_result)

    result = await parser.parse(
        sample_pdf,
        parsing_context,
    )

    assert result.filename == sample_pdf.name
    assert result.extension == ".pdf"
    assert result.title == sample_pdf.stem

    assert result.markdown == markdown

    assert result.language == "es"

    assert result.word_count == len(markdown.split())
    assert result.character_count == len(markdown)

    assert result.metadata["mime_type"] == "application/pdf"
    assert result.metadata["parser"] == "docling"

    assert result.metadata["tenant_id"] == str(parsing_context.tenant_id)

    assert "checksum" in result.metadata
    assert len(result.metadata["checksum"]) == 64


@pytest.mark.asyncio
async def test_parse_pdf_file_not_found(
    parsing_context,
):
    parser = PdfParser()

    with pytest.raises(FileNotFoundError):

        await parser.parse(
            Path("not_exists.pdf"),
            parsing_context,
        )


@pytest.mark.asyncio
async def test_parse_pdf_converter_called(
    sample_pdf,
    parsing_context,
    mocked_converter_result,
):
    parser = PdfParser()

    fake_result, _ = mocked_converter_result

    parser.converter.convert = MagicMock(return_value=fake_result)

    await parser.parse(
        sample_pdf,
        parsing_context,
    )

    parser.converter.convert.assert_called_once_with(sample_pdf)


@pytest.mark.asyncio
async def test_parse_pdf_metadata(
    sample_pdf,
    parsing_context,
    mocked_converter_result,
):
    parser = PdfParser()

    fake_result, _ = mocked_converter_result

    parser.converter.convert = MagicMock(return_value=fake_result)

    result = await parser.parse(
        sample_pdf,
        parsing_context,
    )

    metadata = result.metadata

    assert metadata["source"] == str(sample_pdf)
    assert metadata["mime_type"] == "application/pdf"
    assert metadata["parser"] == "docling"

    assert metadata["tenant_id"] == (str(parsing_context.tenant_id))

    assert metadata["organization_id"] == (str(parsing_context.organization_id))

    assert metadata["department_id"] == (str(parsing_context.department_id))

    assert metadata["member_id"] == (str(parsing_context.member_id))

    assert metadata["uploaded_by"] == (str(parsing_context.uploaded_by))

    assert metadata["tags"] == parsing_context.tags


@pytest.mark.asyncio
async def test_parse_pdf_default_language(
    sample_pdf,
    mocked_converter_result,
):
    parser = PdfParser()

    context = parsing_context = {"tenant_id": None}

    fake_result, _ = mocked_converter_result

    parser.converter.convert = MagicMock(return_value=fake_result)

    # contexto sin idioma
    from parsers.base import ParsingContext
    from uuid import UUID

    context = ParsingContext(tenant_id=UUID("00000000-0000-0000-0000-000000000001"))

    result = await parser.parse(
        sample_pdf,
        context,
    )

    assert result.language == "es"
