import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agrops_postgres as pg  # noqa: E402


class SqlGuardTests(unittest.TestCase):
    def test_select_ok(self):
        sql = pg.validate_readonly_sql("SELECT id, content FROM chunks LIMIT 5")
        self.assertTrue(sql.lower().startswith("select"))

    def test_with_select_ok(self):
        sql = pg.validate_readonly_sql(
            "WITH x AS (SELECT id FROM documents) SELECT * FROM x"
        )
        self.assertTrue(sql.lower().startswith("with"))

    def test_explain_ok(self):
        pg.validate_readonly_sql("EXPLAIN SELECT 1")

    def test_show_ok(self):
        pg.validate_readonly_sql("SHOW search_path")

    def test_rejects_empty(self):
        with self.assertRaises(pg.SqlGuardError):
            pg.validate_readonly_sql("   ")

    def test_rejects_multiple_statements(self):
        with self.assertRaises(pg.SqlGuardError):
            pg.validate_readonly_sql("SELECT 1; SELECT 2")

    def test_rejects_insert(self):
        with self.assertRaises(pg.SqlGuardError):
            pg.validate_readonly_sql("INSERT INTO chunks (id) VALUES ('x')")

    def test_rejects_drop(self):
        with self.assertRaises(pg.SqlGuardError):
            pg.validate_readonly_sql("DROP TABLE chunks")

    def test_rejects_delete(self):
        with self.assertRaises(pg.SqlGuardError):
            pg.validate_readonly_sql("DELETE FROM documents")

    def test_rejects_with_delete(self):
        with self.assertRaises(pg.SqlGuardError):
            pg.validate_readonly_sql(
                "WITH x AS (SELECT id FROM chunks) DELETE FROM chunks WHERE id IN (SELECT id FROM x)"
            )

    def test_strips_comments_before_write(self):
        with self.assertRaises(pg.SqlGuardError):
            pg.validate_readonly_sql("SELECT 1; --\nDELETE FROM chunks")

    def test_comment_only_is_empty(self):
        with self.assertRaises(pg.SqlGuardError):
            pg.validate_readonly_sql("-- nada\n/* tampoco */")

    def test_rejects_select_star_embeddings(self):
        with self.assertRaises(pg.SqlGuardError):
            pg.validate_readonly_sql("SELECT * FROM embeddings")

    def test_rejects_vector_column(self):
        with self.assertRaises(pg.SqlGuardError):
            pg.validate_readonly_sql("SELECT chunk_id, vector FROM embeddings")

    def test_allows_vector_dims(self):
        sql = pg.validate_readonly_sql(
            "SELECT chunk_id, vector_dims(vector) AS dim FROM embeddings LIMIT 3"
        )
        self.assertIn("vector_dims", sql.lower())

    def test_allows_created_at_without_false_create(self):
        pg.validate_readonly_sql("SELECT id, created_at FROM embedding_model")

    def test_allows_literal_with_write_word(self):
        pg.validate_readonly_sql("SELECT 'DROP TABLE chunks' AS warning")

    def test_sanitize_omits_vector_column(self):
        row = pg.sanitize_row({"id": 1, "vector": [0.1] * 64, "model": "nomic"})
        self.assertIn("omitido", row["vector"])
        self.assertEqual(row["model"], "nomic")

    def test_strip_line_comment(self):
        cleaned = pg.strip_sql_comments("SELECT 1 -- comentario\n")
        self.assertEqual(cleaned.strip(), "SELECT 1")


class PostgresQueryTests(unittest.TestCase):
    def test_rewrites_asyncpg_docker_dsn(self):
        dsn = pg.rewrite_dsn(
            "postgresql+asyncpg://postgres:change-me@postgres:5432/agrops"
        )
        self.assertEqual(dsn, "postgresql://postgres:change-me@localhost:5432/agrops")

    def test_rewrites_hostname_postgres_without_sqlalchemy(self):
        dsn = pg.rewrite_dsn("postgresql://u:p@postgres:5432/agrops")
        self.assertEqual(dsn, "postgresql://u:p@localhost:5432/agrops")

    def test_database_dsn_prefers_mcp_url(self):
        old = {
            key: os.environ.get(key)
            for key in ("MCP_DATABASE_URL", "DATABASE_URL")
        }
        try:
            os.environ["MCP_DATABASE_URL"] = (
                "postgresql+psycopg://u:p@postgres:5432/agrops"
            )
            os.environ["DATABASE_URL"] = "postgresql://ignored@db:5432/x"
            self.assertEqual(
                pg.database_dsn(),
                "postgresql://u:p@localhost:5432/agrops",
            )
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_catalog_queries_pass_readonly_guard(self):
        pg.validate_readonly_sql(pg.CORPUS_STATS_SQL)
        pg.validate_readonly_sql(pg.LIST_TABLES_SQL)
        pg.validate_readonly_sql(pg.DESCRIBE_TABLE_SQL)

    def test_corpus_stats_does_not_count_star_on_embeddings(self):
        sql = " ".join(pg.CORPUS_STATS_SQL.lower().split())
        self.assertNotIn("count(*) from embeddings", sql)
        self.assertIn("pg_class", sql)
        self.assertIn("reltuples", sql)


if __name__ == "__main__":
    unittest.main()
