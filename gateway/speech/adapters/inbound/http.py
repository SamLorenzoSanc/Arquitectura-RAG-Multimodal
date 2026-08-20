from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from speech.application import RAGService, SpeechService

router = APIRouter(prefix="/speech", tags=["Speech"])

speech = SpeechService()
rag = RAGService()


@router.websocket("/transcribe")
async def live(
    websocket: WebSocket,
    tenant_id: str = Query(...),
    knowledge_base_id: str = Query(...),
):
    await websocket.accept()
    session = speech.create_session()
    try:
        while True:
            audio = await websocket.receive_bytes()
            session.add_audio(audio)
            event = await session.process()
            if event is None:
                continue
            if event["type"] == "partial":
                await websocket.send_json(event)
                continue
            if event["type"] == "final":
                await websocket.send_json(event)
                await websocket.send_json({"type": "thinking"})
                answer = await rag.answer(
                    question=event["text"],
                    history=[],
                    tenant_id=tenant_id,
                    collections=[knowledge_base_id],
                )
                await websocket.send_json(
                    {
                        "type": "assistant",
                        "text": answer["answer"],
                        "chunks": answer["chunks"],
                    }
                )
    except WebSocketDisconnect:
        session.reset()
