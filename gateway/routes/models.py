import os
import httpx

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/models", tags=["Models"])

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


class ModelSelection(BaseModel):
    model: str


async def _fetch_available_models() -> list[str]:
    """Modelos realmente instalados en Ollama."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{OLLAMA_URL}/api/tags")
        resp.raise_for_status()
        data = resp.json()

    return [m["name"] for m in data.get("models", [])]


@router.get("")
async def list_models():
    try:
        models = await _fetch_available_models()
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="No se pudo consultar Ollama")
    return {"models": models}


@router.post("/select")
async def select_model(selection: ModelSelection):
    try:
        available = await _fetch_available_models()
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="No se pudo consultar Ollama")

    if selection.model not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Modelo no disponible. Opciones: {available}",
        )
    return {"selected": selection.model}