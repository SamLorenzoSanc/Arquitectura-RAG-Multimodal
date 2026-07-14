from pydantic import BaseModel


class MetricsResponse(BaseModel):
    requests: int
    average_latency: float
    retrieval_time: float
    generation_time: float
    reranking_time: float