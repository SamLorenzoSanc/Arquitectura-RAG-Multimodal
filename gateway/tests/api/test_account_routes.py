from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from identity.http import get_current_user
from main import app


def test_account_tokens_require_auth(client):
    response = client.get("/api/v1/account/tokens")
    assert response.status_code in (401, 403, 422)


def test_create_account_token(authenticated_client, override_db):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "ana@agrops.test"
    user.name = "Ana"
    app.dependency_overrides[get_current_user] = lambda: user
    override_db.execute = AsyncMock()
    override_db.commit = AsyncMock()
    response = authenticated_client.post(
        "/api/v1/account/tokens",
        json={"name": "CLI", "kind": "access", "expires_days": 7},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["token"]
    assert body["kind"] == "access"
    app.dependency_overrides.pop(get_current_user, None)


def _empty_query():
    result = MagicMock()
    result.mappings.return_value.first.return_value = None
    result.mappings.return_value.all.return_value = []
    return result


def test_update_profile(authenticated_client, override_db):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "ana@agrops.test"
    user.name = "Ana"
    app.dependency_overrides[get_current_user] = lambda: user
    override_db.execute = AsyncMock(return_value=_empty_query())
    override_db.commit = AsyncMock()
    override_db.scalar = AsyncMock(return_value=user)
    response = authenticated_client.patch(
        "/api/v1/account/profile",
        json={"name": "Ana Pérez"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Ana Pérez"
    app.dependency_overrides.pop(get_current_user, None)


def test_update_profile_details(authenticated_client, override_db):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "ana@agrops.test"
    user.name = "Ana"
    app.dependency_overrides[get_current_user] = lambda: user
    row = {
        "job_title": "Agricultora",
        "phone": "+34600111222",
        "island": "La Palma",
        "municipality": "Los Llanos",
        "bio": "Plátano de exportación",
        "crop_focus": "Plátano",
        "preferred_language": "es",
        "notify_email": True,
        "notify_whatsapp": True,
        "avatar_path": None,
        "updated_at": None,
    }
    result = MagicMock()
    result.mappings.return_value.first.return_value = row
    override_db.execute = AsyncMock(return_value=result)
    override_db.commit = AsyncMock()
    override_db.scalar = AsyncMock(return_value=user)
    response = authenticated_client.patch(
        "/api/v1/account/profile",
        json={
            "name": "Ana Pérez",
            "job_title": "Agricultora",
            "island": "La Palma",
            "crop_focus": "Plátano",
            "notify_whatsapp": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["job_title"] == "Agricultora"
    assert body["island"] == "La Palma"
    app.dependency_overrides.pop(get_current_user, None)


def test_get_profile(authenticated_client, override_db):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "ana@agrops.test"
    user.name = "Ana"
    app.dependency_overrides[get_current_user] = lambda: user
    override_db.execute = AsyncMock(return_value=_empty_query())
    override_db.commit = AsyncMock()
    response = authenticated_client.get("/api/v1/account/profile")
    assert response.status_code == 200
    assert response.json()["email"] == "ana@agrops.test"
    assert response.json()["has_avatar"] is False
    app.dependency_overrides.pop(get_current_user, None)


def test_avatar_rejects_empty_file(authenticated_client, override_db):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "ana@agrops.test"
    user.name = "Ana"
    app.dependency_overrides[get_current_user] = lambda: user
    override_db.execute = AsyncMock(return_value=_empty_query())
    override_db.commit = AsyncMock()
    response = authenticated_client.post(
        "/api/v1/account/profile/avatar",
        files={"file": ("foto.jpg", b"", "image/jpeg")},
    )
    assert response.status_code == 400
    app.dependency_overrides.pop(get_current_user, None)


def test_create_support_ticket(authenticated_client, override_db):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "ana@agrops.test"
    app.dependency_overrides[get_current_user] = lambda: user
    override_db.execute = AsyncMock()
    override_db.commit = AsyncMock()
    with patch(
        "identity.postgres.PostgresIdentityRepository.ensure_tables",
        AsyncMock(),
    ):
        response = authenticated_client.post(
            "/api/v1/account/support",
            json={
                "subject": "No sube el PDF",
                "message": "Al subir el manual de plátano aparece un error.",
            },
        )
    assert response.status_code == 200
    assert response.json()["status"] == "open"
    app.dependency_overrides.pop(get_current_user, None)


def test_account_usage(authenticated_client, override_db):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "ana@agrops.test"
    app.dependency_overrides[get_current_user] = lambda: user
    override_db.scalar = AsyncMock(return_value=3)
    override_db.execute = AsyncMock()
    override_db.commit = AsyncMock()
    response = authenticated_client.get("/api/v1/account/usage")
    assert response.status_code == 200
    body = response.json()
    assert "documents" in body
    assert "conversations" in body
    app.dependency_overrides.pop(get_current_user, None)


def test_account_analytics(authenticated_client, override_db):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "ana@agrops.test"
    user.name = "Ana"
    app.dependency_overrides[get_current_user] = lambda: user
    override_db.scalar = AsyncMock(return_value=2)
    override_db.execute = AsyncMock(return_value=_empty_query())
    override_db.commit = AsyncMock()
    response = authenticated_client.get("/api/v1/account/analytics")
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == str(user.id)
    assert "totals" in body
    assert "documents" in body["totals"]
    assert "timeline" in body
    app.dependency_overrides.pop(get_current_user, None)
