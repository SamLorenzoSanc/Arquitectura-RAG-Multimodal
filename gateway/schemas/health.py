from pydantic import BaseModel


class ServiceHealth(BaseModel):
    service: str
    status: str


class HealthResponse(BaseModel):
    gateway: ServiceHealth
    rag_service: ServiceHealth
    ingestion_service: ServiceHealth
    chromadb: ServiceHealth
    ollama: ServiceHealth