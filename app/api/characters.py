from fastapi import APIRouter, Request

from app.api.schemas import CharacterSummary

router = APIRouter(prefix="/api/characters", tags=["characters"])


@router.get("", response_model=list[CharacterSummary])
async def list_characters(request: Request):
    return await request.app.state.chat_service.list_characters()
