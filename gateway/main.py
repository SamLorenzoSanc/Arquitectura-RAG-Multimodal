import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rag.composition import build_rag_container as compose_rag_hexagon
from composition import build_app_container
from routes.chat import lab_router as chat_lab_router
from routes.chat import router as chat_router
from routes.documents import lab_router as document_lab_router
from routes.documents import router as document_router
from routes.health import router as health_router
from routes.auth import router as auth_router
from routes.knowledge import router as knowledge_router
from routes.organization import router as organization_router
from routes.department import router as department_router
from routes.account import router as account_router
from routes.user import router as user_router
from routes.evaluation_ext import router as evaluation_router
from routes.datasets import router as datasets_router
from routes.human_validation import router as human_validation_router
import models as models
from middleware.timing import register_logging_middleware

app = FastAPI(title="AgroPS Gateway", version="1.0.0")
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
