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
  status: DatasetStatus;
  row_count?: number;
  knowledge_base_id: string;
  knowledge_base_name?: string;
  department_ids?: string[];
  departments?: Array<{ id: string; name: string }>;
  mapping?: DatasetMapping;
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
}

export interface DatasetPreview {
  columns: string[];
  rows: Array<Record<string, unknown>>;
  total_rows?: number;
  kind?: "tabular" | "chunks";
  format?: string;
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

export interface GuardrailRunResult {
  id: string;
  scanned: number;
  passed: number;
  flagged: number;
  flags: Record<string, number>;
}

export const DEFAULT_LLM_COLUMN_TEMPLATE =
  "Evalúa en una frase si la respuesta está fundada en el contexto.\nPregunta: {{prompt}}\nContexto: {{context}}\nRespuesta: {{response}}";
