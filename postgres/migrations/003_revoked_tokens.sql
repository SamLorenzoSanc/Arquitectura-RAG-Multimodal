-- Alinea el esquema de auth/tenants con el código del gateway.
-- Idempotente: seguro de re-ejecutar.

CREATE TABLE IF NOT EXISTS revoked_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token TEXT NOT NULL,
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_revoked_tokens_token ON revoked_tokens (token);
CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires_at ON revoked_tokens (expires_at);

-- La columna slug se eliminó del modelo ORM; no se crea aquí.
-- Si existiera en algún entorno legacy, se puede ignorar sin romper SELECTs actuales.
