from copy import deepcopy

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.schemas import CharacterDraftRequest
from app.db.base import Base
from app.db.models import Character
from app.db.repositories import Repository
from app.seed import load_seed_characters
from app.services.character_admin_service import CharacterAdminService, validate_character_profile


def test_seed_contains_the_three_editable_demo_characters():
    characters = load_seed_characters()

    assert {item["code"] for item in characters} == {"suhe", "linwan", "shenyan"}
    assert all(item["profile_json"]["personality"] for item in characters)


def test_seed_profiles_are_valid_for_publishing():
    characters = load_seed_characters()

    for character in characters:
        assert validate_character_profile(character["profile_json"]) == []


def test_profile_validation_rejects_untrusted_media_paths():
    profile = load_seed_characters()[0]["profile_json"]
    profile["photo_policy"]["assets"] = ["../secret.png"]

    issues = validate_character_profile(profile)

    assert any(issue["path"] == "profile.photo_policy.assets" for issue in issues)


def test_profile_validation_matches_runtime_reply_limit():
    profile = deepcopy(load_seed_characters()[0]["profile_json"])
    profile["fallback_replies"]["photo"] = "哈" * 81

    issues = validate_character_profile(profile)

    assert any(issue["path"] == "profile.fallback_replies.photo" for issue in issues)


@pytest.mark.asyncio
async def test_published_character_stays_public_while_draft_is_edited():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        seed = load_seed_characters()[0]
        async with factory() as session:
            character = Character(
                code=seed["code"],
                name=seed["name"],
                avatar_path=seed["avatar_path"],
                profile_json=seed["profile_json"],
                profile_version=1,
                config_status="published",
                is_active=True,
            )
            session.add(character)
            await session.commit()
            await session.refresh(character)
            character_id = character.id

        repository = Repository(factory)
        service = CharacterAdminService(repository)
        draft_profile = deepcopy(seed["profile_json"])
        draft_profile["description"] = "这只是尚未发布的新简介。"
        detail = await service.save_draft(
            character_id,
            CharacterDraftRequest(
                code="suhe-new",
                name="草稿名字",
                avatar_path="/static/characters/shenyan/avatar.svg",
                profile=draft_profile,
            ),
        )

        public_characters = await repository.list_active_characters()
        stored = await repository.get_character(character_id)
        assert [item.code for item in public_characters] == ["suhe"]
        assert stored is not None
        assert stored.code == "suhe"
        assert stored.name == "苏禾"
        assert stored.profile_json["description"] == seed["profile_json"]["description"]
        assert detail.code == "suhe-new"
        assert detail.name == "草稿名字"
        assert detail.has_draft is True
        assert detail.config_status == "published"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_publish_promotes_profile_and_top_level_draft_together():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        repository = Repository(factory)
        seed = load_seed_characters()[0]
        created = await repository.create_character(
            code="new-role",
            name="新角色",
            avatar_path="/static/characters/suhe/avatar.svg",
            profile=seed["profile_json"],
        )
        service = CharacterAdminService(repository)

        published = await service.publish(created.id)
        public_characters = await repository.list_active_characters()

        assert published.code == "new-role"
        assert published.name == "新角色"
        assert published.profile_version == 1
        assert published.has_draft is False
        assert [item.code for item in public_characters] == ["new-role"]
    finally:
        await engine.dispose()
