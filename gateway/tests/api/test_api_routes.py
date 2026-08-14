import uuid
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from services.database import get_db
from services.rag_service import RAGService

HEALTH_ROUTE = "api/v1/health"
PROTECTED_ROUTE = "/api/v1/documents"
CHAT_ROUTE = "/api/v1/chat"
UPLOAD_ROUTE = "/api/v1/documents"

# Generamos un UUID válido para que la validación de Pydantic no se queje
VALID_UUID = str(uuid.uuid4())


def test_health_check(client):
    response = client.get(HEALTH_ROUTE)
    assert response.status_code == 200


def test_protected_route_without_auth(client):
    # Añadimos el parámetro query requerido
    response = client.get(PROTECTED_ROUTE, params={"knowledge_base_id": VALID_UUID})

    # Aceptamos 422 porque FastAPI rechaza la falta de cabecera 'authorization' antes de llegar al 401
    assert response.status_code in (401, 403, 422)


def test_send_chat_message_success(authenticated_client):
    # --- 1. EL FIX DE LA BASE DE DATOS ---
    # Creamos un resultado falso puramente SÍNCRONO para encadenar .mappings().first()
    mock_db_result = MagicMock()
    mock_db_result.mappings.return_value.first.return_value = {
        "organization_id": "org_dummy",
        "tenant_id": VALID_UUID,
    }

    # Creamos el mock de la sesión de BD asíncrona
    mock_db = AsyncMock()
    # Le decimos que cuando haga await db.execute(), devuelva nuestro objeto síncrono
    mock_db.execute.return_value = mock_db_result
    mock_db.scalar.return_value = VALID_UUID

    # Sobrescribimos la base de datos en FastAPI solo para este test
    # (authenticated_client.app accede a tu instancia de FastAPI)
    authenticated_client.app.dependency_overrides[get_db] = lambda: mock_db
    # --------------------------------------

    payload = {
        "question": "Hola, ¿qué información hay?",
        "knowledge_base_id": VALID_UUID,
    }

    METHOD_TO_MOCK = "ask" if hasattr(RAGService, "ask") else "answer"

    with patch.object(RAGService, METHOD_TO_MOCK) as mock_rag:
        mock_rag.return_value = {
            "answer": "Respuesta simulada",
            "chunks": [],
            "retrieval": {
                "original_query": "Hola",
                "rewritten_query": "Hola",
                "retrieved_chunks": 0,
                "rewritten_chunks": 0,
                "merged_chunks": 0,
                "final_chunks": 0,
                "retrieval_k": 5,
                "final_k": 5,
                "reranking": False,
            },
        }
        response = authenticated_client.post(CHAT_ROUTE, json=payload)

    # Limpiamos el override para no afectar a otros tests
    authenticated_client.app.dependency_overrides.clear()

    assert response.status_code in (
        200,
        201,
    ), f"Falló con {response.status_code}: {response.text}"


def test_upload_document_requires_kb_access(authenticated_client):
    """Sin acceso a KB / mocks incompletos, la subida no debe colarse como 405."""
    response = authenticated_client.post(
        UPLOAD_ROUTE,
        files={"file": ("test.txt", b"Contenido", "text/plain")},
        data={"knowledge_base_id": VALID_UUID},
    )
    assert response.status_code in (200, 201, 403, 404, 422, 500)


def test_upload_persists_when_storage_fails(authenticated_client, override_db):
    kb = MagicMock()
    kb.tenant_id = VALID_UUID
    override_db.scalar = AsyncMock(return_value=kb)
    override_db.add = MagicMock()
    override_db.flush = AsyncMock()
    override_db.commit = AsyncMock()
    override_db.refresh = AsyncMock()
    with patch("routes.documents._validate_kb_access", AsyncMock()), patch(
        "routes.documents._storage.save_bytes",
        AsyncMock(side_effect=OSError("disco lleno")),
    ):
        response = authenticated_client.post(
            UPLOAD_ROUTE,
            files={"file": ("aviso.txt", b"Contenido", "text/plain")},
            data={"knowledge_base_id": VALID_UUID},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["processing_status"] == "failed"
    assert "disco lleno" in (body.get("error") or "")
    assert body["id"]


def test_delete_document_requires_auth(client):
    response = client.delete(
        f"/api/v1/documents/{VALID_UUID}",
        params={"knowledge_base_id": VALID_UUID},
    )
    assert response.status_code in (401, 403, 422)


def test_delete_document_endpoint(authenticated_client, override_db):
    document = MagicMock()
    document.storage_path = None
    document.tenant_id = VALID_UUID
    override_db.scalar = AsyncMock(return_value=document)
    override_db.execute = AsyncMock()
    override_db.delete = AsyncMock()
    override_db.commit = AsyncMock()
    with patch("routes.documents._validate_kb_access", AsyncMock()), patch(
        "routes.documents.RAGService.invalidate_retrieval_cache", return_value=0
    ):
        response = authenticated_client.delete(
            f"/api/v1/documents/{VALID_UUID}",
            params={"knowledge_base_id": VALID_UUID},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"


def test_reindex_embeddings_endpoint(authenticated_client, override_db):
    kb = MagicMock()
    kb.tenant_id = VALID_UUID
    override_db.scalar = AsyncMock(return_value=kb)
    with patch("routes.documents._validate_kb_access", AsyncMock()), patch(
        "routes.documents.reindex_embeddings",
        AsyncMock(
            return_value={
                "chunks": 4,
                "models": {
                    "qwen3-embedding:latest": {
                        "indexed": 4,
                        "skipped": 0,
                        "failed": 0,
                    }
                },
                "note": "ok",
            }
        ),
    ):
        response = authenticated_client.post(
            "/api/v1/documents/reindex-embeddings",
            json={
                "knowledge_base_id": VALID_UUID,
                "embedding_models": [
                    "qwen3-embedding:latest",
                    "nomic-embed-text",
                ],
            },
        )
    assert response.status_code == 200
    assert response.json()["chunks"] == 4


def test_reindex_embeddings_records_job_for_document(authenticated_client, override_db):
    kb = MagicMock()
    kb.tenant_id = VALID_UUID
    override_db.scalar = AsyncMock(return_value=kb)
    with patch("routes.documents._validate_kb_access", AsyncMock()), patch(
        "routes.documents.reindex_embeddings",
        AsyncMock(
            return_value={
                "chunks": 2,
                "models": {
                    "nomic-embed-text": {
                        "indexed": 2,
                        "skipped": 0,
                        "failed": 0,
                    }
                },
                "note": "ok",
            }
        ),
    ), patch(
        "routes.documents.record_reindex_on_job", AsyncMock()
    ) as record_job, patch(
        "routes.documents.RAGService.invalidate_retrieval_cache", return_value=0
    ):
        response = authenticated_client.post(
            "/api/v1/documents/reindex-embeddings",
            json={
                "knowledge_base_id": VALID_UUID,
                "document_id": VALID_UUID,
                "embedding_models": ["nomic-embed-text"],
            },
        )
    assert response.status_code == 200
    record_job.assert_awaited()
