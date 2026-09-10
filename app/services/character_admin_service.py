import json
from pathlib import PurePosixPath
from typing import Any

from app.api.schemas import (
    AdminCharacterDetail,
    AdminCharacterSummary,
    CharacterCreateRequest,
    CharacterDraftRequest,
    ValidationIssue,
)
from app.db.models import Character
from app.db.repositories import Repository

ALLOWED_EMOTIONS = {"calm", "happy", "shy", "curious", "annoyed", "sad", "guarded"}
ALLOWED_SCENES = {"first_meet", "familiar", "daily", "plot"}
ALLOWED_PHOTO_OUTCOMES = {"send", "delay", "decline"}
ALLOWED_VOICE_MODES = {"never", "on_request", "occasional", "emotional"}
ALLOWED_DISPLAY_MODES = {"text_and_audio", "audio_only"}
ALLOWED_TRANSFER_MODES = {"accept", "return", "conditional"}


class CharacterProfileValidationError(ValueError):
    def __init__(self, issues: list[dict[str, str]]):
        super().__init__("character_profile_invalid")
        self.issues = issues


def _issue(path: str, message: str, level: str = "error") -> dict[str, str]:
    return {"path": path, "message": message, "level": level}


def _number_in_range(value: Any, minimum: int = 0, maximum: int = 100) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and minimum <= value <= maximum


def validate_character_profile(profile: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if len(json.dumps(profile, ensure_ascii=False)) > 50000:
        issues.append(_issue("profile", "角色配置不能超过 50000 个字符"))

    for field in ("description", "background", "safety_notes"):
        if not str(profile.get(field, "")).strip():
            issues.append(_issue(f"profile.{field}", "此项不能为空"))

    personality = profile.get("personality")
    if not isinstance(personality, list) or not any(str(item).strip() for item in personality):
        issues.append(_issue("profile.personality", "至少填写一个性格标签"))

    speech_style = profile.get("speech_style")
    if not isinstance(speech_style, dict):
        issues.append(_issue("profile.speech_style", "说话方式配置必须是对象"))
    else:
        if not str(speech_style.get("address", "")).strip():
            issues.append(_issue("profile.speech_style.address", "需要设置角色如何称呼用户"))
        if not str(speech_style.get("sentence_length", "")).strip():
            issues.append(_issue("profile.speech_style.sentence_length", "需要设置句子长度"))

    defaults = profile.get("defaults")
    if not isinstance(defaults, dict):
        issues.append(_issue("profile.defaults", "初始状态配置必须是对象"))
    else:
        for field in ("familiarity", "trust", "affection", "annoyance"):
            if not _number_in_range(defaults.get(field)):
                issues.append(_issue(f"profile.defaults.{field}", "数值必须在 0 到 100 之间"))
        if defaults.get("emotion", "calm") not in ALLOWED_EMOTIONS:
            issues.append(_issue("profile.defaults.emotion", "不是支持的情绪类型"))
        if defaults.get("scene", "first_meet") not in ALLOWED_SCENES:
            issues.append(_issue("profile.defaults.scene", "不是支持的场景类型"))

    photo_policy = profile.get("photo_policy", {})
    if not isinstance(photo_policy, dict):
        issues.append(_issue("profile.photo_policy", "照片策略必须是对象"))
    else:
        assets = photo_policy.get("assets", [])
        if not isinstance(assets, list):
            issues.append(_issue("profile.photo_policy.assets", "素材必须是 ID 列表"))
        elif any("/" in str(asset) or ".." in str(asset) for asset in assets):
            issues.append(
                _issue("profile.photo_policy.assets", "只能填写素材 ID，不能填写文件路径")
            )
        for field in ("min_familiarity", "min_trust"):
            if field in photo_policy and not _number_in_range(photo_policy[field]):
                issues.append(_issue(f"profile.photo_policy.{field}", "数值必须在 0 到 100 之间"))
        if photo_policy.get("early_outcome", "delay") not in ALLOWED_PHOTO_OUTCOMES:
            issues.append(_issue("profile.photo_policy.early_outcome", "不是支持的照片策略"))

    voice_policy = profile.get("voice_policy", {})
    if not isinstance(voice_policy, dict):
        issues.append(_issue("profile.voice_policy", "语音策略必须是对象"))
    else:
        if voice_policy.get("mode", "on_request") not in ALLOWED_VOICE_MODES:
            issues.append(_issue("profile.voice_policy.mode", "不是支持的语音模式"))
        if voice_policy.get("display_mode", "text_and_audio") not in ALLOWED_DISPLAY_MODES:
            issues.append(_issue("profile.voice_policy.display_mode", "不是支持的展示方式"))
        voice_id = str(voice_policy.get("voice_id", "")).strip()
        if "/" in voice_id or ".." in voice_id:
            issues.append(_issue("profile.voice_policy.voice_id", "音色 ID 不能包含路径字符"))

    transfer_policy = profile.get("transfer_policy", {})
    if not isinstance(transfer_policy, dict):
        issues.append(_issue("profile.transfer_policy", "转账策略必须是对象"))
    else:
        if transfer_policy.get("mode", "conditional") not in ALLOWED_TRANSFER_MODES:
            issues.append(_issue("profile.transfer_policy.mode", "不是支持的转账策略"))
        for field in ("min_familiarity", "min_trust"):
            if field in transfer_policy and not _number_in_range(transfer_policy[field]):
                issues.append(
                    _issue(
                        f"profile.transfer_policy.{field}",
                        "数值必须在 0 到 100 之间",
                    )
                )
        max_amount = transfer_policy.get("max_accept_amount_cents", 20000)
        if (
            not isinstance(max_amount, int)
            or isinstance(max_amount, bool)
            or not 1 <= max_amount <= 100000
        ):
            issues.append(
                _issue(
                    "profile.transfer_policy.max_accept_amount_cents",
                    "可接受金额上限必须在 1 到 100000 分之间",
                )
            )
        for field in ("accept_reply", "return_reply"):
            if len(str(transfer_policy.get(field, ""))) > 120:
                issues.append(
                    _issue(f"profile.transfer_policy.{field}", "转账回复不能超过 120 个字符")
                )

    scene_rules = profile.get("scene_rules", {})
    if not isinstance(scene_rules, dict):
        issues.append(_issue("profile.scene_rules", "场景规则必须是对象"))

    fallback_replies = profile.get("fallback_replies", {})
    if not isinstance(fallback_replies, dict):
        issues.append(_issue("profile.fallback_replies", "兜底回复必须是对象"))
    else:
        for field in ("photo", "photo_send", "voice", "avoid"):
            if len(str(fallback_replies.get(field, ""))) > 80:
                issues.append(
                    _issue(f"profile.fallback_replies.{field}", "回复不能超过 80 个字符")
                )

    return issues


def _valid_static_path(path: str) -> bool:
    if not path.startswith("/static/characters/"):
        return False
    parts = PurePosixPath(path).parts
    return ".." not in parts and len(parts) >= 5


class CharacterAdminService:
    def __init__(self, repository: Repository):
        self.repository = repository

    @staticmethod
    def _summary(character: Character) -> AdminCharacterSummary:
        profile = character.profile_json or {}
        return AdminCharacterSummary(
            id=character.id,
            code=character.code,
            name=character.name,
            description=str(profile.get("description", "")),
            avatar_url=character.avatar_path,
            is_active=character.is_active,
            config_status=character.config_status or "published",
            has_draft=character.draft_profile_json is not None,
            profile_version=character.profile_version or 0,
            updated_at=character.updated_at.isoformat(),
        )

    @classmethod
    def _detail(cls, character: Character) -> AdminCharacterDetail:
        published = dict(character.profile_json or {})
        draft = dict(character.draft_profile_json or published)
        summary = cls._summary(character)
        editable_code = character.draft_code or character.code
        editable_name = character.draft_name or character.name
        editable_avatar = character.draft_avatar_path or character.avatar_path
        return AdminCharacterDetail(
            **{
                **summary.model_dump(),
                "code": editable_code,
                "name": editable_name,
                "avatar_url": editable_avatar,
            },
            avatar_path=editable_avatar,
            profile=draft,
            draft_profile=draft,
            published_profile=published,
            published_at=character.published_at.isoformat() if character.published_at else None,
        )

    @staticmethod
    def _check_top_level(payload: CharacterDraftRequest) -> None:
        if not _valid_static_path(payload.avatar_path):
            raise ValueError("avatar_path_invalid")

    async def list_characters(self) -> list[AdminCharacterSummary]:
        characters = await self.repository.list_characters(include_inactive=True)
        return [self._summary(item) for item in characters]

    async def get_detail(self, character_id: int) -> AdminCharacterDetail:
        character = await self.repository.get_character(character_id)
        if character is None:
            raise ValueError("character_not_found")
        return self._detail(character)

    async def create(self, payload: CharacterCreateRequest) -> AdminCharacterDetail:
        self._check_top_level(payload)
        existing = await self.repository.list_characters(include_inactive=True)
        if any(payload.code in {item.code, item.draft_code} for item in existing):
            raise ValueError("character_code_exists")
        character = await self.repository.create_character(
            code=payload.code,
            name=payload.name.strip(),
            avatar_path=payload.avatar_path,
            profile=dict(payload.profile),
        )
        return self._detail(character)

    async def save_draft(
        self, character_id: int, payload: CharacterDraftRequest
    ) -> AdminCharacterDetail:
        self._check_top_level(payload)
        existing = await self.repository.list_characters(include_inactive=True)
        if any(
            item.id != character_id
            and payload.code in {item.code, item.draft_code}
            for item in existing
        ):
            raise ValueError("character_code_exists")
        character = await self.repository.update_character_draft(
            character_id,
            code=payload.code,
            name=payload.name.strip(),
            avatar_path=payload.avatar_path,
            profile=dict(payload.profile),
        )
        return self._detail(character)

    async def validate(self, profile: dict[str, Any]) -> list[ValidationIssue]:
        return [ValidationIssue(**item) for item in validate_character_profile(profile)]

    async def publish(self, character_id: int) -> AdminCharacterDetail:
        character = await self.repository.get_character(character_id)
        if character is None:
            raise ValueError("character_not_found")
        profile = dict(character.draft_profile_json or character.profile_json or {})
        issues = validate_character_profile(profile)
        if issues:
            raise CharacterProfileValidationError(issues)
        return self._detail(await self.repository.publish_character(character_id))

    async def set_active(self, character_id: int, is_active: bool) -> AdminCharacterDetail:
        character = await self.repository.set_character_active(character_id, is_active)
        return self._detail(character)

    async def duplicate(self, character_id: int) -> AdminCharacterDetail:
        source = await self.repository.get_character(character_id)
        if source is None:
            raise ValueError("character_not_found")
        existing_codes = {
            item.code for item in await self.repository.list_characters(include_inactive=True)
        }
        base = f"{source.code[:48]}-copy"
        code = base
        index = 2
        while code in existing_codes:
            code = f"{base[:45]}-{index}"
            index += 1
        return self._detail(await self.repository.duplicate_character(character_id, code))


__all__ = [
    "CharacterAdminService",
    "CharacterProfileValidationError",
    "validate_character_profile",
]
