-- Validación humana HITL + preguntas extraídas de documentos.
-- Idempotente.

CREATE TABLE IF NOT EXISTS public.document_questions (
    id character varying(36) PRIMARY KEY,
    document_id uuid,
    knowledge_base_id uuid,
    organization_id uuid,
    user_id character varying(36),
    question text NOT NULL,
    rationale text,
    status character varying(20) NOT NULL DEFAULT 'pending',
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    reviewed_at timestamp without time zone,
    reviewer_notes text
);

CREATE INDEX IF NOT EXISTS idx_document_questions_doc
    ON public.document_questions (document_id);

CREATE INDEX IF NOT EXISTS idx_document_questions_kb
    ON public.document_questions (knowledge_base_id);

CREATE TABLE IF NOT EXISTS public.rag_human_reviews (
    id character varying(36) PRIMARY KEY,
    source character varying(40) NOT NULL DEFAULT 'chat',
    user_id character varying(36),
    organization_id uuid,
    conversation_id character varying(36),
    document_id uuid,
    question text NOT NULL,
    answer text,
    context_snippet text,
    chunk_ids jsonb,
    status character varying(20) NOT NULL DEFAULT 'pending',
    corrected_answer text,
    reviewer_notes text,
    reviewer_id character varying(36),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    reviewed_at timestamp without time zone
);

CREATE INDEX IF NOT EXISTS idx_rag_human_reviews_status
    ON public.rag_human_reviews (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_rag_human_reviews_org
    ON public.rag_human_reviews (organization_id);
