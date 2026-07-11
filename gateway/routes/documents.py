from fastapi import APIRouter, UploadFile, File

router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)


@router.post("/upload")
async def upload_document(
        file: UploadFile = File(...)
):

    return {
        "filename": file.filename
    }


@router.get("")
async def list_documents():

    return {
        "documents": []
    }


@router.get("/{document_id}")
async def get_document(document_id: str):

    return {
        "document": document_id
    }


@router.delete("/{document_id}")
async def delete_document(document_id: str):

    return {
        "deleted": document_id
    }


@router.post("/reindex")
async def reindex_documents():

    return {
        "status": "reindex started"
    }