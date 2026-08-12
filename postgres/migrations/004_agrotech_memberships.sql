-- Asegura org global AgroTech + membership de todos los usuarios activos.
-- Idempotente.

INSERT INTO organizations (id, name, description, active)
SELECT gen_random_uuid(), 'AgroTech',
       'Organización global compartida (base de conocimiento de referencia)',
       true
WHERE NOT EXISTS (
  SELECT 1 FROM organizations WHERE lower(name) = lower('AgroTech')
);

INSERT INTO tenants (id, organization_id, name, description, active)
SELECT gen_random_uuid(), o.id, 'Default', 'Tenant AgroTech', true
FROM organizations o
WHERE lower(o.name) = lower('AgroTech')
  AND NOT EXISTS (
    SELECT 1 FROM tenants t WHERE t.organization_id = o.id
  );

INSERT INTO knowledge_bases (id, tenant_id, name, description, chroma_collection)
SELECT gen_random_uuid(), t.id, 'General', 'Knowledge Base global AgroTech',
       'col_' || replace(t.id::text, '-', '')
FROM tenants t
JOIN organizations o ON o.id = t.organization_id
WHERE lower(o.name) = lower('AgroTech')
  AND NOT EXISTS (
    SELECT 1 FROM knowledge_bases kb WHERE kb.tenant_id = t.id
  );

INSERT INTO organization_members (organization_id, user_id, role_id, active)
SELECT
  o.id,
  u.id,
  COALESCE(
    (SELECT id FROM roles WHERE name = 'USER' AND organization_id IS NULL LIMIT 1),
    (SELECT id FROM roles WHERE name = 'ORG_ADMIN' AND organization_id IS NULL LIMIT 1),
    (SELECT id FROM roles WHERE organization_id IS NULL ORDER BY id LIMIT 1)
  ),
  true
FROM users u
CROSS JOIN organizations o
WHERE lower(o.name) = lower('AgroTech')
  AND u.active = true
  AND COALESCE(
    (SELECT id FROM roles WHERE name = 'USER' AND organization_id IS NULL LIMIT 1),
    (SELECT id FROM roles WHERE name = 'ORG_ADMIN' AND organization_id IS NULL LIMIT 1),
    (SELECT id FROM roles WHERE organization_id IS NULL ORDER BY id LIMIT 1)
  ) IS NOT NULL
ON CONFLICT (organization_id, user_id) DO UPDATE
SET active = true,
    role_id = COALESCE(organization_members.role_id, EXCLUDED.role_id);

UPDATE organization_members om
SET role_id = COALESCE(
  om.role_id,
  (SELECT id FROM roles WHERE name = 'USER' AND organization_id IS NULL LIMIT 1),
  (SELECT id FROM roles WHERE name = 'ORG_ADMIN' AND organization_id IS NULL LIMIT 1)
)
FROM organizations o
WHERE om.organization_id = o.id
  AND lower(o.name) = lower('AgroTech')
  AND om.role_id IS NULL;
