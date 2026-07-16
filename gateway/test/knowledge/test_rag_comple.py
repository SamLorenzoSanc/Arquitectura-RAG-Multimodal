
from pathlib import Path
from uuid import uuid4

import pytest

from services.rag_service import RAGService

@pytest.mark.asyncio
async def test_rag_pipeline():


    rag = RAGService()


    response = await rag.answer(

        knowledge_base_id="test",

        question=
        """
        ¿Qué tecnología utiliza AgroTech?
        """

    )


    assert response


    assert len(response)>20