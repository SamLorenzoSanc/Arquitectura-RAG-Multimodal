from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from models.base import Base
from models.document import Document
from models.processing_job import ProcessingJob

from services.ingest_service import IngestService
from services.document_processor import DocumentProcessor

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from main import app
from routes.auth import get_current_user
from services.database import get_db


DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def engine():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine):
    Session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with Session() as session:
        yield session


@pytest.fixture
async def document(session):
    doc = Document(
        id=uuid4(),
        filename="manual.pdf",
        storage_path="tests/fixtures/sample1.pdf",
        tenant_id=uuid4(),
        knowledge_base_id=uuid4(),
        owner_id=uuid4(),
    )

    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc


@pytest.fixture
async def processing_job(session, document):
    job = ProcessingJob(
        id=uuid4(),
        document_id=document.id,
        status="PENDING",
    )

    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


@pytest.fixture
def ingest_service(session):
    return IngestService(session)


@pytest.fixture
def document_processor(session):
    return DocumentProcessor(session)

@pytest.fixture
def override_db():
    """Mock del generador de sesiones de base de datos."""
    mock_session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_session
    yield mock_session
    app.dependency_overrides.clear()

@pytest.fixture
def client(override_db):
    """Cliente HTTP síncrono para testear la app de FastAPI."""
    return TestClient(app)

@pytest.fixture
def authenticated_client(client):
    """Cliente con usuario autenticado inyectado vía dependency override."""
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_user.tenant_id = "tenant-456"
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield client
    # Se limpia la dependencia al terminar
    app.dependency_overrides.pop(get_current_user, None)