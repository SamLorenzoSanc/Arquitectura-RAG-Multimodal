from __future__ import annotations

import logging

from openai import OpenAI
from pydantic import BaseModel, Field
from tenacity import retry, wait_exponential

from services.chunking_service import Chunk

logger = logging.getLogger(__name__)

MODEL = "llama3"

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

wait = wait_exponential(
    multiplier=1,
    min=5,
    max=120,
)


# ============================================================
# MODELOS
# ============================================================

class Entity(BaseModel):

    name: str = Field(
        description="Nombre de la entidad"
    )

    type: str = Field(
        description="Tipo de entidad"
    )

    description: str = Field(
        description="Descripción corta"
    )


class Relation(BaseModel):

    source: str = Field(
        description="Entidad origen"
    )

    target: str = Field(
        description="Entidad destino"
    )

    relation: str = Field(
        description="Tipo de relación"
    )

    description: str = Field(
        description="Descripción"
    )


class Knowledge(BaseModel):

    entities: list[Entity]

    relations: list[Relation]


# ============================================================
# SERVICIO
# ============================================================

class KnowledgeExtractionService:

    def make_prompt(
        self,
        chunk: Chunk,
    ) -> str:

        return f"""
            Eres un sistema experto en extracción de conocimiento.

            Analiza el siguiente fragmento documental.

            Extrae TODAS las entidades relevantes.

            Tipos de entidades posibles:

            - Company
            - Person
            - Crop
            - Product
            - Technology
            - Device
            - Sensor
            - Disease
            - Fertilizer
            - Chemical
            - Machinery
            - Process
            - Location
            - Regulation
            - Department
            - Organization
            - Project

            Después identifica TODAS las relaciones existentes entre ellas.

            Reglas:

            - No inventes información.
            - No resumas.
            - Extrae únicamente información explícita.
            - Una entidad no debe aparecer dos veces.
            - Una relación debe tener origen y destino.
            - Utiliza nombres descriptivos para las relaciones.

            Fragmento:

            Título:
            {chunk.headline}

            Resumen:
            {chunk.summary}

            Contenido:

            {chunk.original_text}

            Devuelve EXCLUSIVAMENTE JSON.
        """

    def messages(
        self,
        chunk: Chunk,
    ):

        return [
            {
                "role": "user",
                "content": self.make_prompt(chunk),
            }
        ]

    @retry(wait=wait)
    async def extract(
        self,
        chunk: Chunk,
    ) -> Knowledge:

        logger.info(
            "Extracting knowledge from chunk %s",
            chunk.headline,
        )

        response = client.beta.chat.completions.parse(

            model=MODEL,

            messages=self.messages(chunk),

            response_format=Knowledge,
        )

        knowledge = response.choices[0].message.parsed

        logger.info(
            "Extracted %s entities and %s relations",
            len(knowledge.entities),
            len(knowledge.relations),
        )

        return knowledge

    async def extract_many(
        self,
        chunks: list[Chunk],
    ) -> list[Knowledge]:

        results = []

        for chunk in chunks:

            results.append(
                await self.extract(chunk)
            )

        return results