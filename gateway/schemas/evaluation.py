from pydantic import BaseModel, Field
from typing import Optional, Any, Literal


class QuestionBankItem(BaseModel):
    question: str
    keywords: list[str] = Field(default_factory=list)
    reference_answer: Optional[str] = None
    category: str = "general"
    split: Literal["dev", "holdout"] = "dev"
    out_of_knowledge: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class QuestionBankImportRequest(BaseModel):
    questions: list[QuestionBankItem]


class SimulatorSearchRequest(BaseModel):
    question: str
    knowledge_base_id: str | None = None
    evaluation_mode: bool = False


class SimulatorFlags(BaseModel):
    different_info: bool = False
    out_of_knowledge: bool = False


class SimulatorSaveRequest(BaseModel):
    question: str
    selected_chunk_ids: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    reference_answer: str | None = None
    category: str | None = None
    flags: SimulatorFlags


class EvaluationConfig(BaseModel):
    model_name: str = "llama3.2:latest"
    embedding_model: str = "qwen3-embedding:latest"
    retrieval_k: int = 10
    bm25_k: int = 10
    rrf_k: int = 60
    candidate_k: int = 15
    top_k: int = 5
    reranker_model: Optional[str] = "BAAI/bge-reranker-v2-m3"
    reranker_batch_size: int = 16
    retrieval_method: str = "dense_bm25_rrf_rerank"
    distance_metric: str = "cosine"


class DatasetEvaluationRequest(BaseModel):
    model_name: str = "llama3.2:latest"
    embedding_model: str = "qwen3-embedding:latest"
    top_k: int = Field(default=5, ge=1)
    retrieval_k: int = Field(default=10, ge=1)
    bm25_k: int = Field(default=10, ge=1)
    rrf_k: int = Field(default=60, ge=1)
    candidate_k: int = Field(default=15, ge=1)
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_batch_size: int = Field(default=16, ge=1)
    split: Literal["dev", "holdout", "all"] = "dev"
    evaluation_mode: bool = True
    similarity_strategy: str | None = None
    reranking_strategy: str | None = None
    agentic_rag_enabled: bool = False
    rag_strategy: str | None = None

    distance_metric: Literal[
        "cosine",
        "euclidean",
        "inner_product",
    ] = "cosine"


class DatasetEvaluationResponse(BaseModel):
    run_id: int
    model_name: str
    embedding_model: str | None = None
    dataset_size: int
    evaluated_questions: int
    pending_questions: int
    normal_questions: int
    different_info_questions: int
    out_of_knowledge_questions: int
    recall_1: float
    recall_k: float
    precision_at_k: float
    ndcg: float
    mrr: float
    false_positives: int
    failures: int
    duration_ms: float
    status: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    dataset_name: str | None = None
    model_date: str | None = None
    cached: bool = False
    created_at: str | None = None
    artifacts_path: str | None = None


class AnswerEvaluation(BaseModel):
    feedback: str
    accuracy: float = Field(ge=1, le=5)
    completeness: float = Field(ge=1, le=5)
    relevance: float = Field(ge=1, le=5)
    faithfulness: float = Field(ge=1, le=5)
    groundedness: float = Field(ge=1, le=5)
    citation_accuracy: float = Field(ge=0, le=1)
    numeric_match: float = Field(ge=0, le=1)
    abstention: float = Field(ge=0, le=1)


class EvaluationHistoryItem(BaseModel):
    id: int
    created_at: str
    model_name: str
    embedding_model: str
    dataset_size: int
    top_k: int
    recall_1: float
    recall_k: float
    mrr: float
    false_positives: int
    failures: int
    duration_ms: float
    status: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class EvaluationResultItem(BaseModel):
    id: int
    dataset_id: int
    question: str
    expected_chunk_id: Optional[str]
    retrieved_chunk_ids: list[str]
    retrieved_scores: list[float]
    expected_rank: Optional[int]
    hit_at_1: bool
    hit_at_k: bool
    reciprocal_rank: float
    false_positive: bool
    failure: bool
    flag_different_info: bool
    flag_out_of_knowledge: bool
    retrieval_latency_ms: Optional[float]
