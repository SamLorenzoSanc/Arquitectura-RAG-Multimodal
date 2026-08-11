import os
from pathlib import Path

import psycopg2
import pytest

pytestmark = pytest.mark.integration


def test_hnsw_migration_creates_index_without_data_loss():
    dsn = os.getenv(
        "TEST_DATABASE_DSN",
        "postgresql://postgres:postgres@localhost:5432/agrops_test",
    )
    connection = psycopg2.connect(dsn)
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
                Path(__file__).parents[3]
                / "postgres"
                / "migrations"
                / "001_hnsw_embeddings.sql"
            ).read_text(encoding="utf-8")
            for statement in migration.split(";"):
                sql = "\n".join(
                    line for line in statement.splitlines() if not line.lstrip().startswith("--")
                ).strip()
                if sql:
                    cursor.execute(sql)
            cursor.execute("SELECT count(*) FROM public.embeddings")
            assert cursor.fetchone()[0] == 2
            cursor.execute(
                "SELECT indexdef FROM pg_indexes "
                "WHERE schemaname='public' AND indexname='idx_embeddings_vector_hnsw'"
            )
            assert "USING hnsw" in cursor.fetchone()[0]
    finally:
        connection.close()
