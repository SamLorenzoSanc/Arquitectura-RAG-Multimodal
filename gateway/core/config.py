from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    APP_NAME: str = "AgroRAG Gateway"

    DEBUG: bool = True

    RAG_SERVICE_URL: str = "http://rag-service:8001"

    INGESTION_SERVICE_URL: str = "http://ingestion-service:8002"

    AUTH_SERVICE_URL: str = "http://auth-service:8003"

    class Config:

        env_file = ".env"


settings = Settings()