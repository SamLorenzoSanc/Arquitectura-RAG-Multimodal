-- Compatibilidad con dumps generados en Render (owner = palmero).
-- Debe ejecutarse antes que seed.sql en docker-entrypoint-initdb.d.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'palmero') THEN
    CREATE ROLE palmero NOLOGIN;
  END IF;
END
$$;

GRANT palmero TO CURRENT_USER;
GRANT ALL ON SCHEMA public TO palmero;
