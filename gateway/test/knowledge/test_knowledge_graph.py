from pathlib import Path
from uuid import uuid4

import pytest

@pytest.mark.asyncio
async def test_graph_creation():

    service = KnowledgeGraphService()


    chunks=[

        Chunk(
            page_content="""
            AgroTech utiliza sensores IoT
            para controlar cultivos.
            """,

            metadata={
                "document_id":"123"
            }
        )

    ]


    await service.build(
        tenant_id="tenant1",
        knowledge_base_id="kb1",
        document_id="doc1",
        chunks=chunks,
    )


    result = service.driver.session().run(
        """
        MATCH(n)
        RETURN count(n)
        """
    )


    assert result.single()[0] > 0