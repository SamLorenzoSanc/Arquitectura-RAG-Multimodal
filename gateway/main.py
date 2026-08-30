import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rag.composition import build_rag_container as compose_rag_hexagon
from composition import build_app_container
from chat.http import lab_router as chat_lab_router
from chat.http import router as chat_router
from catalog.http import lab_router as document_lab_router
from catalog.http import router as document_router
from ops.http import health_router
from identity.http import router as auth_router
from tenancy.http import knowledge_router
from tenancy.http import organization_router
from tenancy.http import department_router
from identity.http import account_router
from identity.http import user_router
from evaluation.http import lab_router as evaluation_router
from evaluation.http import datasets_router
from evaluation.http import hitl_router as human_validation_router
import models as models
from middleware.timing import register_logging_middleware
from services.inference_warmup import schedule_warmup
from services.embedding_indexer import schedule_indexer


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inferencia automática: calienta embed + LLM al arrancar (no bloquea /health).
    app.state.warmup_task = schedule_warmup()
    app.state.indexer_task = schedule_indexer()
    yield
    for name in ("warmup_task", "indexer_task"):
        task = getattr(app.state, name, None)
        if task is not None and not task.done():
            task.cancel()


app = FastAPI(title="AgroPS Gateway", version="1.0.0", lifespan=lifespan)
app.state.compose_rag = compose_rag_hexagon
app.state.container = build_app_container()
register_logging_middleware(app)

origins = [
    "http://localhost",
    "http://localhost:80",
    "http://localhost:8080",
    "http://localhost:5173",
    *[
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "").split(",")
        if origin.strip()
    ],
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth, salud, corpus, chat agéntico y tenancy (organización / departamentos / miembros).
app.include_router(auth_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")
app.include_router(document_router, prefix="/api/v1")
app.include_router(document_lab_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(chat_lab_router, prefix="/api/v1")
app.include_router(evaluation_router, prefix="/api/v1")
app.include_router(datasets_router, prefix="/api/v1")
app.include_router(human_validation_router, prefix="/api/v1")
app.include_router(organization_router, prefix="/api/v1")
app.include_router(department_router, prefix="/api/v1")
app.include_router(account_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
