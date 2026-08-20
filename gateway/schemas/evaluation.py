from pydantic import BaseModel, Field, model_validator
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
    distance_metric: Literal[
        "cosine",
        "euclidean",
        "manhattan",
        "inner_product",
        "l1",
        "l2",
    ] = "cosine"


class SimulatorFlags(BaseModel):
    different_info: bool = False
    out_of_knowledge: bool = False


class SimulatorSaveRequest(BaseModel):
    question: str
    selected_chunk_ids: list[str] = Field(default_factory=list)
    selected_chunk_id: str | None = None
    keywords: list[str] = Field(default_factory=list)
    reference_answer: str | None = None
    category: str | None = None
    flags: SimulatorFlags = Field(default_factory=SimulatorFlags)

    @model_validator(mode="after")
    def merge_selected_chunk(self):
        if (
            self.selected_chunk_id
            and self.selected_chunk_id not in self.selected_chunk_ids
        ):
            self.selected_chunk_ids = [*self.selected_chunk_ids, self.selected_chunk_id]
        return self


class EvaluationConfig(BaseModel):
    model_name: str = "llama3.2:latest"
    embedding_model: str = "nomic-embed-text"
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
    embedding_model: str = "nomic-embed-text"
    top_k: int = Field(default=5, ge=1)
    retrieval_k: int = Field(default=10, ge=1)
    bm25_k: int = Field(default=10, ge=1)
    rrf_k: int = Field(default=60, ge=1)
    candidate_k: int = Field(default=15, ge=1)
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_batch_size: int = Field(default=16, ge=1)
    split: Literal["dev", "holdout", "all"] = "dev"
    evaluation_mode: bool = True
    force: bool = False
    similarity_strategy: str | None = None
    reranking_strategy: str | None = None
    agentic_rag_enabled: bool = False
    rag_strategy: str | None = None
    temperature: float = Field(default=0, ge=0, le=2)

    distance_metric: Literal[
        "cosine",
        "euclidean",
        "inner_product",
        "manhattan",
        "l1",
        "l2",
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
    precision: float = Field(ge=1, le=5, default=3)
    completeness: float = Field(ge=1, le=5)
    relevance: float = Field(ge=1, le=5)
    faithfulness: float = Field(ge=1, le=5)
    groundedness: float = Field(ge=1, le=5)
    citation_accuracy: float = Field(ge=0, le=1)
    numeric_match: float = Field(ge=0, le=1)
    abstention: float = Field(ge=0, le=1)
    mrr: float = Field(default=0.0, ge=0, le=1)
    ndcg: float = Field(default=0.0, ge=0, le=1)
    keywords_found: int = 0
    total_keywords: int = 0
    keyword_coverage: float = Field(default=0.0, ge=0, le=100)


class EvaluationHistoryItem(BaseModel):
    id: int
    created_at: str
    model_name: str = ""
    embedding_model: str
    distance_metric: str = "cosine"
    dataset_size: int = 0
    top_k: int = 3
    recall_1: float = 0.0
    recall_k: float = 0.0
    precision_at_k: float | None = None
    ndcg: float | None = None
    mrr: float = 0.0
    keyword_coverage: float | None = None
    accuracy: float | None = None
    false_positives: int = 0
    failures: int = 0
    duration_ms: float = 0.0
    status: str = "completed"
    experiment_type: str = "retrieval_dataset"
    retrieval_strategy: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class ExperimentRunRequest(BaseModel):
    embedding_model: str = "nomic-embed-text"
    distance_metric: Literal[
        "cosine",
        "euclidean",
        "manhattan",
        "inner_product",
        "l1",
        "l2",
    ] = "cosine"
    top_k: int = Field(default=3, ge=1)
    knowledge_base_id: str | None = None
    persist: bool = True
    temperature: float = Field(default=0, ge=0, le=2)


class ExperimentCompareRequest(BaseModel):
    embedding_models: list[str] = Field(
        default_factory=lambda: ["nomic-embed-text"]
    )
    distance_metrics: list[str] = Field(
        default_factory=lambda: ["cosine", "euclidean", "manhattan"]
    )
    top_k: int = Field(default=3, ge=1)
    knowledge_base_id: str | None = None


RetrievalStrategy = Literal[
    "dense",
    "bm25",
    "hybrid_rrf",
    "hybrid_rrf_rerank",
    "hybrid_expansion_rrf",
    "hybrid_expansion_rrf_rerank",
]


class RetrievalStrategyCompareRequest(BaseModel):
    strategies: list[RetrievalStrategy] = Field(
        default_factory=lambda: [
            "dense",
            "bm25",
            "hybrid_rrf",
            "hybrid_rrf_rerank",
            "hybrid_expansion_rrf",
            "hybrid_expansion_rrf_rerank",
        ]
    )
    embedding_model: str = "nomic-embed-text"
    distance_metric: Literal[
        "cosine",
        "euclidean",
        "manhattan",
        "inner_product",
        "l1",
        "l2",
    ] = "cosine"
    top_k: int = Field(default=3, ge=1, le=50)
    organization_id: str | None = None
    department_id: str | None = None
    knowledge_base_id: str | None = None
    temperature: float = Field(default=0, ge=0, le=2)


class ExperimentCompareResponse(BaseModel):
    runs: list[EvaluationHistoryItem]
    best_mrr_id: int | None = None
    note: str = (
        "Las distancias (coseno, L2, L1) son comparables sobre el mismo embedding. "
        "Comparar embeddings distintos es válido tras reindexar el corpus con cada modelo."
    )


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


RagEvaluationField = Literal[
    "traceId",
    "prompt",
    "context",
    "response",
    "timestamp",
    "expected_response",
    "expected_context",
    "metadata",
    "pipeline",
    "alternate_response",
    "code_hash",
]


class MetricThreshold(BaseModel):
    operator: Literal["gte", "lte"] = "gte"
    value: float = Field(default=0.5, ge=0, le=1)


class EvaluationFilters(BaseModel):
    split: Literal["dev", "holdout", "all"] = "all"
    categories: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=lambda: ["ready", "approved"])
    limit: int = Field(default=100, ge=1, le=500)


class EvaluationLabConfigCreate(BaseModel):
    dataset_id: str
    name: str = Field(min_length=1, max_length=255)
    provider: Literal["ollama"] = "ollama"
    model_name: str = Field(default="llama3.2:latest", min_length=1, max_length=255)
    metrics: list[str] = Field(min_length=1)
    mapping: dict[str, RagEvaluationField] = Field(default_factory=dict)
    thresholds: dict[str, MetricThreshold] = Field(default_factory=dict)
    filters: EvaluationFilters = Field(default_factory=EvaluationFilters)

    @model_validator(mode="after")
    def unique_metrics(self):
        self.metrics = list(dict.fromkeys(self.metrics))
        return self


class EvaluationLabConfigUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    model_name: str | None = Field(default=None, min_length=1, max_length=255)
    metrics: list[str] | None = Field(default=None, min_length=1)
    mapping: dict[str, RagEvaluationField] | None = None
    thresholds: dict[str, MetricThreshold] | None = None
    filters: EvaluationFilters | None = None


class EvaluationLabRunRequest(BaseModel):
    force: bool = False


class EvaluationMetricDefinition(BaseModel):
    id: str
    name: str
    description: str
    category: Literal["prompt", "context", "response", "text"]
    required_fields: list[str]
    default_threshold: MetricThreshold
    engine: str
