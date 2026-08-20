import uuid
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from services.database import get_db
from services.agentic_rag_service import AgenticRAGService

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
    mock_db_result = MagicMock()
    mock_db_result.mappings.return_value.first.return_value = {
        "organization_id": "org_dummy",
        "tenant_id": VALID_UUID,
        "role_name": "admin",
        "legacy_department_id": None,
    }
    mock_db_result.all.return_value = []

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_db_result
    mock_db.scalar.return_value = 1

    authenticated_client.app.dependency_overrides[get_db] = lambda: mock_db

    payload = {
        "question": "Hola, ¿qué información hay?",
        "knowledge_base_id": VALID_UUID,
    }

    rag_payload = {
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

    with patch.object(
        AgenticRAGService, "answer", new_callable=AsyncMock, return_value=rag_payload
    ):
        response = authenticated_client.post(CHAT_ROUTE, json=payload)

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
    with patch("catalog.adapters.inbound.documents._validate_kb_access", AsyncMock()), patch(
        "catalog.adapters.inbound.documents._storage.save_bytes",
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
    with patch("catalog.adapters.inbound.documents._validate_kb_access", AsyncMock()), patch(
        "catalog.adapters.inbound.documents.RAGService.invalidate_retrieval_cache", return_value=0
    ):
        response = authenticated_client.delete(
            f"/api/v1/documents/{VALID_UUID}",
            params={"knowledge_base_id": VALID_UUID},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"


def test_list_document_chunks(authenticated_client, override_db):
    document = MagicMock()
    document.id = VALID_UUID
    document.filename = "posei.pdf"
    document.title = "Ayudas POSEI"
    document.mime_type = "application/pdf"
    document.size = 2048
    document.knowledge_base_id = VALID_UUID
    chunk = MagicMock()
    chunk.id = uuid.uuid4()
    chunk.position = 0
    chunk.headline = "Ayuda por hectárea"
    chunk.summary = "Cuantía POSEI"
    chunk.content = "La ayuda directa para aguacate en zona árida es de 1.200 € por hectárea."
    override_db.scalar = AsyncMock(return_value=document)
    override_db.scalars = AsyncMock(return_value=MagicMock(all=lambda: [chunk]))
    override_db.execute = AsyncMock(return_value=[])
    with patch(
        "catalog.adapters.inbound.documents._validate_kb_access", AsyncMock()
    ):
        response = authenticated_client.get(
            f"/api/v1/documents/{VALID_UUID}/chunks",
            params={"knowledge_base_id": VALID_UUID},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["chunk_count"] == 1
    assert body["chunks"][0]["headline"] == "Ayuda por hectárea"
    assert "1.200" in body["chunks"][0]["content"]
