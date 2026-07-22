from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from parsers.image_parser import ImageParser


@pytest.fixture
def mocked_llm_response():

    response = MagicMock()

    response.choices = [
        MagicMock(
            message=MagicMock(
                content=(
                    "# Imagen\n\n"
                    "Texto extraído"
                )
            )
        )
    ]

    return response



@pytest.fixture
def mock_image_client(
    mocked_llm_response,
):
    return AsyncMock(
        return_value=mocked_llm_response
    )

@pytest.mark.asyncio
async def test_parse_image_success(
    sample_png,
    parsing_context,
    mock_image_client,
):

    parser = ImageParser()

    parser.client.chat.completions.create = (
        mock_image_client
    )


    result = await parser.parse(
        sample_png,
        parsing_context,
    )


    assert result.filename == (
        sample_png.name
    )


    assert result.extension == ".png"


    assert result.title == (
        sample_png.stem
    )


    assert result.markdown == (
        "# Imagen\n\nTexto extraído"
    )


    assert result.language == "es"


    assert result.word_count > 0


    assert result.character_count > 0

@pytest.mark.asyncio
async def test_parse_image_metadata(
    sample_png,
    parsing_context,
    mock_image_client,
):

    parser = ImageParser()

    parser.client.chat.completions.create = (
        mock_image_client
    )


    result = await parser.parse(
        sample_png,
        parsing_context,
    )


    metadata = result.metadata


    assert metadata["source"] == (
        str(sample_png)
    )


    assert metadata["mime_type"] == (
        "image/png"
    )


    assert metadata["parser"] == (
        "vision-llm"
    )


    assert metadata["model"] == (
        parser.model
    )


    assert metadata["tenant_id"] == (
        str(parsing_context.tenant_id)
    )


    assert metadata["tags"] == (
        parsing_context.tags
    )
    