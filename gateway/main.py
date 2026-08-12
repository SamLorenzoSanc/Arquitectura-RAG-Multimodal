import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.chat import router as chat_router
from routes.documents import router as document_router
from routes.health import router as health_router
from routes.models import router as model_router
from routes.metrics import router as metrics_router
from routes.auth import router as auth_router
from routes.user import router as user_router
from routes.tenant import router as tenant_router
from routes.knowledge import router as knowledge_router
from routes.organization import router as organization_router
from routes.department import router as department_router
from routes.forecast import router as forecast_router
from routes.logistic import router as logicstic_router
from routes.map import router as map_router
from routes.crops import router as crop_router
from routes.speech import router as speech_router
from routes.recogida import router as recogida_router
import models as models
from middleware.timing import register_logging_middleware

app = FastAPI(title="AgroRAG Gateway", version="1.0.0")
register_logging_middleware(app)

origins = [
    "http://localhost",
    "http://localhost:80",
    "http://localhost:8080",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(document_router, prefix="/api/v1")
app.include_router(model_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(tenant_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")
app.include_router(organization_router, prefix="/api/v1")
app.include_router(department_router, prefix="/api/v1")
app.include_router(forecast_router, prefix="/api/v1")
app.include_router(logicstic_router, prefix="/api/v1")
app.include_router(map_router, prefix="/api/v1")
app.include_router(crop_router, prefix="/api/v1")
app.include_router(speech_router, prefix="/api/v1")
app.include_router(recogida_router, prefix="/api/v1")


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
