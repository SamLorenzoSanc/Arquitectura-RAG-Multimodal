-- Indexador de embeddings: catálogo de modelos + estado por documento×modelo.
CREATE TABLE IF NOT EXISTS public.embedding_model (
    id UUID PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    runtime_model_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    dimensions INTEGER NOT NULL DEFAULT 768,
    max_input_tokens INTEGER,
    chunk_max_tokens INTEGER,
    chunk_overlap INTEGER,
    status TEXT NOT NULL DEFAULT 'inactive'
        CHECK (status IN ('active', 'inactive')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.embedding_index_state (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL
        REFERENCES public.documents(id) ON DELETE CASCADE,
    embedding_model_id UUID NOT NULL
        REFERENCES public.embedding_model(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'indexing', 'indexed', 'failed')),
    source_hash TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    leased_until TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, embedding_model_id)
);

CREATE INDEX IF NOT EXISTS idx_embedding_index_state_status
    ON public.embedding_index_state (status, updated_at);

CREATE INDEX IF NOT EXISTS idx_embedding_index_state_document
    ON public.embedding_index_state (document_id);

INSERT INTO public.embedding_model (
    id, slug, runtime_model_id, display_name, dimensions, status
) VALUES
    (
        'a0e1b2c3-0001-4000-8000-000000000001',
        'nomic-embed-text',
        'nomic-embed-text',
        'Nomic Embed Text',
        768,
        'active'
    ),
    (
        'a0e1b2c3-0002-4000-8000-000000000002',
        'qwen3-embedding',
        'qwen3-embedding:latest',
        'Qwen3 Embedding',
        1024,
        'inactive'
    ),
    (
        'a0e1b2c3-0003-4000-8000-000000000003',
        'mxbai-embed-large',
        'mxbai-embed-large',
        'mixedbread large',
        1024,
        'inactive'
    ),
    (
        'a0e1b2c3-0004-4000-8000-000000000004',
        'bge-m3',
        'bge-m3',
        'BGE-M3',
        1024,
        'inactive'
    )
ON CONFLICT (slug) DO NOTHING;
