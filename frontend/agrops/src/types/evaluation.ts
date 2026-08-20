import type { RagField } from "@/types/dataset";

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

export interface RagDatasetDetail {
  dataset: Record<string, unknown>;
  rows: Array<Record<string, unknown>>;
  offset: number;
  limit: number;
}
