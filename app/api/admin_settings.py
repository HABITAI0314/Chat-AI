from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.admin_characters import require_admin
from app.api.schemas import (
    LLMConfigRequest,
    LLMConfigResponse,
    PromptConfigResponse,
    PromptVersionCreateRequest,
    TTSConfigRequest,
    TTSConfigResponse,
)
from app.services.llm_config_service import llm_config_service, tts_config_service
from app.services.prompt_config_service import prompt_config_service
from app.services.prompt_config_service import prompt_config_service

router = APIRouter(
    prefix="/api/admin/settings",
    tags=["admin-settings"],
    dependencies=[Depends(require_admin)],
)


@router.get("/chat-model", response_model=LLMConfigResponse)
async def get_chat_model_config():
    return llm_config_service.public_config()


@router.put("/chat-model", response_model=LLMConfigResponse)
async def save_chat_model_config(payload: LLMConfigRequest):
    try:
        return llm_config_service.save(
            enabled=payload.enabled,
            base_url=payload.base_url,
            model=payload.model,
            api_key=payload.api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/tts", response_model=TTSConfigResponse)
async def get_tts_config():
    return tts_config_service.public_config()


@router.put("/tts", response_model=TTSConfigResponse)
async def save_tts_config(payload: TTSConfigRequest):
    try:
        return tts_config_service.save(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/prompts", response_model=PromptConfigResponse)
async def get_prompt_config(version: int | None = Query(default=None, ge=1)):
    try:
        return prompt_config_service.public_state(version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/prompts/versions", response_model=PromptConfigResponse)
async def create_prompt_version(payload: PromptVersionCreateRequest):
    try:
        return prompt_config_service.create_version(
            payload.name,
            payload.prompts.model_dump(),
            payload.activate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/prompts/versions/{version}/activate", response_model=PromptConfigResponse)
async def activate_prompt_version(version: int):
    try:
        return prompt_config_service.activate(version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/prompts", response_model=PromptConfigResponse)
async def get_prompts(version: int | None = None):
    try:
        return prompt_config_service.public_state(version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/prompts/versions", response_model=PromptConfigResponse)
async def create_prompt_version(payload: PromptVersionCreateRequest):
    try:
        return prompt_config_service.create_version(
            payload.name,
            payload.prompts.model_dump(),
            payload.activate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/prompts/versions/{version}/activate", response_model=PromptConfigResponse)
async def activate_prompt_version(version: int):
    try:
        return prompt_config_service.activate(version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
