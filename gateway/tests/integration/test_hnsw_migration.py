import os
from pathlib import Path

import psycopg2
import pytest
from dotenv import load_dotenv

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env", override=False)


def _test_dsn() -> str:
    explicit = os.getenv("TEST_DATABASE_DSN")
    if explicit:
        return explicit
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("TEST_DATABASE_NAME", "agrops_test")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def test_hnsw_migration_creates_index_without_data_loss():
    dsn = _test_dsn()
    try:
        connection = psycopg2.connect(dsn)
    except psycopg2.OperationalError as exc:
        pytest.skip(f"Postgres de integración no disponible: {exc}")

    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cursor.execute("DROP TABLE IF EXISTS public.embeddings")
            cursor.execute(
                "CREATE TABLE public.embeddings "
                "(id bigserial PRIMARY KEY, vector vector(4096) NOT NULL)"
            )
            first = "[1," + ",".join(["0"] * 4095) + "]"
            second = "[0,1," + ",".join(["0"] * 4094) + "]"
            cursor.execute(
                "INSERT INTO public.embeddings(vector) VALUES (%s), (%s)",
                (first, second),
            )
            migration = (
                _REPO_ROOT / "postgres" / "migrations" / "001_hnsw_embeddings.sql"
            ).read_text(encoding="utf-8")
            # Quitar comentarios de línea antes de partir por ';'
            # (un ';' dentro de un comentario no debe crear un statement).
            executable = "\n".join(
                line
                for line in migration.splitlines()
                if line.strip() and not line.lstrip().startswith("--")
            )
            for statement in executable.split(";"):
                sql = statement.strip()
                if sql:
                    cursor.execute(sql)
            cursor.execute("SELECT count(*) FROM public.embeddings")
            assert cursor.fetchone()[0] == 2
            cursor.execute(
                "SELECT indexdef FROM pg_indexes "
                "WHERE schemaname='public' AND indexname='idx_embeddings_vector_hnsw'"
            )
            row = cursor.fetchone()
            assert row is not None
            assert "USING hnsw" in row[0]
    finally:
        connection.close()
