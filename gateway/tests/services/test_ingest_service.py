import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.document_processor import DocumentProcessor
from services.ingest_service import IngestService, Result

@pytest.fixture
def db_session(document):
    session = MagicMock()
    session.scalar = AsyncMock(return_value=document)
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session

@pytest.fixture
def document():
    doc = MagicMock()
    doc.id = "123"
    doc.tenant_id = "tenant_1"
    doc.owner_id = "owner_1"
    return doc

@pytest.fixture
def processing_job():
    job = MagicMock()
    job.status = "PENDING"
    job.chunks_generated = 0
    return job

@pytest.fixture
def service():
    with patch("services.ingest_service.OpenAI"):
        return IngestService(None)


@pytest.mark.asyncio
async def test_process_success(db_session, document, processing_job):
    with patch("services.document_processor.IngestService") as ingest:
        ingest.return_value.process = AsyncMock(return_value=15)
        processor = DocumentProcessor(db_session)
        chunks = await processor.process(document.id)

        assert chunks == 15
        await db_session.refresh(processing_job)

def test_build_context(service, document):
    context = service.build_context(document)
    assert context.tenant_id == document.tenant_id
    assert context.member_id == document.owner_id
    assert context.language == "es"

def test_prompt_contains_document(service):
    document = {
        "type": "pdf",
        "source": "manual.pdf",
        "text": "Hola mundo"
    }
    prompt = service.make_prompt(document)
    assert "manual.pdf" in prompt
    assert "Hola mundo" in prompt

def test_make_messages(service):
    messages = service.make_messages({
        "type": "pdf",
        "source": "doc",
        "text": "hola"
    })
    assert len(messages) == 1
    assert messages[0]["role"] == "user"

def test_create_chunks(service):
    document = {
        "type": "document",
        "source": "manual.pdf",
        "document_id": "1",
        "tenant_id": "1",
        "knowledge_base_id": "1",
        "text": "Texto de prueba"
    }

    with patch.object(service, "process_document") as mock:
        mock.return_value = [Result(page_content="hola", metadata={})]
        chunks = service.create_chunks(document)
        assert len(chunks) == 1