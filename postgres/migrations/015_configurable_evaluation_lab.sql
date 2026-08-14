-- Laboratorio declarativo de evaluación RAG. Idempotente para despliegues existentes.
CREATE TABLE IF NOT EXISTS public.rag_evaluation_configs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id uuid NOT NULL REFERENCES public.rag_datasets(id) ON DELETE CASCADE,
    organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    knowledge_base_id uuid REFERENCES public.knowledge_bases(id) ON DELETE SET NULL,
    name varchar(255) NOT NULL,
    provider varchar(40) NOT NULL DEFAULT 'ollama',
    model_name varchar(255) NOT NULL DEFAULT 'llama3.2:latest',
    metrics jsonb NOT NULL DEFAULT '[]'::jsonb,
    mapping jsonb NOT NULL DEFAULT '{}'::jsonb,
    thresholds jsonb NOT NULL DEFAULT '{}'::jsonb,
    filters jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_by uuid REFERENCES public.users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rag_eval_configs_scope
    ON public.rag_evaluation_configs (organization_id, tenant_id, dataset_id);

CREATE TABLE IF NOT EXISTS public.rag_evaluation_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id uuid NOT NULL REFERENCES public.rag_evaluation_configs(id) ON DELETE CASCADE,
    dataset_id uuid NOT NULL REFERENCES public.rag_datasets(id) ON DELETE CASCADE,
    organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    status varchar(30) NOT NULL DEFAULT 'running',
    fingerprint varchar(64) NOT NULL,
    parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    aggregates jsonb NOT NULL DEFAULT '{}'::jsonb,
    row_count integer NOT NULL DEFAULT 0,
    passed_count integer NOT NULL DEFAULT 0,
    failed_count integer NOT NULL DEFAULT 0,
    error text,
    started_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_rag_eval_runs_scope
    ON public.rag_evaluation_runs (organization_id, tenant_id, config_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_rag_eval_runs_fingerprint
    ON public.rag_evaluation_runs (config_id, fingerprint);

CREATE TABLE IF NOT EXISTS public.rag_evaluation_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id uuid NOT NULL REFERENCES public.rag_evaluation_runs(id) ON DELETE CASCADE,
    dataset_row_id uuid NOT NULL REFERENCES public.rag_dataset_rows(id) ON DELETE CASCADE,
    metric varchar(80) NOT NULL,
    value double precision,
    passed boolean NOT NULL DEFAULT false,
    explanation text,
    latency_ms double precision,
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (run_id, dataset_row_id, metric)
);

CREATE INDEX IF NOT EXISTS idx_rag_eval_results_run
    ON public.rag_evaluation_results (run_id, metric);
