-- Cuaderno de campo: agenda de anotaciones del agricultor.
-- Idempotente.

CREATE TABLE IF NOT EXISTS public.field_notebook_entries (
    id character varying(36) PRIMARY KEY,
    user_id character varying(36) NOT NULL,
    organization_id uuid,
    crop_id character varying(36),
    entry_date date NOT NULL,
    title character varying(180) NOT NULL,
    body text,
    category character varying(40) NOT NULL DEFAULT 'otro',
    reminder_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_field_notebook_user_date
    ON public.field_notebook_entries (user_id, entry_date);

CREATE INDEX IF NOT EXISTS idx_field_notebook_org
    ON public.field_notebook_entries (organization_id);

CREATE INDEX IF NOT EXISTS idx_field_notebook_crop
    ON public.field_notebook_entries (crop_id);
