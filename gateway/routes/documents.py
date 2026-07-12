from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID, uuid4
from datetime import datetime, timezone
import shutil
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends,
    BackgroundTasks,
    status,
)

from services.document_processor import DocumentProcessor
from fastapi.responses import FileResponse

from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession

from minio import Minio
from minio.error import S3Error

from services.database import get_db

from .auth import get_current_user

from schemas.user import User
from schemas.document import Document, UploadResponse
from schemas.processing_job import ProcessingJob
from schemas.knowledge_base import KnowledgeBase
from services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)

STORAGE_ROOT = Path("storage")
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

async def upload_to_storage(
    file: UploadFile,
    tenant_id: UUID,
    knowledge_base_id: UUID,
) -> str:

    extension = Path(file.filename).suffix

    filename = f"{uuid4()}{extension}"

    folder = (
        STORAGE_ROOT
        / str(tenant_id)
        / str(knowledge_base_id)
    )

    folder.mkdir(parents=True, exist_ok=True)

    filepath = folder / filename

    file.file.seek(0)

    with filepath.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return str(filepath)

async def delete_from_storage(path: str):

    try:

        MINIO_CLIENT.remove_object(
            BUCKET_NAME,
            path,
        )

    except S3Error:

        logger.exception("Cannot delete object")

@router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    knowledge_base_id: UUID = Form(...),
    title: str | None = Form(None),
    description: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = await db.scalar(select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id))

    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")

    if file.filename is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename",
        )

    if file.size == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file",
        )

    file.file.seek(0, 2)

    size = file.file.tell()

    file.file.seek(0)

    try:
        storage_path = await upload_to_storage(
            file=file,
            tenant_id=kb.tenant_id,
            knowledge_base_id=kb.id,
        )

    except Exception as ex:
        logger.exception(ex)

        raise HTTPException(
            status_code=500,
            detail="Cannot upload document",
        )
    
    document = Document(
        id=uuid4(),  # Genera el UUID único en Python
        tenant_id=kb.tenant_id,
        knowledge_base_id=kb.id,
        owner_id=current_user.id,
        filename=file.filename,
        title=title,
        description=description,
        mime_type=file.content_type,
        storage_path=storage_path,
        size=size,
        created_at=datetime.now(timezone.utc) 
    )

    db.add(document)

    await db.flush()
    
    job = ProcessingJob(
        id=uuid4(),
        document_id=document.id, 
        status="PENDING", 
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    

    db.add(job)

    await db.refresh(document)

    processor = DocumentProcessor(db)
    background_tasks.add_task(

        processor.process,

        document.id,
    )

    return UploadResponse(

        id=document.id,
        message="Document uploaded successfully",
    )