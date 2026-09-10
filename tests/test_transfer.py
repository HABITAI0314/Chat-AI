import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.schemas import TransferRequest
from app.db.base import Base
from app.db.models import Character
from app.db.repositories import Repository
from app.domain.transfer import resolve_transfer
from app.seed import load_seed_characters
from app.services.chat_service import ChatService


def test_seeded_characters_have_distinct_transfer_reactions():
    profiles = {item["code"]: item["profile_json"] for item in load_seed_characters()}

    assert (
        resolve_transfer(profiles["linwan"], {"familiarity": 0, "trust": 0}, 8800)["status"]
        == "accepted"
    )
    assert (
        resolve_transfer(profiles["suhe"], {"familiarity": 8, "trust": 5}, 8800)["status"]
        == "returned"
    )
    assert (
        resolve_transfer(profiles["shenyan"], {"familiarity": 80, "trust": 80}, 8800)["status"]
        == "returned"
    )


def test_conditional_transfer_accepts_only_when_relationship_and_amount_allow_it():
    profile = {
        "personality": ["慢热"],
        "transfer_policy": {
            "mode": "conditional",
            "min_familiarity": 20,
            "min_trust": 10,
            "max_accept_amount_cents": 10000,
        },
    }

    assert (
        resolve_transfer(profile, {"familiarity": 20, "trust": 10}, 10000)["status"]
        == "accepted"
    )
    assert (
        resolve_transfer(profile, {"familiarity": 19, "trust": 10}, 10000)["status"]
        == "returned"
    )
    assert (
        resolve_transfer(profile, {"familiarity": 20, "trust": 10}, 10001)["status"]
        == "returned"
    )


def test_direct_accept_policy_still_respects_the_configured_amount_cap():
    profile = {
        "transfer_policy": {
            "mode": "accept",
            "max_accept_amount_cents": 20000,
        }
    }

    assert resolve_transfer(profile, {}, 20001)["status"] == "returned"


def test_legacy_profile_uses_personality_as_a_safe_fallback():
    decision = resolve_transfer(
        {"personality": ["克制", "有边界"]},
        {"familiarity": 100, "trust": 100},
        100,
    )

    assert decision["status"] == "returned"


@pytest.mark.asyncio
async def test_transfer_is_persisted_with_result_metadata_and_history():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        seed = next(item for item in load_seed_characters() if item["code"] == "linwan")
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
        service = ChatService(repository)
        conversation = await service.open_conversation("transfer-test-user", character_id)
        result = await service.send_transfer(
            conversation.id,
            TransferRequest(user_id="transfer-test-user", amount_cents=8800, note="请你喝茶"),
        )

        user_message = result["user_message"]
        assert user_message["message_type"] == "transfer"
        assert user_message["metadata"]["event"] == "simulated_transfer"
        assert user_message["metadata"]["status"] == "accepted"
        assert result["assistant_messages"][0]["content"]

        history = await service.history(conversation.id, "transfer-test-user")
        assert history["messages"][0]["message_type"] == "transfer"
        assert history["messages"][0]["metadata"]["amount_cents"] == 8800
    finally:
        await engine.dispose()
