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

export interface RagDatasetDetail {
  dataset: Record<string, unknown>;
  rows: Array<Record<string, unknown>>;
  offset: number;
  limit: number;
}
