from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from services.knowledge_builder import KnowledgeBuilder
from parsers.parsed_document import ParsedDocument


async def main():

    document = SimpleNamespace(

        id=uuid4(),

        tenant_id=uuid4(),

        knowledge_base_id=uuid4(),

        owner_id=uuid4(),

        filename="sample.txt",

        storage_path="test/fixtures/sample.txt",

        size=1024,

    )


    ##################################################################
    # ParsedDocument simulado
    ##################################################################

    parsed = ParsedDocument(

        filename="sample.txt",

        extension=".txt",

        title="Documento ejemplo",

        markdown="""
# Documento ejemplo

Este documento pertenece a AgroTech.

La plataforma utiliza sensores IoT
para monitorizar cultivos.
""",

        language="es",

        word_count=15,

        character_count=150,


        summary="Documento de prueba",


        page_count=None,


        metadata={

            "mime_type":"text/plain",

            "parser":"native",

            "checksum":"abc123",

        },

    )


    ##################################################################
    # Builder
    ##################################################################

    builder = KnowledgeBuilder(

        storage_root=Path(
            "out/knowledge-base"
        )

    )


    asset = await builder.ingest(

        document,

        parsed,

    )


    ##################################################################
    # Mostrar resultado
    ##################################################################

    print("\n" + "="*80)

    print("KNOWLEDGE ASSET GENERADO")

    print("="*80)


    print(
        "ROOT:",
        asset.root
    )


    print()

    print(
        "METADATA:"
    )

    print(
        asset.metadata
    )


    print()

    print(
        "CONTENT:"
    )

    print(
        asset.content
    )


    print()

    print(
        "FILES:"
    )


    for path in asset.root.rglob("*"):

        print(
            " -",
            path
        )



if __name__ == "__main__":

    asyncio.run(main())