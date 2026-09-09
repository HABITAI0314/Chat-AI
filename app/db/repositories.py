from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import Character, Conversation, Memory, Message


def _now() -> datetime:
    return datetime.now(UTC)


def _defaults(profile: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    defaults = profile.get("defaults", {})
    relationship = {
        "familiarity": int(defaults.get("familiarity", 0)),
        "trust": int(defaults.get("trust", 0)),
        "affection": int(defaults.get("affection", 0)),
        "annoyance": int(defaults.get("annoyance", 0)),
        "turn_count": 0,
    }
    emotion = {
        "dominant": defaults.get("emotion", "calm"),
        "intensity": int(defaults.get("emotion_intensity", 35)),
        "valence": int(defaults.get("emotion_valence", 0)),
        "updated_at": _now().isoformat(),
    }
    scene = {
        "current": defaults.get("scene", "first_meet"),
        "turn_count": 0,
        "flags": [],
        "last_transition_reason": "conversation_created",
        "updated_at": _now().isoformat(),
    }
    return relationship, emotion, scene


class Repository:
    def __init__(self, factory: async_sessionmaker[AsyncSession]):
        self.factory = factory

    async def list_active_characters(self) -> list[Character]:
        return await self.list_characters(include_inactive=False, published_only=True)

    async def list_characters(
        self, *, include_inactive: bool = True, published_only: bool = False
    ) -> list[Character]:
        async with self.factory() as session:
            statement = select(Character)
            if not include_inactive:
                statement = statement.where(Character.is_active.is_(True))
            if published_only:
                statement = statement.where(Character.config_status == "published")
            result = await session.execute(statement.order_by(Character.id))
            return list(result.scalars().all())

    async def get_character(self, character_id: int) -> Character | None:
        async with self.factory() as session:
            return await session.get(Character, character_id)

    async def create_character(
        self,
        *,
        code: str,
        name: str,
        avatar_path: str,
        profile: dict[str, Any],
    ) -> Character:
        async with self.factory() as session:
            character = Character(
                code=code,
                name=name,
                avatar_path=avatar_path,
                profile_json={},
                draft_code=code,
                draft_name=name,
                draft_avatar_path=avatar_path,
                draft_profile_json=profile,
                profile_version=0,
                config_status="draft",
                is_active=True,
            )
            session.add(character)
            await session.commit()
            await session.refresh(character)
            return character

    async def update_character_draft(
        self,
        character_id: int,
        *,
        code: str,
        name: str,
        avatar_path: str,
        profile: dict[str, Any],
    ) -> Character:
        async with self.factory() as session:
            character = await session.get(Character, character_id)
            if character is None:
                raise ValueError("character_not_found")
            character.draft_code = code
            character.draft_name = name
            character.draft_avatar_path = avatar_path
            character.draft_profile_json = profile
            if not character.profile_json or not character.profile_version:
                character.config_status = "draft"
            character.updated_at = _now()
            await session.commit()
            await session.refresh(character)
            return character

    async def publish_character(self, character_id: int) -> Character:
        async with self.factory() as session:
            character = await session.get(Character, character_id)
            if character is None:
                raise ValueError("character_not_found")
            character.code = character.draft_code or character.code
            character.name = character.draft_name or character.name
            character.avatar_path = character.draft_avatar_path or character.avatar_path
            character.profile_json = dict(
                character.draft_profile_json or character.profile_json or {}
            )
            character.draft_code = None
            character.draft_name = None
            character.draft_avatar_path = None
            character.draft_profile_json = None
            character.profile_version = max(character.profile_version or 0, 0) + 1
            character.config_status = "published"
            character.published_at = _now()
            character.updated_at = _now()
            await session.commit()
            await session.refresh(character)
            return character

    async def set_character_active(self, character_id: int, is_active: bool) -> Character:
        async with self.factory() as session:
            character = await session.get(Character, character_id)
            if character is None:
                raise ValueError("character_not_found")
            character.is_active = is_active
            character.updated_at = _now()
            await session.commit()
            await session.refresh(character)
            return character

    async def duplicate_character(self, character_id: int, new_code: str) -> Character:
        async with self.factory() as session:
            source = await session.get(Character, character_id)
            if source is None:
                raise ValueError("character_not_found")
            profile = dict(source.draft_profile_json or source.profile_json or {})
            source_name = source.draft_name or source.name
            source_avatar = source.draft_avatar_path or source.avatar_path
            character = Character(
                code=new_code,
                name=f"{source_name} 副本",
                avatar_path=source_avatar,
                profile_json={},
                draft_code=new_code,
                draft_name=f"{source_name} 副本",
                draft_avatar_path=source_avatar,
                draft_profile_json=profile,
                profile_version=0,
                config_status="draft",
                is_active=True,
            )
            session.add(character)
            await session.commit()
            await session.refresh(character)
            return character

    async def get_conversation(self, conversation_id: int) -> Conversation | None:
        async with self.factory() as session:
            return await session.get(Conversation, conversation_id)

    async def get_or_create_conversation(
        self, user_id: str, character_id: int
    ) -> tuple[Conversation, Character]:
        async with self.factory() as session:
            character = await session.get(Character, character_id)
            if (
                character is None
                or not character.is_active
                or getattr(character, "config_status", "published") != "published"
            ):
                raise ValueError("character_not_found")

            result = await session.execute(
                select(Conversation).where(
                    Conversation.user_id == user_id,
                    Conversation.character_id == character_id,
                )
            )
            conversation = result.scalar_one_or_none()
            if conversation is None:
                relationship, emotion, scene = _defaults(character.profile_json)
                conversation = Conversation(
                    user_id=user_id,
                    character_id=character_id,
                    relationship_state=relationship,
                    emotion_state=emotion,
                    scene_state=scene,
                )
                session.add(conversation)
                await session.commit()
                await session.refresh(conversation)
            return conversation, character

    async def load_context(self, conversation_id: int, user_id: str) -> dict[str, Any]:
        async with self.factory() as session:
            conversation = await session.get(Conversation, conversation_id)
            if conversation is None or conversation.user_id != user_id:
                raise ValueError("conversation_not_found")

            character = await session.get(Character, conversation.character_id)
            if character is None or not character.is_active:
                raise ValueError("character_not_found")

            message_result = await session.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(desc(Message.created_at), desc(Message.id))
                .limit(20)
            )
            messages: Sequence[Message] = list(message_result.scalars().all())
            memory_result = await session.execute(
                select(Memory)
                .where(Memory.conversation_id == conversation_id, Memory.is_active.is_(True))
                .order_by(desc(Memory.importance), desc(Memory.last_used_at), desc(Memory.id))
                .limit(10)
            )
            memories: Sequence[Memory] = list(memory_result.scalars().all())

            return {
                "conversation": conversation,
                "character": character,
                "recent_messages": [
                    {
                        "id": item.id,
                        "role": item.role,
                        "message_type": item.message_type,
                        "content": item.content,
                        "image_path": item.image_path,
                        "audio_path": item.audio_path,
                        "metadata": item.metadata_json or {},
                        "created_at": item.created_at.isoformat(),
                    }
                    for item in reversed(messages)
                ],
                "memories": [
                    {
                        "id": item.id,
                        "type": item.memory_type,
                        "content": item.content,
                        "importance": item.importance,
                    }
                    for item in reversed(memories)
                ],
            }

    async def get_history(self, conversation_id: int, user_id: str) -> dict[str, Any]:
        async with self.factory() as session:
            conversation = await session.get(Conversation, conversation_id)
            if conversation is None or conversation.user_id != user_id:
                raise ValueError("conversation_not_found")
            character = await session.get(Character, conversation.character_id)
            if character is None:
                raise ValueError("character_not_found")
            result = await session.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at, Message.id)
            )
            messages = list(result.scalars().all())
            return {
                "conversation": conversation,
                "character": character,
                "messages": [self.serialize_message(item) for item in messages],
            }

    async def reset_conversation(
        self, conversation_id: int, user_id: str
    ) -> tuple[Conversation, Character]:
        async with self.factory() as session:
            async with session.begin():
                conversation = await session.get(Conversation, conversation_id)
                if conversation is None or conversation.user_id != user_id:
                    raise ValueError("conversation_not_found")
                character = await session.get(Character, conversation.character_id)
                if character is None:
                    raise ValueError("character_not_found")

                await session.execute(
                    delete(Memory).where(Memory.conversation_id == conversation_id)
                )
                await session.execute(
                    delete(Message).where(Message.conversation_id == conversation_id)
                )
                relationship, emotion, scene = _defaults(character.profile_json or {})
                scene["last_transition_reason"] = "conversation_reset"
                conversation.relationship_state = relationship
                conversation.emotion_state = emotion
                conversation.scene_state = scene
                conversation.updated_at = _now()
                await session.flush()
                return conversation, character

    async def list_memories(self, conversation_id: int, user_id: str) -> list[dict[str, Any]]:
        async with self.factory() as session:
            conversation = await session.get(Conversation, conversation_id)
            if conversation is None or conversation.user_id != user_id:
                raise ValueError("conversation_not_found")
            result = await session.execute(
                select(Memory)
                .where(Memory.conversation_id == conversation_id, Memory.is_active.is_(True))
                .order_by(desc(Memory.importance), desc(Memory.created_at), desc(Memory.id))
            )
            return [self.serialize_memory(item) for item in result.scalars().all()]

    async def delete_memory(
        self, conversation_id: int, memory_id: int, user_id: str
    ) -> None:
        async with self.factory() as session:
            async with session.begin():
                conversation = await session.get(Conversation, conversation_id)
                if conversation is None or conversation.user_id != user_id:
                    raise ValueError("conversation_not_found")
                memory = await session.get(Memory, memory_id)
                if memory is None or memory.conversation_id != conversation_id:
                    raise ValueError("memory_not_found")
                await session.delete(memory)

    async def persist_turn(
        self,
        *,
        conversation_id: int,
        user_id: str,
        user_content: str,
        reply_messages: list[dict[str, Any]],
        persistence_patch: dict[str, Any],
        memory_candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        async with self.factory() as session:
            async with session.begin():
                conversation = await session.get(Conversation, conversation_id)
                if conversation is None or conversation.user_id != user_id:
                    raise ValueError("conversation_not_found")

                user_message = Message(
                    conversation_id=conversation_id,
                    role="user",
                    message_type="text",
                    content=user_content,
                    metadata_json={},
                )
                session.add(user_message)
                await session.flush()

                persisted_replies: list[dict[str, Any]] = []
                for payload in reply_messages:
                    message = Message(
                        conversation_id=conversation_id,
                        role="assistant",
                        message_type=payload["message_type"],
                        content=payload.get("content"),
                        image_path=payload.get("image_path"),
                        audio_path=payload.get("audio_path"),
                        audio_duration_ms=payload.get("audio_duration_ms"),
                        metadata_json=payload.get("metadata", {}),
                    )
                    session.add(message)
                    await session.flush()
                    persisted = self.serialize_message(message)
                    persisted["delay_ms"] = payload.get("delay_ms", 0)
                    persisted_replies.append(persisted)

                conversation.relationship_state = persistence_patch["relationship"]
                conversation.emotion_state = persistence_patch["emotion"]
                conversation.scene_state = persistence_patch["scene"]
                conversation.updated_at = _now()

                for candidate in memory_candidates:
                    content = " ".join(candidate.get("content", "").split())
                    if not content:
                        continue
                    duplicate = await session.execute(
                        select(Memory).where(
                            Memory.conversation_id == conversation_id,
                            Memory.is_active.is_(True),
                            Memory.content == content,
                        )
                    )
                    existing = duplicate.scalar_one_or_none()
                    if existing is not None:
                        existing.importance = max(
                            existing.importance, int(candidate.get("importance", 3))
                        )
                        existing.last_used_at = _now()
                        continue
                    session.add(
                        Memory(
                            conversation_id=conversation_id,
                            memory_type=candidate.get("type", "preference"),
                            content=content,
                            importance=int(candidate.get("importance", 3)),
                            source_message_id=user_message.id,
                            last_used_at=_now(),
                        )
                    )

                active_memories = await session.execute(
                    select(Memory)
                    .where(
                        Memory.conversation_id == conversation_id,
                        Memory.is_active.is_(True),
                    )
                    .order_by(desc(Memory.importance), desc(Memory.created_at), desc(Memory.id))
                )
                for stale_memory in list(active_memories.scalars().all())[20:]:
                    stale_memory.is_active = False

                await session.flush()
                return {
                    "user_message": self.serialize_message(user_message),
                    "assistant_messages": persisted_replies,
                    "conversation": conversation,
                }

    @staticmethod
    def serialize_message(message: Message) -> dict[str, Any]:
        metadata = message.metadata_json or {}
        result = {
            "id": message.id,
            "role": message.role,
            "message_type": message.message_type,
            "content": message.content,
            "image_url": message.image_path,
            "audio_url": message.audio_path,
            "audio_duration_ms": message.audio_duration_ms,
            "metadata": metadata,
            "created_at": message.created_at.isoformat(),
        }
        if metadata.get("transcript"):
            result["transcript"] = metadata["transcript"]
        return result

    @staticmethod
    def serialize_memory(memory: Memory) -> dict[str, Any]:
        return {
            "id": memory.id,
            "memory_type": memory.memory_type,
            "content": memory.content,
            "importance": memory.importance,
            "created_at": memory.created_at.isoformat(),
        }
