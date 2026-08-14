CREATE TABLE IF NOT EXISTS public.rag_experiment_runs (
    id SERIAL PRIMARY KEY,
    tenant_id UUID,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    embedding_model TEXT NOT NULL,
    distance_metric TEXT NOT NULL,
    generation_model TEXT,
    experiment_type TEXT NOT NULL DEFAULT 'question_bank',
    dataset_size INTEGER NOT NULL DEFAULT 0,
    evaluated_questions INTEGER NOT NULL DEFAULT 0,
    recall_1 DOUBLE PRECISION,
    recall_k DOUBLE PRECISION,
    mrr DOUBLE PRECISION,
    ndcg DOUBLE PRECISION,
    precision_at_k DOUBLE PRECISION,
    keyword_coverage DOUBLE PRECISION,
    accuracy DOUBLE PRECISION,
    failures INTEGER NOT NULL DEFAULT 0,
    duration_ms DOUBLE PRECISION,
    status TEXT NOT NULL DEFAULT 'completed',
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_rag_experiment_runs_tenant_created
ON public.rag_experiment_runs (tenant_id, created_at DESC);
