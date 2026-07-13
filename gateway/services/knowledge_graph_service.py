from __future__ import annotations

import json
import logging
from typing import List

from neo4j import GraphDatabase
from openai import OpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)


MODEL = "llama3"

BASE_URL = "http://localhost:11434/v1"

SYSTEM_PROMPT = """
    Eres un sistema experto en extracción de conocimiento.
    
    A partir del texto debes devolver ÚNICAMENTE JSON.
    
    Extrae:
    
    - entidades
    - relaciones
    
    Cada entidad debe tener:
    
    id
    type
    name
    description
    
    Cada relación:
    
    source
    target
    type
    description
    
    No inventes información.
    
    Formato:
    
    {
      "entities":[...],
      "relations":[...]
    }
    """


class Entity(BaseModel):
    id: str
    type: str
    name: str
    description: str


class Relation(BaseModel):
    source: str
    target: str
    type: str
    description: str


class GraphExtraction(BaseModel):
    entities: List[Entity]
    relations: List[Relation]


class KnowledgeGraphService:

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "password",
    ):

        self.client = OpenAI(
            base_url=BASE_URL,
            api_key="ollama",
        )

        self.driver = GraphDatabase.driver(
            uri,
            auth=(username, password),
        )

    async def ingest(
        self,
        chunks: list,
    ):

        with self.driver.session() as session:

            for chunk in chunks:

                graph = await self.extract(chunk.page_content)

                self.store(
                    session,
                    graph,
                )



    async def extract(
        self,
        text: str,
    ) -> GraphExtraction:

        response = self.client.chat.completions.create(

            model=MODEL,

            response_format={"type": "json_object"},

            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
        )

        content = response.choices[0].message.content

        data = json.loads(content)

        return GraphExtraction.model_validate(data)


    def store(
        self,
        session,
        graph: GraphExtraction,
    ):

        for entity in graph.entities:

            session.run(
                """
                MERGE (e:Entity {id:$id})

                SET
                    e.name=$name,
                    e.type=$type,
                    e.description=$description
                """,
                id=entity.id,
                name=entity.name,
                type=entity.type,
                description=entity.description,
            )

        for relation in graph.relations:

            session.run(
                """
                MATCH (a:Entity {id:$source})

                MATCH (b:Entity {id:$target})

                MERGE (a)-[r:RELATED_TO {
                    type:$type
                }]->(b)

                SET
                    r.description=$description
                """,
                source=relation.source,
                target=relation.target,
                type=relation.type,
                description=relation.description,
            )

    def close(self):

        self.driver.close()