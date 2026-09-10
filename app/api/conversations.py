from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import (
    ChatResponse,
    ConversationCreateRequest,
    ConversationResponse,
    HistoryResponse,
    MemoryResponse,
    TransferRequest,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse)
async def open_conversation(payload: ConversationCreateRequest, request: Request):
    try:
        return await request.app.state.chat_service.open_conversation(
            payload.user_id, payload.character_id
        )
    except ValueError as exc:
        if str(exc) in {"character_not_found", "conversation_not_found"}:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{conversation_id}/messages", response_model=HistoryResponse)
async def get_messages(conversation_id: int, user_id: str, request: Request):
    try:
        return await request.app.state.chat_service.history(conversation_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{conversation_id}/transfers", response_model=ChatResponse)
async def send_transfer(
    conversation_id: int, payload: TransferRequest, request: Request
):
    try:
        return await request.app.state.chat_service.send_transfer(conversation_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{conversation_id}/messages", response_model=ConversationResponse)
async def reset_conversation(conversation_id: int, user_id: str, request: Request):
    try:
        return await request.app.state.chat_service.reset_conversation(
            conversation_id, user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{conversation_id}/memories", response_model=list[MemoryResponse])
async def get_memories(conversation_id: int, user_id: str, request: Request):
    try:
        return await request.app.state.chat_service.memories(conversation_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{conversation_id}/memories/{memory_id}", status_code=204)
async def delete_memory(
    conversation_id: int, memory_id: int, user_id: str, request: Request
):
    try:
        await request.app.state.chat_service.delete_memory(
            conversation_id, memory_id, user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
