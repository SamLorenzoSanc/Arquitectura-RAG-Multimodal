from __future__ import annotations

import pytest

from main import app

pytestmark = pytest.mark.api


def test_dataset_wizard_routes_are_registered():
    contracts = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }
    expected = {
        ("GET", "/api/v1/datasets"),
        ("GET", "/api/v1/datasets/{dataset_id}"),
        ("POST", "/api/v1/datasets/{dataset_id}/rows"),
        ("GET", "/api/v1/datasets/{dataset_id}/traces"),
        ("POST", "/api/v1/datasets/{dataset_id}/traces/import"),
        ("POST", "/api/v1/datasets/{dataset_id}/columns"),
        ("POST", "/api/v1/datasets/{dataset_id}/guardrails"),
        ("PATCH", "/api/v1/datasets/{dataset_id}"),
        ("DELETE", "/api/v1/datasets/{dataset_id}"),
        ("POST", "/api/v1/datasets/preview"),
        ("POST", "/api/v1/datasets/import"),
        ("POST", "/api/v1/datasets/synthetic"),
        ("POST", "/api/v1/datasets/synthetic/preview"),
        ("GET", "/api/v1/datasets/demo-catalog"),
        ("POST", "/api/v1/datasets/demo"),
        ("GET", "/api/v1/datasets/knowledge-bases/{knowledge_base_id}/departments"),
        ("PUT", "/api/v1/datasets/knowledge-bases/{knowledge_base_id}/departments"),
        ("GET", "/api/v1/datasets/departments/{department_id}/knowledge-bases"),
    }
    assert expected <= contracts


def test_preview_requires_auth(client):
    response = client.post(
        "/api/v1/datasets/preview",
        files={"file": ("sample.csv", b"prompt,response\nQ,A\n", "text/csv")},
        data={"limit": "10"},
    )
    assert response.status_code in (401, 403, 422)


def test_list_datasets_filters_by_dataset_department_not_knowledge_base():
    from routes import datasets as datasets_route
    import inspect

    source = inspect.getsource(datasets_route.list_datasets)
    assert "FROM rag_dataset_departments" in source
    assert "FROM department_knowledge_bases" not in source
