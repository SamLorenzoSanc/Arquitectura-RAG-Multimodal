/* --- types/dataset.ts --- */
export const RAG_FIELDS = [
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
] as const;

export type RagField = (typeof RAG_FIELDS)[number];
export type DatasetSource = "file" | "logs" | "synthetic" | "demo";
export type DatasetStatus =
  | "draft"
  | "processing"
  | "pending_review"
  | "ready"
  | "failed";

export interface RagDataset {
  id: string;
  name: string;
  description?: string | null;
  source: DatasetSource;
  source_type?: string;
  source_name?: string | null;
  status: DatasetStatus;
  row_count?: number;
  knowledge_base_id: string;
  knowledge_base_name?: string;
  department_ids?: string[];
  departments?: Array<{ id: string; name: string }>;
  mapping?: DatasetMapping;
  source_metadata?: {
    kind?: "tabular" | "chunks";
    format?: string;
    [key: string]: unknown;
  };
  created_at?: string;
  updated_at?: string;
}

export type DatasetMapping = Partial<Record<RagField, string>>;

export interface DatasetChunk {
  chunk_index: number;
  headline: string;
  summary: string;
  fragment: string;
  characters: number;
  filename?: string;
  title?: string;
  metadata?: Record<string, unknown>;
}

export interface DatasetPreview {
  columns: string[];
  rows: Array<Record<string, unknown>>;
  total_rows?: number;
  kind?: "tabular" | "chunks";
  format?: string;
  filename?: string;
  schema_mapping?: Record<string, { columnType: string }>;
  suggested_mapping?: DatasetMapping;
  chunks?: DatasetChunk[];
}

export interface DemoCatalogItem {
  id: string;
  name: string;
  description: string;
  row_count: number;
}

export interface DatasetBaseInput {
  name: string;
  organization_id: string;
  knowledge_base_id: string;
  department_ids: string[];
  mapping: DatasetMapping;
}

export interface SyntheticConfig {
  rows: number;
  topic: string;
  instructions?: string;
  destination: "human_validation";
}

export type CreateDatasetInput =
  | (DatasetBaseInput & { source: "file" | "logs"; file: File })
  | (DatasetBaseInput & {
      source: "synthetic";
      synthetic: SyntheticConfig;
    })
  | (DatasetBaseInput & { source: "demo"; catalogId: string });

export interface UpdateDatasetInput {
  name?: string;
  description?: string | null;
  knowledge_base_id?: string | null;
  department_ids?: string[];
  mapping?: DatasetMapping;
}

export interface DatasetAddColumnInput {
  column_name: string;
  prompt_template: string;
  limit?: number;
}

export interface DatasetTraceSpan {
  name: string;
  content: string;
}

export interface DatasetTrace {
  traceId: string;
  row_id?: string;
  timestamp?: string | null;
  prompt?: string | null;
  response?: string | null;
  context?: unknown;
  spans: DatasetTraceSpan[];
  guardrails?: { passed?: boolean; flags?: string[]; details?: Record<string, unknown> };
  llm_columns?: Record<string, unknown>;
}

export interface GuardrailRowVerdict {
  row_id: string;
  traceId: string;
  passed: boolean;
  flags: string[];
  details?: Record<string, unknown>;
}

export interface GuardrailRunResult {
  id: string;
  scanned: number;
  passed: number;
  flagged: number;
  flags: Record<string, number>;
  rows?: GuardrailRowVerdict[];
}

export const DEFAULT_LLM_COLUMN_TEMPLATE =
  "Evalúa en una frase si la respuesta está fundada en el contexto.\nPregunta: {{prompt}}\nContexto: {{context}}\nRespuesta: {{response}}";

/* --- types/chat.ts --- */
export interface ChatRequest {
    question: string;
    conversation_id?: string | null;
    history?: Array<{ role: string; content: string }>;
    knowledge_base_id?: string;
    department_id?: string;
    use_rag?: boolean;
    organization_id?: string;
    organization_name?: string;
    model?: string;
    rag_mode?: "hybrid" | "agentic" | "compare";
    /** Modos estilo Cursor: agent | plan | debug | multitask */
    agent_mode?: "agent" | "plan" | "debug" | "multitask";
    use_query_rewrite?: boolean;
    use_reranking?: boolean;
    retrieval_k?: number;
    final_k?: number;
    temperature?: number;
}

export interface AgentTraceStep {
    tool: string;
    reason?: string;
    ok?: boolean;
    latency_ms?: number;
    summary?: string;
    n_chunks?: number;
    intent?: string;
    planner?: string;
}

export type LiveProcessStepStatus = "pending" | "running" | "done" | "error";

export interface LiveProcessStep {
    id: string;
    label: string;
    detail?: string;
    status: LiveProcessStepStatus;
}

export type RagFlowNodeId =
    | "pregunta"
    | "agente"
    | "sql"
    | "memoria"
    | "retrieve"
    | "dense"
    | "bm25"
    | "rrf"
    | "grade"
    | "rewrite"
    | "generate"
    | "respuesta";

export type RagFlowNodeState =
    | "idle"
    | "active"
    | "done"
    | "error"
    | "skipped";

export type ChatStreamEvent =
    | { type: "meta"; conversation_id?: string; message?: string }
    | { type: "status"; phase?: string; message?: string }
    | { type: "intent"; intent?: string; message?: string }
    | {
          type: "plan";
          intent?: string;
          tools?: string[];
          steps?: Array<{ tool?: string; reason?: string; planner?: string }>;
          message?: string;
      }
    | {
          type: "tool_start";
          tool?: string;
          reason?: string;
          message?: string;
      }
    | {
          type: "tool_end";
          tool?: string;
          reason?: string;
          ok?: boolean;
          latency_ms?: number;
          summary?: string;
          n_chunks?: number;
          message?: string;
      }
    | { type: "grade"; grade?: string; message?: string; n_chunks?: number }
    | { type: "rewrite"; query?: string; message?: string }
    | { type: "abstain"; message?: string }
    | { type: "token"; delta?: string }
    | { type: "done"; payload?: ChatResponse }
    | { type: "error"; detail?: string };

export interface ModeComparisonSide {
    mode: string;
    architecture?: string | null;
    answer: string;
    context?: ContextChunk[];
    retrieval?: RetrievalInfo | null;
    retrieval_details?: any;
    agent_trace?: AgentTraceStep[] | null;
    related_questions?: string[];
    latency_ms?: number | null;
}

export interface ChatResponse {
    conversation_id: string;
    answer: string;
    context: ContextChunk[];
    retrieval: RetrievalInfo;
    retrieval_details?: any;
    related_questions?: string[];
    rag_mode?: string | null;
    agent_mode?: string | null;
    architecture?: string | null;
    agent_trace?: AgentTraceStep[] | null;
    comparison?: {
        hybrid?: ModeComparisonSide;
        agentic?: ModeComparisonSide;
        note?: string;
    } | null;
    review_id?: string | null;
}


export interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
    sources?: Array<{
        source?: string;
        score?: number;
        chunk_id?: string;
        snippet?: string;
    }>;
    pendingReview?: boolean;
}

export interface ChatContext {
    type: string;
    page_content: string;
    metadata: {
        source?: string;
        type?: string;
        document_id?: string;
        chunk_id?: string;
        score?: number;
        page?: number;
        title?: string;
        author?: string;
        created_at?: string;
        [key: string]: any;
    };
}

export interface Conversation {
    id:string;
    title:string;
    created_at:string;
    updated_at:string;
}

export interface RetrievalInfo {
    original_query: string;
    rewritten_query: string;
    retrieved_chunks: number;
    rewritten_chunks: number;
    merged_chunks: number;
    final_chunks: number;
    retrieval_k: number;
    final_k: number;
    reranking: boolean;
    architecture?: string | null;
    agent_tools?: string[] | null;
    intent?: string | null;
    strategy?: string | null;
}



export interface ContextChunk {
    page_content:string;
    type:string;
    metadata:any;
}

export interface ChatMessage {
    role:
        "user"
        |
        "assistant";
    content:string;

}

export interface ConversationMessage {
    id: string;
    role: "user" | "assistant" | "system";
    content: string;
}

export interface ConversationResponse {
    conversation_id: string;
    title: string;
    messages: ConversationMessage[];
}

export interface ConversationHistoryItem {
    id: string;
    title: string;
    created_at?: string | null;
    updated_at?: string | null;
    user_id?: string | null;
    user_name: string;
    user_email: string;
    message_count: number;
    first_user_message?: string;
}

export interface ConversationHistoryUserSummary {
    user_id: string;
    user_name: string;
    user_email: string;
    conversation_count: number;
    message_count: number;
}

export interface UserConversationHistoryResponse {
    tenant_id: string;
    total_conversations: number;
    users: ConversationHistoryUserSummary[];
    conversations: ConversationHistoryItem[];
    note?: string;
}

export interface ConversationHistoryDetail {
    conversation_id: string;
    title: string;
    user_id?: string | null;
    user_name?: string;
    user_email?: string;
    created_at?: string | null;
    updated_at?: string | null;
    messages: Array<ConversationMessage & { created_at?: string | null }>;
}
/* --- types/evaluation.ts --- */

export type EvaluationCategory = "prompt" | "context" | "response" | "text";
export type ThresholdOperator = "gte" | "lte";

export interface EvaluationMetric {
  id: string;
  name: string;
  description: string;
  category: EvaluationCategory;
  required_fields: string[];
  default_threshold: { operator: ThresholdOperator; value: number };
  engine: string;
  compatible: boolean;
  missing_fields: string[];
}

export interface EvaluationCatalog {
  provider: "ollama";
  models: string[];
  fields: RagField[];
  metrics: EvaluationMetric[];
}

export interface EvaluationFilters {
  split: "dev" | "holdout" | "all";
  categories: string[];
  statuses: string[];
  limit: number;
}

export interface EvaluationConfig {
  id: string;
  dataset_id: string;
  name: string;
  provider: "ollama";
  model_name: string;
  metrics: string[];
  mapping: Record<string, RagField>;
  thresholds: Record<
    string,
    { operator: ThresholdOperator; value: number }
  >;
  filters: EvaluationFilters;
  created_at?: string;
  updated_at?: string;
}

export interface EvaluationConfigInput {
  dataset_id: string;
  name: string;
  provider: "ollama";
  model_name: string;
  metrics: string[];
  mapping: Record<string, RagField>;
  thresholds: EvaluationConfig["thresholds"];
  filters: EvaluationFilters;
}

export interface EvaluationResult {
  id: string;
  dataset_row_id: string;
  metric: string;
  value: number;
  passed: boolean;
  explanation?: string;
  latency_ms?: number;
}

export interface EvaluationRun {
  id: string;
  config_id: string;
  status: string;
  aggregates: Record<string, number>;
  row_count: number;
  passed_count: number;
  failed_count: number;
  cached?: boolean;
  started_at?: string;
  finished_at?: string;
  results?: EvaluationResult[];
}

export type RetrievalStrategy =
  | "dense"
  | "bm25"
  | "hybrid_rrf"
  | "hybrid_rrf_rerank"
  | "hybrid_expansion_rrf"
  | "hybrid_expansion_rrf_rerank";

export interface RetrievalExperimentRun {
  id: number;
  created_at: string;
  model_name?: string;
  embedding_model: string;
  distance_metric: string;
  retrieval_strategy?: RetrievalStrategy;
  dataset_size: number;
  evaluated_questions?: number;
  top_k: number;
  recall_1: number;
  recall_k: number;
  precision_at_k?: number | null;
  mrr: number;
  ndcg?: number | null;
  keyword_coverage?: number | null;
  false_positives?: number;
  failures: number;
  duration_ms: number;
  experiment_type?: string;
  parameters?: Record<string, unknown>;
}

export interface ProbeChunk {
  id: string;
  rank: number;
  title: string;
  description: string;
  content: string;
  score?: number;
  distance: number | null;
}

export interface EvaluationBankItem {
  id: number;
  question: string;
  keywords?: string[];
  reference_answer?: string;
  category?: string;
  source?: string;
  source_file?: string;
  page?: string;
  validated?: boolean;
  annotated?: boolean;
  split?: string;
  out_of_knowledge?: boolean;
  different_info?: boolean;
  expected_chunk_ids?: string[];
}

export interface RagRuntimeConfig {
  generation_model: string;
  embedding_model: string;
  temperature: number;
  chunk_size_chars: number;
  chunk_overlap_chars: number;
  retrieval_k: number;
  bm25_k: number;
  rrf_k: number;
  final_k: number;
  eval_top_k: number;
  use_reranker: boolean;
  use_query_rewrite: boolean;
  note?: string;
}

export interface RetrievalStrategyComparison {
  runs: RetrievalExperimentRun[];
  best_mrr_id: number | null;
  note: string;
}

export type DistanceMetricId = "cosine" | "euclidean" | "manhattan";

export interface DistanceMetricsComparison {
  runs: RetrievalExperimentRun[];
  best_mrr_id: number | null;
  note: string;
}

export interface RagDatasetDetail {
  dataset: Record<string, unknown>;
  rows: Array<Record<string, unknown>>;
  offset: number;
  limit: number;
}

/* --- types/document.ts --- */
export interface IngestProgress {
    document_id?: string;
    stage?: string;
    percent?: number;
    status?: string;
    message?: string;
    chunks?: number;
    embedded?: number;
    total?: number;
    error?: string | null;
}

export interface IndexState {
    id: string;
    document_id?: string;
    status: "pending" | "indexing" | "indexed" | "failed" | string;
    attempts?: number;
    error?: string | null;
    slug?: string;
    display_name?: string;
    runtime_model_id?: string;
    updated_at?: string;
}

export interface IndexTask {
    id: string | null;
    document_id: string;
    filename: string;
    title?: string | null;
    knowledge_base_id: string;
    status: string;
    attempts?: number;
    error?: string | null;
    updated_at?: string | null;
    slug?: string | null;
    display_name?: string | null;
    runtime_model_id?: string | null;
}

export interface IndexCounts {
    total: number;
    indexed: number;
    pending: number;
    indexing: number;
    failed: number;
    none: number;
}

export interface IndexTasksResponse {
    counts: IndexCounts;
    items: IndexTask[];
    total: number;
    limit: number;
    offset: number;
}

export interface DocumentItem {
    id: string;
    filename: string;
    name?: string;
    title?: string;
    description?: string;
    size: number;
    mime_type?: string;
    content_type?: string;
    current_version: number;
    created_at: string;
    updated_at?: string;
    status?: "active" | "inactive";
    processing_status?: string;
    embedding_model?: string;
    generation_model?: string;
    llm_model?: string;
    chunks?: number;
    attempts?: number;
    error?: string | null;
    progress?: IngestProgress | null;
    knowledge_base_id?: string;
    knowledge_base_name?: string;
    index_states?: IndexState[];
}

export interface DocumentChunk {
    id: string;
    position: number;
    headline: string;
    summary: string;
    content: string;
    char_count: number;
    overlap_prev: number;
    embedding_models: string[];
}

export interface DocumentChunksResponse {
    id: string;
    filename: string;
    title: string;
    mime_type?: string;
    size?: number;
    knowledge_base_id: string;
    chunk_count: number;
    chunks: DocumentChunk[];
}

/* --- types/knowledge.ts --- */
export interface KnowledgeNode {
    id: string;
    type:
        | "document"
        | "chunk"
        | "entity"
        | "concept";

    label: string;
    document?: string;
    content?: string;
    metadata?: Record<string, any>;
    words?: number;
    x: number;
    y: number;
    z?: number;
    weight?: number;
    group?: string;
    has_embedding?: boolean;
}


export interface KnowledgeEdge {
    source: string;
    target: string;
    label?: string;
    weight?: number;
}


export interface KnowledgeGraph {
    nodes: KnowledgeNode[];
    edges: KnowledgeEdge[];
    stats: {
        nodes: number;
        edges: number;
        documents: number;
        average_similarity: number;
    };

}



export interface KnowledgeMap {

    organization: {
        id: string;
        name: string;
        description?: string;
    };


    statistics: {
        nodes: number;
        edges: number;
        documents: number;
        chunks: number;
        chunks_with_embedding?: number;
        chunks_without_embedding?: number;
        similarity_threshold?: number;
        average_similarity?: number;
        knowledge_base_id?: string | null;
    };


    graph: KnowledgeGraph;

}
/* --- types/organization.ts --- */

export type KnowledgeBaseSummary = {
  id: string;
  tenant_id: string;
  name: string;
  description?: string | null;
  use_case?: string | null;
  chroma_collection?: string | null;
  created_by?: string | null;
  created_by_name?: string | null;
  created_at?: string;
  document_count?: number;
  organization_id?: string;
  department_ids?: string[];
  knowledge_base_id?: string;
};

export interface Department {
    id: string;
    organization_id?: string;
    name: string;
    description?: string;
    members?: number;
}

export interface Member {
    id: string;
    name: string;
    email: string;
    role: string;
    departmentId?: string;
}

export interface Organization {
    id: string;
    name: string;
    description?: string;
    status?: string;
    is_global?: boolean;
    departments?: Department[];
    members?: Member[];
}

export interface OrgContextType {
    organizations: Organization[];
    selectedOrg: Organization | null;
    selectedDept: Department | null;
    knowledgeBases: KnowledgeBaseSummary[];
    generalKnowledgeBase: KnowledgeBaseSummary | null;
    setSelectedOrg: (org: Organization | null) => void;
    setSelectedDept: (dept: Department | null) => void;
    reloadKnowledgeBases: () => Promise<KnowledgeBaseSummary[]>;
    addOrganization: (name: string, description: string) => Promise<void>;
    setOrganizations: (orgs: Organization[]) => void;
}

/* --- types/tenant.ts --- */
export interface Tenant {
    id: string;
    organization_id: string;
    name: string;
    description: string | null;
    active: boolean;
}

export interface CreateTenantRequest {
    name: string;
    description?: string;
}

export interface UpdateTenantRequest {
    name?: string;
    description?: string;
    active?: boolean;
}

export interface TenantListResponse {
    items: Tenant[];
    total: number;
}
