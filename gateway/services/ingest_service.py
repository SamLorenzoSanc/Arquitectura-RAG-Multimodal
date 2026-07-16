from __future__ import annotations

import logging
from pathlib import Path

import chromadb
from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, wait_exponential

from models.document import Document
from parsers.factory import FileParserFactory

logger = logging.getLogger(__name__)

MODEL = "llama3"
EMBEDDING_MODEL = "qwen3-embedding:latest"

AVERAGE_CHUNK_SIZE = 100

CHROMA_PATH = Path("storage/chroma")

COLLECTION_NAME = "documents"

wait = wait_exponential(
    multiplier=1,
    min=5,
    max=120,
)

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)


class Result(BaseModel):

    page_content: str

    metadata: dict


class Chunk(BaseModel):

    headline: str = Field(
        description="Título breve del fragmento"
    )

    summary: str = Field(
        description="Resumen del fragmento"
    )

    original_text: str = Field(
        description="Texto original EXACTO del documento"
    )

    def as_result(
        self,
        document: dict,
    ):

        metadata = {

            "source": document["source"],

            "document_id": document["document_id"],

            "tenant_id": document["tenant_id"],

            "knowledge_base_id": document["knowledge_base_id"],

        }

        return Result(

            page_content=
                f"{self.headline}\n\n"
                f"{self.summary}\n\n"
                f"{self.original_text}",

            metadata=metadata,

        )


class Chunks(BaseModel):

    chunks: list[Chunk]


class IngestService:

    def __init__(
        self,
        session: AsyncSession,
    ):

        self.session = session

        self.parser_factory = FileParserFactory()

        self.chroma = chromadb.PersistentClient(
            path=str(CHROMA_PATH)
        )

    async def process(
        self,
        document: Document,
    ):

        logger.info(
            "Processing %s",
            document.filename,
        )

        parser = self.parser_factory.create(
            Path(document.storage_path)
        )

        parsed = await parser.parse(
            Path(document.storage_path)
        )

        llm_document = {

            "type": "document",

            "source": document.filename,

            "document_id": str(document.id),

            "tenant_id": str(document.tenant_id),

            "knowledge_base_id": str(
                document.knowledge_base_id
            ),

            "text": parsed.markdown,

        }

        chunks = self.create_chunks(
            llm_document
        )

        self.create_embeddings(
            chunks
        )

        logger.info(
            "Document %s ingested (%s chunks)",
            document.filename,
            len(chunks),
        )

        return len(chunks)

    def make_prompt(
        self,
        document: dict,
    ):

        how_many = (
            len(document["text"])
            //
            AVERAGE_CHUNK_SIZE
        ) + 1

        return f"""
            Tomas un documento y lo divides en fragmentos superpuestos para una base de conocimientos.

            El documento es de tipo: {document["type"]}

            El documento se obtuvo de: {document["source"]}

            Responde únicamente en español.

            No inventes información.

            No completes datos inexistentes.

            No utilices placeholders como:

            - [Insert...]

            - Example

            - Lorem Ipsum

            - TBD

            El campo original_text debe contener EXACTAMENTE el texto original.

            Debes dividir el documento en aproximadamente {how_many} fragmentos.

            Debe existir un pequeño solapamiento.

            Cada fragmento debe contener:

            headline

            summary

            original_text

            Documento:

            {document["text"]}
            """


    def make_messages(
            self,
            document: dict,
        ):
            return [
                {
                    "role": "user",
                    "content": self.make_prompt(
                        document
                    ),
    
                }
    
            ]
    
    @retry(wait=wait)
    def process_document(
            self,
            document: dict,
        ):
    
            response = client.beta.chat.completions.parse(
            
                model=MODEL,
    
                messages=self.make_messages(document),
    
                response_format=Chunks,
    
            )
    
            parsed = response.choices[0].message.parsed
    
            return [
            
                chunk.as_result(document)
    
                for chunk in parsed.chunks
    
            ]
    
    def create_chunks(
        self,
        document: dict,
    ):

        return self.process_document(
            document
        )

    def create_embeddings(
        self,
        chunks: list[Result],
    ):

        texts = [
            chunk.page_content
            for chunk in chunks
        ]

        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
        )

        vectors = [
            emb.embedding
            for emb in response.data

        ]

        collection = self.chroma.get_or_create_collection(
            COLLECTION_NAME
        )

        ids = [

            f"{chunk.metadata['document_id']}_{i}"

            for i, chunk in enumerate(chunks)

        ]

        metadatas = [

            chunk.metadata

            for chunk in chunks

        ]

        collection.add(

            ids=ids,

            embeddings=vectors,

            documents=texts,

            metadatas=metadatas,

        )

        logger.info(
            "%s embeddings stored",
            len(chunks),
        )