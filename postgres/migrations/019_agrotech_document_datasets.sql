-- Backfill: un dataset RAG por documento, propiedad de AgroTech.
-- Idempotente: no duplica datasets ya vinculados al mismo document_id.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TEMP TABLE agrotech_scope AS
SELECT o.id AS org_id, t.id AS tenant_id, kb.id AS kb_id
FROM organizations o
JOIN tenants t ON t.organization_id = o.id
JOIN knowledge_bases kb ON kb.tenant_id = t.id
WHERE lower(o.name) = 'agrotech'
ORDER BY kb.name
LIMIT 1;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM agrotech_scope) THEN
        RAISE EXCEPTION 'No existe la organización AgroTech';
    END IF;
END $$;

UPDATE documents d
SET tenant_id = a.tenant_id,
    knowledge_base_id = a.kb_id
FROM agrotech_scope a
WHERE d.tenant_id IS DISTINCT FROM a.tenant_id
   OR d.knowledge_base_id IS DISTINCT FROM a.kb_id;

INSERT INTO department_knowledge_bases (
    department_id, knowledge_base_id, organization_id, created_by
)
SELECT d.id, a.kb_id, a.org_id, om.user_id
FROM agrotech_scope a
JOIN departments d ON d.organization_id = a.org_id
CROSS JOIN LATERAL (
    SELECT om.user_id
    FROM organization_members om
    WHERE om.organization_id = a.org_id AND om.active IS TRUE
    ORDER BY om.user_id
    LIMIT 1
) om
WHERE lower(d.name) IN ('it', 'rrhh')
ON CONFLICT DO NOTHING;

INSERT INTO rag_datasets (
    id, organization_id, tenant_id, knowledge_base_id, name, description,
    source_type, source_name, source_metadata, mapping, status, row_count, created_by
)
SELECT
    gen_random_uuid(),
    a.org_id,
    a.tenant_id,
    a.kb_id,
    COALESCE(NULLIF(d.title, ''), d.filename),
    COALESCE(
        NULLIF(d.description, ''),
        'Dataset generado a partir del documento indexado en AgroTech.'
    ),
    'document',
    d.filename,
    jsonb_build_object(
        'document_id', d.id,
        'filename', d.filename,
        'origin', 'existing_document'
    ),
    jsonb_build_object(
        'prompt', 'prompt',
        'context', 'context',
        'expected_response', 'expected_response',
        'metadata', 'metadata'
    ),
    'ready',
    GREATEST(
        (SELECT count(*) FROM chunks c WHERE c.document_id = d.id),
        1
    ),
    om.user_id
FROM documents d
CROSS JOIN agrotech_scope a
CROSS JOIN LATERAL (
    SELECT om.user_id
    FROM organization_members om
    WHERE om.organization_id = a.org_id AND om.active IS TRUE
    ORDER BY om.user_id
    LIMIT 1
) om
WHERE d.tenant_id = a.tenant_id
  AND NOT EXISTS (
      SELECT 1
      FROM rag_datasets rd
      WHERE rd.organization_id = a.org_id
        AND rd.source_metadata->>'document_id' = d.id::text
  );

INSERT INTO rag_dataset_rows (
    dataset_id, organization_id, tenant_id, knowledge_base_id, source, status,
    "traceId", prompt, context, expected_response, expected_context,
    metadata, pipeline, code_hash
)
SELECT
    rd.id,
    rd.organization_id,
    rd.tenant_id,
    rd.knowledge_base_id,
    'document',
    'ready',
    c.id::text,
    format(
        '¿Qué información aporta la sección «%s» de %s?',
        COALESCE(NULLIF(c.headline, ''), 'fragmento ' || c.position),
        COALESCE(d.title, d.filename)
    ),
    jsonb_build_array(c.content),
    COALESCE(NULLIF(c.summary, ''), left(c.content, 1000)),
    '[]'::jsonb,
    jsonb_build_object(
        'document_id', d.id,
        'filename', d.filename,
        'chunk_id', c.id,
        'chunk_position', c.position,
        'origin', 'document'
    ),
    '{}'::jsonb,
    encode(
        sha256(
            convert_to(rd.id::text || ':' || c.id::text || ':' || c.position::text, 'UTF8')
        ),
        'hex'
    )
FROM rag_datasets rd
JOIN documents d
  ON d.id::text = rd.source_metadata->>'document_id'
JOIN chunks c ON c.document_id = d.id
WHERE rd.source_type = 'document'
  AND rd.source_metadata->>'origin' = 'existing_document'
ON CONFLICT (dataset_id, code_hash) DO NOTHING;

INSERT INTO rag_dataset_rows (
    dataset_id, organization_id, tenant_id, knowledge_base_id, source, status,
    prompt, context, expected_response, expected_context, metadata, pipeline, code_hash
)
SELECT
    rd.id,
    rd.organization_id,
    rd.tenant_id,
    rd.knowledge_base_id,
    'document',
    'ready',
    format('¿Qué información relevante contiene %s?', COALESCE(d.title, d.filename)),
    '[]'::jsonb,
    COALESCE(
        NULLIF(d.description, ''),
        'Documento registrado en AgroTech: ' || d.filename
    ),
    '[]'::jsonb,
    jsonb_build_object(
        'document_id', d.id,
        'filename', d.filename,
        'origin', 'document_without_chunks'
    ),
    '{}'::jsonb,
    encode(sha256(convert_to(rd.id::text || ':placeholder', 'UTF8')), 'hex')
FROM rag_datasets rd
JOIN documents d
  ON d.id::text = rd.source_metadata->>'document_id'
WHERE rd.source_type = 'document'
  AND rd.source_metadata->>'origin' = 'existing_document'
  AND NOT EXISTS (SELECT 1 FROM chunks c WHERE c.document_id = d.id)
  AND NOT EXISTS (SELECT 1 FROM rag_dataset_rows r WHERE r.dataset_id = rd.id)
ON CONFLICT (dataset_id, code_hash) DO NOTHING;

INSERT INTO rag_dataset_departments (dataset_id, department_id)
SELECT rd.id, dept.id
FROM rag_datasets rd
JOIN organizations o ON o.id = rd.organization_id
JOIN departments dept ON dept.organization_id = o.id
JOIN documents d ON d.id::text = rd.source_metadata->>'document_id'
WHERE lower(o.name) = 'agrotech'
  AND rd.source_metadata->>'origin' = 'existing_document'
  AND (
      (
          lower(dept.name) = 'rrhh'
          AND d.filename ~* '(vida_laboral|alejandro|alicia|lancaster|jose arcadio|cultura)'
      )
      OR (
          lower(dept.name) = 'it'
          AND d.filename !~* '(vida_laboral|alejandro|alicia|lancaster|jose arcadio|cultura)'
      )
  )
ON CONFLICT DO NOTHING;

UPDATE rag_datasets rd
SET row_count = (
        SELECT count(*) FROM rag_dataset_rows r WHERE r.dataset_id = rd.id
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE rd.source_metadata->>'origin' = 'existing_document';
