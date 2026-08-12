from pathlib import Path
from unittest.mock import MagicMock
import hashlib
import pytest

from parsers.docx_parser import DocxParser


@pytest.fixture
def mocked_docx_converter_result():
    """
    Simula la respuesta de Docling.
    """

    markdown = (
        "# Documento DOCX\n\n"
        "Contenido convertido desde Word."
    )

    document = MagicMock()

    document.export_to_markdown.return_value = markdown

    result = MagicMock()

    result.document = document

    return result, markdown


@pytest.mark.asyncio
async def test_parse_docx_success(
    sample_docx,
    parsing_context,
    mocked_docx_converter_result,
):
    """
    Comprueba que un DOCX válido genera un ParsedDocument correcto.
    """

    parser = DocxParser()

    fake_result, markdown = (
        mocked_docx_converter_result
    )

    parser.converter.convert = MagicMock(
        return_value=fake_result
    )


    parsed = await parser.parse(
        sample_docx,
        parsing_context,
    )


    assert parsed.filename == sample_docx.name

    assert parsed.extension == ".docx"

    assert parsed.title == sample_docx.stem


    assert parsed.markdown == markdown


    assert parsed.language == (
        parsing_context.language
    )


    assert parsed.word_count == (
        len(markdown.split())
    )


    assert parsed.character_count == (
        len(markdown)
    )

@pytest.mark.asyncio
async def test_parse_docx_metadata(
    sample_docx,
    parsing_context,
    mocked_docx_converter_result,
):

    parser = DocxParser()

    fake_result, _ = (
        mocked_docx_converter_result
    )

    parser.converter.convert = MagicMock(
        return_value=fake_result
    )


    parsed = await parser.parse(
        sample_docx,
        parsing_context,
    )


    metadata = parsed.metadata


    assert metadata["source"] == (
        str(sample_docx)
    )

    assert metadata["parser"] == "docling"


    assert metadata["tenant_id"] == (
        str(parsing_context.tenant_id)
    )


    assert metadata["uploaded_by"] == (
        str(parsing_context.uploaded_by)
    )


    assert metadata["tags"] == (
        parsing_context.tags
    )


@pytest.mark.asyncio
async def test_parse_docx_checksum(
    sample_docx,
    parsing_context,
    mocked_docx_converter_result,
):

    parser = DocxParser()

    fake_result, _ = (
        mocked_docx_converter_result
    )

    parser.converter.convert = MagicMock(
        return_value=fake_result
    )


    parsed = await parser.parse(
        sample_docx,
        parsing_context,
    )


    expected_checksum = hashlib.sha256(
        sample_docx.read_bytes()
    ).hexdigest()


    assert parsed.metadata["checksum"] == (
        expected_checksum
    )