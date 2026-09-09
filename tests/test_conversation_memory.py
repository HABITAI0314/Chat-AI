import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import Character, Memory, Message
from app.db.repositories import Repository
from app.seed import load_seed_characters


@pytest.mark.asyncio
async def test_reset_conversation_clears_messages_memories_and_progress():
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
        conversation, _ = await repository.get_or_create_conversation("user-1", character_id)
        async with factory() as session:
            session.add(
                Message(
                    conversation_id=conversation.id,
                    role="user",
                    message_type="text",
                    content="我喜欢乌龙茶",
                    metadata_json={},
                )
            )
            session.add(
                Memory(
                    conversation_id=conversation.id,
                    memory_type="preference",
                    content="用户喜欢乌龙茶",
                    importance=4,
                )
            )
            stored = await session.get(type(conversation), conversation.id)
            stored.relationship_state = {"familiarity": 80, "turn_count": 12}
            stored.scene_state = {"current": "plot", "turn_count": 12}
            await session.commit()

        reset, _ = await repository.reset_conversation(conversation.id, "user-1")
        history = await repository.get_history(conversation.id, "user-1")
        memories = await repository.list_memories(conversation.id, "user-1")

        assert history["messages"] == []
        assert memories == []
        assert reset.relationship_state["turn_count"] == 0
        assert reset.scene_state["current"] == seed["profile_json"]["defaults"]["scene"]
        assert reset.scene_state["last_transition_reason"] == "conversation_reset"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_duplicate_memory_updates_importance_and_can_be_deleted():
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
        conversation, _ = await repository.get_or_create_conversation("user-2", character_id)
        patch = {
            "relationship": conversation.relationship_state,
            "emotion": conversation.emotion_state,
            "scene": conversation.scene_state,
        }
        for importance in (2, 5):
            await repository.persist_turn(
                conversation_id=conversation.id,
                user_id="user-2",
                user_content="我喜欢 乌龙茶",
                reply_messages=[],
                persistence_patch=patch,
                memory_candidates=[
                    {
                        "type": "preference",
                        "content": "用户喜欢   乌龙茶",
                        "importance": importance,
                    }
                ],
            )

        memories = await repository.list_memories(conversation.id, "user-2")
        assert len(memories) == 1
        assert memories[0]["content"] == "用户喜欢 乌龙茶"
        assert memories[0]["importance"] == 5

        await repository.delete_memory(conversation.id, memories[0]["id"], "user-2")
        assert await repository.list_memories(conversation.id, "user-2") == []
    finally:
        await engine.dispose()
