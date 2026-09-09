from secrets import compare_digest

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.api.schemas import (
    AdminCharacterDetail,
    AdminCharacterSummary,
    AdminPreviewRequest,
    AdminPreviewResponse,
    CharacterActiveRequest,
    CharacterCreateRequest,
    CharacterDraftRequest,
    CharacterValidationResponse,
)
from app.config import settings
from app.services.character_admin_service import (
    CharacterAdminService,
    CharacterProfileValidationError,
)


async def require_admin(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> None:
    if settings.app_env.lower() == "dev" and not settings.admin_token:
        return
    if settings.admin_token and x_admin_token and compare_digest(
        x_admin_token, settings.admin_token
    ):
        return
    raise HTTPException(status_code=401, detail="admin_unauthorized")


router = APIRouter(
    prefix="/api/admin/characters",
    tags=["admin-characters"],
    dependencies=[Depends(require_admin)],
)


def _handle_error(exc: ValueError) -> HTTPException:
    if isinstance(exc, CharacterProfileValidationError):
        return HTTPException(
            status_code=422,
            detail={"code": "character_profile_invalid", "issues": exc.issues},
        )
    message = str(exc)
    if message == "character_not_found":
        return HTTPException(status_code=404, detail=message)
    if message == "character_code_exists":
        return HTTPException(status_code=409, detail=message)
    if message == "avatar_path_invalid":
        return HTTPException(status_code=422, detail=message)
    return HTTPException(status_code=400, detail=message)


def _service(request: Request) -> CharacterAdminService:
    return request.app.state.character_admin_service


@router.get("", response_model=list[AdminCharacterSummary])
async def list_characters(request: Request):
    return await _service(request).list_characters()


@router.post("", response_model=AdminCharacterDetail)
async def create_character(payload: CharacterCreateRequest, request: Request):
    try:
        return await _service(request).create(payload)
    except ValueError as exc:
        raise _handle_error(exc) from exc


@router.get("/{character_id}", response_model=AdminCharacterDetail)
async def get_character(character_id: int, request: Request):
    try:
        return await _service(request).get_detail(character_id)
    except ValueError as exc:
        raise _handle_error(exc) from exc


@router.put("/{character_id}/draft", response_model=AdminCharacterDetail)
async def save_draft(
    character_id: int, payload: CharacterDraftRequest, request: Request
):
    try:
        return await _service(request).save_draft(character_id, payload)
    except ValueError as exc:
        raise _handle_error(exc) from exc


@router.post("/{character_id}/validate", response_model=CharacterValidationResponse)
async def validate_character(
    character_id: int, payload: CharacterDraftRequest, request: Request
):
    try:
        detail = await _service(request).get_detail(character_id)
        issues = await _service(request).validate(payload.profile or detail.profile)
        return CharacterValidationResponse(
            valid=not any(item.level == "error" for item in issues),
            issues=issues,
        )
    except ValueError as exc:
        raise _handle_error(exc) from exc


@router.post("/{character_id}/publish", response_model=AdminCharacterDetail)
async def publish_character(character_id: int, request: Request):
    try:
        return await _service(request).publish(character_id)
    except ValueError as exc:
        raise _handle_error(exc) from exc


@router.patch("/{character_id}/active", response_model=AdminCharacterDetail)
async def set_character_active(
    character_id: int, payload: CharacterActiveRequest, request: Request
):
    try:
        return await _service(request).set_active(character_id, payload.is_active)
    except ValueError as exc:
        raise _handle_error(exc) from exc


@router.post("/{character_id}/duplicate", response_model=AdminCharacterDetail)
async def duplicate_character(character_id: int, request: Request):
    try:
        return await _service(request).duplicate(character_id)
    except ValueError as exc:
        raise _handle_error(exc) from exc


@router.post("/{character_id}/preview", response_model=AdminPreviewResponse)
async def preview_character(
    character_id: int, payload: AdminPreviewRequest, request: Request
):
    try:
        detail = await _service(request).get_detail(character_id)
        issues = await _service(request).validate(payload.profile or detail.profile)
        if any(item.level == "error" for item in issues):
            raise CharacterProfileValidationError([item.model_dump() for item in issues])
        return await request.app.state.chat_service.preview(character_id, payload)
    except ValueError as exc:
        raise _handle_error(exc) from exc
