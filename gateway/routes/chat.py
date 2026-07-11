from fastapi import APIRouter
from schemas.chat import ChatRequest, ChatResponse, ContextChunk
from services import rag_service

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):

    print("Entrando al endpoint")
    result = rag_service.answer(
        request.question,
        request.history,
    )

    print("He salido del RAG")
    
    return ChatResponse(
        answer=result.answer,
        context=[
            ContextChunk(
                page_content=c.page_content,
                metadata=c.metadata,
            )
            for c in result.context
        ]
    )

@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):

    return {
        "conversation_id": conversation_id
    }


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):

    return {
        "deleted": conversation_id
    }