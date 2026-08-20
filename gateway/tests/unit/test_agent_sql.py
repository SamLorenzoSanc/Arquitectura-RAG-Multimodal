import pytest

from services.agent_sql import AgentSqlError, validate_agent_select

pytestmark = pytest.mark.unit


def test_validate_agent_select_accepts_tenant_scoped_documents():
    sql = validate_agent_select(
        "SELECT filename, title FROM documents WHERE tenant_id = :tenant_id"
    )
    assert sql.upper().endswith("LIMIT 25")
    assert ":tenant_id" in sql


def test_validate_agent_select_rejects_writes_and_foreign_tables():
    with pytest.raises(AgentSqlError):
        validate_agent_select("DELETE FROM documents WHERE tenant_id = :tenant_id")
    with pytest.raises(AgentSqlError):
        validate_agent_select("SELECT email FROM users")
    with pytest.raises(AgentSqlError):
        validate_agent_select(
            "SELECT filename FROM documents WHERE tenant_id = :tenant_id; DROP TABLE documents"
        )


def test_validate_agent_select_requires_join_for_chunks_and_messages():
    with pytest.raises(AgentSqlError):
        validate_agent_select("SELECT content FROM chunks LIMIT 5")
    with pytest.raises(AgentSqlError):
        validate_agent_select("SELECT content FROM messages LIMIT 5")
    ok = validate_agent_select(
        "SELECT c.content FROM chunks c "
        "JOIN documents d ON d.id = c.document_id "
        "WHERE d.tenant_id = :tenant_id LIMIT 100"
    )
    assert "LIMIT 50" in ok


def test_validate_agent_select_allows_created_at_and_notebook():
    sql = validate_agent_select(
        "SELECT title, created_at FROM conversations "
        "WHERE tenant_id = :tenant_id AND user_id = :user_id"
    )
    assert "created_at" in sql
    notebook = validate_agent_select(
        "SELECT entry_date, title, category, LEFT(body, 180) AS body "
        "FROM field_notebook_entries "
        "WHERE user_id = :user_id OR organization_id = :organization_id "
        "ORDER BY entry_date DESC LIMIT 15"
    )
    assert "LIMIT 15" in notebook


def test_validate_agent_select_rejects_set_and_catalog():
    with pytest.raises(AgentSqlError):
        validate_agent_select(
            "SELECT filename FROM documents WHERE tenant_id = :tenant_id "
            "UNION SELECT current_user"
        )
    with pytest.raises(AgentSqlError):
        validate_agent_select("SELECT * FROM information_schema.tables")
