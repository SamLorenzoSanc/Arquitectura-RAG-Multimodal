"""Smoke test de todos los endpoints expuestos en OpenAPI."""

from __future__ import annotations

import json
import sys
import time
import uuid
from typing import Any
from urllib.parse import urljoin

import httpx

BASE = "http://127.0.0.1:8000"
API = f"{BASE}/api/v1"
TIMEOUT = 60.0

# Payloads mínimos por path (sin prefijo /api/v1).
POST_BODIES: dict[str, dict[str, Any]] = {
    "/auth/register": {},  # se rellena en runtime
    "/auth/login": {},
    "/auth/logout": {},
    "/chat/": {
        "message": "Hola, esto es una prueba de smoke test",
        "conversation_id": None,
        "knowledge_base_id": None,
        "model": "llama3.2:latest",
    },
    "/chat/retrieve": {
        "query": "subvenciones plátano",
        "top_k": 3,
    },
    "/chat/simulator/search": {
        "query": "precio plátano",
        "top_k": 3,
    },
    "/chat/simulator/save-dataset": {
        "name": "smoke-dataset",
        "items": [],
    },
    "/chat/simulator/import-question-bank": {
        "items": [],
    },
    "/models/select": {"model": "llama3.2:latest"},
    "/knowledge/": {
        "name": f"KB smoke {uuid.uuid4().hex[:8]}",
        "description": "smoke test",
    },
    "/tenants/": {
        "name": f"Tenant smoke {uuid.uuid4().hex[:8]}",
        "organization_id": None,
    },
    "/tenants/assign": {},
    "/organization": {
        "name": f"Org smoke {uuid.uuid4().hex[:8]}",
        "description": "smoke",
    },
    "/department": {
        "name": f"Dept smoke {uuid.uuid4().hex[:8]}",
        "organization_id": None,
    },
    "/crops/": {
        "name": f"Crop smoke {uuid.uuid4().hex[:8]}",
        "island": "Tenerife",
    },
    "/forecast/prophet": {
        "series": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "periods": 3,
    },
    "/forecast/arimax": {
        "series": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "periods": 3,
    },
    "/forecast/compare": {
        "series": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "periods": 3,
    },
    "/logistics/shipments": {
        "origin": "Santa Cruz",
        "destination": "Las Palmas",
        "product": "plátano",
        "quantity_kg": 100,
    },
}

SKIP_PATH_MARKERS = (
    "/speech/transcribe",  # websocket
    "/evaluation/stream-run",  # SSE largo
    "/evaluation/upload-tests",  # multipart
    "/documents",  # upload multipart — se prueba GET aparte
)


def resolve_path(path: str, ids: dict[str, str]) -> str | None:
    out = path
    for key, value in ids.items():
        token = "{" + key + "}"
        if token in out:
            if not value:
                return None
            out = out.replace(token, value)
    if "{" in out and "}" in out:
        return None
    return out


def main() -> int:
    results: list[dict[str, Any]] = []
    email = f"smoke_{uuid.uuid4().hex[:10]}@example.com"
    password = "SmokeTest123!"
    name = "Smoke Tester"

    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        # Health OpenAPI
        openapi = client.get(f"{BASE}/openapi.json")
        if openapi.status_code != 200:
            print(f"FATAL: no OpenAPI ({openapi.status_code})")
            return 1
        spec = openapi.json()
        paths = spec.get("paths", {})

        # Register + login
        reg = client.post(
            f"{API}/auth/register",
            json={"email": email, "password": password, "name": name},
        )
        results.append(
            {
                "method": "POST",
                "path": "/api/v1/auth/register",
                "status": reg.status_code,
                "ok": reg.status_code in (200, 201),
                "detail": _detail(reg),
            }
        )

        login = client.post(
            f"{API}/auth/login",
            json={"email": email, "password": password},
        )
        token = None
        if login.status_code == 200:
            token = login.json().get("access_token")
        results.append(
            {
                "method": "POST",
                "path": "/api/v1/auth/login",
                "status": login.status_code,
                "ok": login.status_code == 200 and bool(token),
                "detail": _detail(login),
            }
        )
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # IDs dinámicos desde me / knowledge / org
        ids: dict[str, str] = {
            "conversation_id": str(uuid.uuid4()),
            "document_id": str(uuid.uuid4()),
            "test_id": "1",
            "shipment_id": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
            "knowledge_base_id": str(uuid.uuid4()),
            "organization_id": str(uuid.uuid4()),
            "department_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
        }

        me = client.get(f"{API}/auth/me", headers=headers)
        results.append(
            {
                "method": "GET",
                "path": "/api/v1/auth/me",
                "status": me.status_code,
                "ok": me.status_code == 200,
                "detail": _detail(me),
            }
        )
        if me.status_code == 200:
            ids["user_id"] = str(me.json().get("id", ids["user_id"]))

        kb = client.get(f"{API}/knowledge/current", headers=headers)
        results.append(
            {
                "method": "GET",
                "path": "/api/v1/knowledge/current",
                "status": kb.status_code,
                "ok": kb.status_code in (200, 404),
                "detail": _detail(kb),
            }
        )
        if kb.status_code == 200:
            data = kb.json()
            if isinstance(data, dict):
                kid = data.get("id") or data.get("knowledge_base_id")
                if kid:
                    ids["knowledge_base_id"] = str(kid)
                oid = data.get("organization_id")
                if oid:
                    ids["organization_id"] = str(oid)

        orgs = client.get(f"{API}/organization", headers=headers)
        if orgs.status_code == 200:
            data = orgs.json()
            items = data if isinstance(data, list) else data.get("items") or data.get("organizations") or []
            if items and isinstance(items[0], dict) and items[0].get("id"):
                ids["organization_id"] = str(items[0]["id"])

        tenants = client.get(f"{API}/tenants/", headers=headers)
        if tenants.status_code == 200:
            data = tenants.json()
            items = data if isinstance(data, list) else data.get("items") or []
            if items and isinstance(items[0], dict) and items[0].get("id"):
                ids["tenant_id"] = str(items[0]["id"])

        convs = client.get(f"{API}/chat/conversations", headers=headers)
        if convs.status_code == 200:
            data = convs.json()
            items = data if isinstance(data, list) else data.get("items") or data.get("conversations") or []
            if items and isinstance(items[0], dict):
                cid = items[0].get("id") or items[0].get("conversation_id")
                if cid:
                    ids["conversation_id"] = str(cid)

        docs = client.get(f"{API}/documents", headers=headers)
        if docs.status_code == 200:
            data = docs.json()
            items = data if isinstance(data, list) else data.get("items") or data.get("documents") or []
            if items and isinstance(items[0], dict) and items[0].get("id"):
                ids["document_id"] = str(items[0]["id"])

        tests = client.get(f"{API}/chat/evaluation/tests", headers=headers)
        if tests.status_code == 200:
            data = tests.json()
            items = data if isinstance(data, list) else data.get("items") or data.get("tests") or []
            if items:
                first = items[0]
                tid = first.get("id") if isinstance(first, dict) else first
                if tid is not None:
                    ids["test_id"] = str(tid)

        # Rellenar bodies dependientes
        POST_BODIES["/auth/register"] = {
            "email": f"extra_{uuid.uuid4().hex[:8]}@example.com",
            "password": password,
            "name": "Extra",
        }
        POST_BODIES["/auth/login"] = {"email": email, "password": password}
        POST_BODIES["/tenants/"]["organization_id"] = ids.get("organization_id")
        POST_BODIES["/department"]["organization_id"] = ids.get("organization_id")
        POST_BODIES["/tenants/assign"] = {
            "tenant_id": ids.get("tenant_id"),
            "user_id": ids.get("user_id"),
        }
        if ids.get("knowledge_base_id"):
            POST_BODIES["/chat/"]["knowledge_base_id"] = ids["knowledge_base_id"]

        tested: set[tuple[str, str]] = {
            ("post", "/api/v1/auth/register"),
            ("post", "/api/v1/auth/login"),
            ("get", "/api/v1/auth/me"),
            ("get", "/api/v1/knowledge/current"),
        }

        for path, methods in sorted(paths.items()):
            for method, meta in methods.items():
                if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                    continue
                full = path if path.startswith("/api/") else path
                # OpenAPI paths ya incluyen /api/v1
                key = (method.lower(), full)
                if key in tested:
                    continue
                if any(m in full for m in SKIP_PATH_MARKERS) and method.lower() == "post" and "documents" in full:
                    continue
                if "/speech/transcribe" in full:
                    results.append(
                        {
                            "method": method.upper(),
                            "path": full,
                            "status": None,
                            "ok": None,
                            "detail": "SKIP websocket",
                        }
                    )
                    continue
                if "/evaluation/stream-run" in full:
                    results.append(
                        {
                            "method": method.upper(),
                            "path": full,
                            "status": None,
                            "ok": None,
                            "detail": "SKIP SSE largo",
                        }
                    )
                    continue
                if method.lower() == "post" and (
                    "/documents" in full
                    or "/evaluation/upload-tests" in full
                    or full.endswith("/documents/")
                ):
                    results.append(
                        {
                            "method": method.upper(),
                            "path": full,
                            "status": None,
                            "ok": None,
                            "detail": "SKIP multipart upload",
                        }
                    )
                    continue

                # path params
                rel = full
                if rel.startswith("/api/v1"):
                    rel_for_ids = rel[len("/api/v1") :]
                else:
                    rel_for_ids = rel
                resolved = resolve_path(rel_for_ids, ids)
                if resolved is None:
                    results.append(
                        {
                            "method": method.upper(),
                            "path": full,
                            "status": None,
                            "ok": None,
                            "detail": "SKIP missing path params",
                        }
                    )
                    continue

                url = urljoin(BASE + "/", f"api/v1{resolved}".lstrip("/"))
                # Prefer exact openapi path when no params
                if "{" not in full:
                    url = urljoin(BASE + "/", full.lstrip("/"))

                kwargs: dict[str, Any] = {"headers": headers}
                m = method.lower()
                body_key = resolved.split("?")[0]
                # match POST_BODIES without trailing dynamic segments when possible
                body = None
                for k, v in POST_BODIES.items():
                    if body_key == k or body_key.rstrip("/") == k.rstrip("/"):
                        body = v
                        break

                try:
                    if m == "get":
                        resp = client.get(url, **kwargs)
                    elif m == "post":
                        resp = client.post(url, json=body or {}, **kwargs)
                    elif m == "put":
                        resp = client.put(url, json=body or {}, **kwargs)
                    elif m == "patch":
                        resp = client.patch(url, json=body or {}, **kwargs)
                    elif m == "delete":
                        resp = client.delete(url, **kwargs)
                    else:
                        continue
                except Exception as exc:  # noqa: BLE001
                    results.append(
                        {
                            "method": method.upper(),
                            "path": full,
                            "status": None,
                            "ok": False,
                            "detail": f"EXC {exc}",
                        }
                    )
                    continue

                # 401/403/404/422 cuentan como "respondió" pero no necesariamente éxito de negocio
                reachable = resp.status_code < 500
                results.append(
                    {
                        "method": method.upper(),
                        "path": full,
                        "resolved": resolved,
                        "status": resp.status_code,
                        "ok": reachable,
                        "success_2xx": 200 <= resp.status_code < 300,
                        "detail": _detail(resp),
                    }
                )
                tested.add(key)
                time.sleep(0.05)

        # GET documents explícito si no se cubrió
        if ("get", "/api/v1/documents") not in tested and ("get", "/api/v1/documents/") not in tested:
            resp = client.get(f"{API}/documents", headers=headers)
            results.append(
                {
                    "method": "GET",
                    "path": "/api/v1/documents",
                    "status": resp.status_code,
                    "ok": resp.status_code < 500,
                    "success_2xx": 200 <= resp.status_code < 300,
                    "detail": _detail(resp),
                }
            )

    # Resumen
    total = len(results)
    reachable = sum(1 for r in results if r.get("ok") is True)
    success = sum(1 for r in results if r.get("success_2xx") is True)
    skipped = sum(1 for r in results if r.get("ok") is None)
    failed_5xx = [
        r
        for r in results
        if isinstance(r.get("status"), int) and r["status"] >= 500
    ]
    unreachable = [r for r in results if r.get("ok") is False]

    print("=" * 80)
    print(f"BASE: {BASE}")
    print(f"Usuario smoke: {email}")
    print(f"Total pruebas: {total}")
    print(f"Respondieron (<500): {reachable}")
    print(f"Éxito 2xx: {success}")
    print(f"Skip: {skipped}")
    print(f"Errores 5xx: {len(failed_5xx)}")
    print(f"Fallos/exc: {len(unreachable)}")
    print("=" * 80)
    print(f"{'METHOD':<8} {'STATUS':<8} {'OK':<6} {'PATH'}")
    print("-" * 80)
    for r in results:
        status = r.get("status")
        status_s = "-" if status is None else str(status)
        ok = r.get("ok")
        ok_s = "SKIP" if ok is None else ("YES" if ok else "NO")
        print(f"{r['method']:<8} {status_s:<8} {ok_s:<6} {r['path']}")
        if r.get("detail") and (ok is False or (isinstance(status, int) and status >= 400)):
            detail = str(r["detail"]).replace("\n", " ")[:160]
            print(f"         detail: {detail}")

    out_path = "scripts/smoke_test_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "email": email,
                "summary": {
                    "total": total,
                    "reachable": reachable,
                    "success_2xx": success,
                    "skipped": skipped,
                    "failed_5xx": len(failed_5xx),
                },
                "results": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print("=" * 80)
    print(f"Resultados JSON: {out_path}")
    return 0 if not failed_5xx and not unreachable else 2


def _detail(resp: httpx.Response) -> str:
    try:
        data = resp.json()
        if isinstance(data, dict):
            if "detail" in data:
                return str(data["detail"])[:300]
            return json.dumps(data, ensure_ascii=False)[:300]
        return str(data)[:300]
    except Exception:  # noqa: BLE001
        return (resp.text or "")[:300]


if __name__ == "__main__":
    sys.exit(main())
