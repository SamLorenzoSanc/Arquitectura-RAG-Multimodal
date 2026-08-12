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
        "tenant_id": VALID_UUID
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
        "knowledge_base_id": VALID_UUID
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
                "reranking": False
            }
        }
        response = authenticated_client.post(CHAT_ROUTE, json=payload)

    # Limpiamos el override para no afectar a otros tests
    authenticated_client.app.dependency_overrides.clear()

    assert response.status_code in (200, 201), f"Falló con {response.status_code}: {response.text}"

def test_upload_document_is_not_available(authenticated_client):
    response = authenticated_client.post(
        UPLOAD_ROUTE,
        files={"file": ("test.txt", b"Contenido", "text/plain")},
        data={"knowledge_base_id": VALID_UUID},
    )
    assert response.status_code == 405