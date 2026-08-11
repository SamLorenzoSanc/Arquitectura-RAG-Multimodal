"""Forecast microservice (stub opcional): Prophet/ARIMAX fuera del gateway.

Por defecto reenvía al gateway /api/v1/forecast/* para no duplicar lógica.
Activa profile `optional` en docker-compose.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request

API_INTERNAL_URL = os.getenv("API_INTERNAL_URL", "http://api:8000").rstrip("/")

app = FastAPI(title="AgroPS Forecast Service", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "forecast", "mode": "proxy"}


@app.api_route("/{path:path}", methods=["GET", "POST"])
async def proxy(path: str, request: Request) -> Any:
    target = f"{API_INTERNAL_URL}/api/v1/forecast/{path}"
    body = await request.body()
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.request(
            request.method,
            target,
            content=body,
            headers={
                k: v
                for k, v in request.headers.items()
                if k.lower() not in {"host", "content-length"}
            },
            params=request.query_params,
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
