ALTER TABLE public.retrieval_dataset
    ADD COLUMN IF NOT EXISTS split text NOT NULL DEFAULT 'dev',
    ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

UPDATE public.retrieval_dataset
SET split = CASE WHEN id % 5 = 0 THEN 'holdout' ELSE 'dev' END
WHERE split IS NULL OR split NOT IN ('dev', 'holdout');

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'retrieval_dataset_split_check'
    ) THEN
        ALTER TABLE public.retrieval_dataset
            ADD CONSTRAINT retrieval_dataset_split_check
            CHECK (split IN ('dev', 'holdout'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_retrieval_dataset_tenant_question_normalized
ON public.retrieval_dataset (tenant_id, lower(btrim(question)));
