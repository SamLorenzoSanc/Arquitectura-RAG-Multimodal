-- Migración idempotente. No elimina ni reconstruye datos.
CREATE EXTENSION IF NOT EXISTS vector;

-- CONCURRENTLY evita bloquear escrituras; ejecutar fuera de una transacción.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_vector_hnsw
ON public.embeddings
USING hnsw ((subvector(vector, 1, 2000)::vector(2000)) vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

ANALYZE public.embeddings;

-- Verificación manual reproducible:
-- SET enable_seqscan = off;
-- EXPLAIN (ANALYZE, BUFFERS)
-- SELECT id FROM public.embeddings
-- ORDER BY subvector(vector, 1, 2000)::vector(2000)
--          <=> subvector('[0,0,...]'::vector, 1, 2000)::vector(2000)
-- LIMIT 10;
