import uvicorn
from fastapi import FastAPI
from routes.chat import router as chat_router
from routes.documents import router as document_router
from routes.health import router as health_router
from routes.models import router as model_router
from routes.metrics import router as metrics_router
from routes.auth import router as auth_router

app = FastAPI(
    title="AgroRAG Gateway",
    version="1.0.0"
)

app.include_router(chat_router, prefix="/api/v1")
app.include_router(document_router, prefix="/api/v1")
app.include_router(model_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")

def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
