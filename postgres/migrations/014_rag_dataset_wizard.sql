-- Backend del Wizard de datasets RAG. Idempotente y apto para despliegues existentes.

CREATE TABLE IF NOT EXISTS public.department_knowledge_bases (
    department_id uuid NOT NULL REFERENCES public.departments(id) ON DELETE CASCADE,
    knowledge_base_id uuid NOT NULL REFERENCES public.knowledge_bases(id) ON DELETE CASCADE,
    organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    created_by uuid REFERENCES public.users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (department_id, knowledge_base_id)
);

CREATE INDEX IF NOT EXISTS idx_department_kb_org
    ON public.department_knowledge_bases (organization_id);

CREATE TABLE IF NOT EXISTS public.rag_datasets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    knowledge_base_id uuid REFERENCES public.knowledge_bases(id) ON DELETE SET NULL,
    name varchar(255) NOT NULL,
    description text,
    source_type varchar(40) NOT NULL DEFAULT 'upload',
    source_name text,
    source_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    mapping jsonb NOT NULL DEFAULT '{}'::jsonb,
    status varchar(30) NOT NULL DEFAULT 'ready',
    row_count integer NOT NULL DEFAULT 0,
    created_by uuid REFERENCES public.users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rag_datasets_scope
    ON public.rag_datasets (organization_id, tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rag_datasets_kb
    ON public.rag_datasets (knowledge_base_id);

CREATE TABLE IF NOT EXISTS public.rag_dataset_rows (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id uuid NOT NULL REFERENCES public.rag_datasets(id) ON DELETE CASCADE,
    organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    knowledge_base_id uuid REFERENCES public.knowledge_bases(id) ON DELETE SET NULL,
    source varchar(80),
    status varchar(30) NOT NULL DEFAULT 'ready',
    "traceId" text,
    prompt text NOT NULL,
    context jsonb,
    response text,
    timestamp timestamptz,
    expected_response text,
    expected_context jsonb,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    pipeline jsonb,
    alternate_response text,
    code_hash varchar(64) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (dataset_id, code_hash)
);

CREATE INDEX IF NOT EXISTS idx_rag_dataset_rows_scope
    ON public.rag_dataset_rows (organization_id, tenant_id);
CREATE INDEX IF NOT EXISTS idx_rag_dataset_rows_dataset
    ON public.rag_dataset_rows (dataset_id, created_at);

CREATE TABLE IF NOT EXISTS public.rag_dataset_departments (
    dataset_id uuid NOT NULL REFERENCES public.rag_datasets(id) ON DELETE CASCADE,
    department_id uuid NOT NULL REFERENCES public.departments(id) ON DELETE CASCADE,
    PRIMARY KEY (dataset_id, department_id)
);

CREATE INDEX IF NOT EXISTS idx_rag_dataset_departments_dept
    ON public.rag_dataset_departments (department_id);
