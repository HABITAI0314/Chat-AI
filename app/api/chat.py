from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/conversations", tags=["chat"])


@router.post("/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(conversation_id: int, payload: ChatRequest, request: Request):
    try:
        return await request.app.state.chat_service.send_message(
            conversation_id, payload.user_id, payload.content
        )
    except ValueError as exc:
        status = 422 if str(exc) == "message_empty" else 404
        raise HTTPException(status_code=status, detail=str(exc)) from exc
