-- Varios embeddings por chunk: un vector por modelo.
ALTER TABLE public.embeddings DROP CONSTRAINT IF EXISTS embeddings_chunk_id_key;
DROP INDEX IF EXISTS embeddings_chunk_id_key;
DROP INDEX IF EXISTS ix_embeddings_chunk_id;

CREATE UNIQUE INDEX IF NOT EXISTS ux_embeddings_chunk_model
ON public.embeddings (chunk_id, model);
