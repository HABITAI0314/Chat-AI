from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.api.schemas import (
    AdminPreviewRequest,
    CharacterSummary,
    ConversationResponse,
    TransferRequest,
)
from app.db.models import Character, Conversation
from app.db.repositories import Repository
from app.domain.relationship import apply_relationship_delta
from app.domain.transfer import format_transfer_amount, resolve_transfer
from app.graph.builder import build_graph
from app.graph.runtime import GraphRuntime
from app.services.asset_service import AssetResolver
from app.services.llm_service import LLMService
from app.services.tts_service import TTSService


def character_summary(character: Character) -> CharacterSummary:
    profile = character.profile_json or {}
    return CharacterSummary(
        id=character.id,
        code=character.code,
        name=character.name,
        description=profile.get("description", ""),
        avatar_url=character.avatar_path,
    )


def conversation_response(conversation: Conversation, character: Character) -> ConversationResponse:
    return ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        character=character_summary(character),
        relationship=conversation.relationship_state or {},
        emotion=conversation.emotion_state or {},
        scene=conversation.scene_state or {},
    )


class ChatService:
    def __init__(self, repository: Repository):
        self.repository = repository
        runtime = GraphRuntime(
            repository=repository,
            llm=LLMService(),
            tts=TTSService(),
            assets=AssetResolver(),
        )
        self.graph = build_graph(runtime)

    async def list_characters(self) -> list[CharacterSummary]:
        return [character_summary(item) for item in await self.repository.list_active_characters()]

    async def open_conversation(
        self, user_id: str, character_id: int
    ) -> ConversationResponse:
        conversation, character = await self.repository.get_or_create_conversation(
            user_id, character_id
        )
        return conversation_response(conversation, character)

    async def history(self, conversation_id: int, user_id: str) -> dict[str, Any]:
        bundle = await self.repository.get_history(conversation_id, user_id)
        return {
            "conversation": conversation_response(bundle["conversation"], bundle["character"]),
            "messages": bundle["messages"],
        }

    async def reset_conversation(
        self, conversation_id: int, user_id: str
    ) -> ConversationResponse:
        conversation, character = await self.repository.reset_conversation(
            conversation_id, user_id
        )
        return conversation_response(conversation, character)

    async def memories(self, conversation_id: int, user_id: str) -> list[dict[str, Any]]:
        return await self.repository.list_memories(conversation_id, user_id)

    async def delete_memory(
        self, conversation_id: int, memory_id: int, user_id: str
    ) -> None:
        await self.repository.delete_memory(conversation_id, memory_id, user_id)

    async def send_message(
        self, conversation_id: int, user_id: str, content: str
    ) -> dict[str, Any]:
        content = content.strip()
        if not content:
            raise ValueError("message_empty")

        result = await self.graph.ainvoke(
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "user_message": content,
                "reply_messages": [],
                "memory_candidates": [],
            }
        )
        persisted = await self.repository.persist_turn(
            conversation_id=conversation_id,
            user_id=user_id,
            user_content=content,
            reply_messages=result.get("reply_messages", []),
            persistence_patch=result["persistence_patch"],
            memory_candidates=result.get("memory_candidates", []),
        )
        patch = result["persistence_patch"]
        return {
            "user_message": persisted["user_message"],
            "assistant_messages": persisted["assistant_messages"],
            "state": {
                "relationship": patch["relationship"],
                "emotion": patch["emotion"],
                "scene": patch["scene"],
            },
        }

    async def send_transfer(
        self, conversation_id: int, payload: TransferRequest
    ) -> dict[str, Any]:
        bundle = await self.repository.load_context(conversation_id, payload.user_id)
        character = bundle["character"]
        relationship = dict(bundle["conversation"].relationship_state or {})
        decision = resolve_transfer(
            dict(character.profile_json or {}),
            relationship,
            payload.amount_cents,
        )
        amount = format_transfer_amount(payload.amount_cents)
        transfer_metadata = {
            "event": "simulated_transfer",
            "transfer_id": f"tr_{uuid4().hex[:20]}",
            "amount_cents": payload.amount_cents,
            "note": payload.note.strip(),
            "status": decision["status"],
            "reason": decision["reason"],
        }
        relationship_patch = apply_relationship_delta(
            relationship,
            decision["relationship_delta"],
        )
        reply = decision["reply"].replace("{{amount}}", amount)
        persisted = await self.repository.persist_turn(
            conversation_id=conversation_id,
            user_id=payload.user_id,
            user_content=f"模拟转账 {amount}",
            user_message_type="transfer",
            user_metadata=transfer_metadata,
            reply_messages=[
                {
                    "message_type": "text",
                    "content": reply,
                    "delay_ms": 420,
                    "metadata": {
                        "tone": "warm" if decision["status"] == "accepted" else "guarded",
                        "transfer_status": decision["status"],
                    },
                }
            ],
            persistence_patch={
                "relationship": relationship_patch,
                "emotion": bundle["conversation"].emotion_state or {},
                "scene": bundle["conversation"].scene_state or {},
            },
            memory_candidates=[],
        )
        return {
            "user_message": persisted["user_message"],
            "assistant_messages": persisted["assistant_messages"],
            "state": {
                "relationship": relationship_patch,
                "emotion": bundle["conversation"].emotion_state or {},
                "scene": bundle["conversation"].scene_state or {},
            },
        }

    async def preview(
        self, character_id: int, payload: AdminPreviewRequest
    ) -> dict[str, Any]:
        character = await self.repository.get_character(character_id)
        if character is None:
            raise ValueError("character_not_found")

        profile = dict(payload.profile)
        defaults = profile.get("defaults", {})
        relationship = dict(payload.relationship or {})
        relationship = {
            "familiarity": int(relationship.get("familiarity", defaults.get("familiarity", 0))),
            "trust": int(relationship.get("trust", defaults.get("trust", 0))),
            "affection": int(relationship.get("affection", defaults.get("affection", 0))),
            "annoyance": int(relationship.get("annoyance", defaults.get("annoyance", 0))),
            "turn_count": int(relationship.get("turn_count", 0)),
        }
        emotion = dict(payload.emotion or {})
        emotion = {
            "dominant": emotion.get("dominant", defaults.get("emotion", "calm")),
            "intensity": int(
                emotion.get("intensity", defaults.get("emotion_intensity", 35))
            ),
            "valence": int(emotion.get("valence", defaults.get("emotion_valence", 0))),
            "updated_at": emotion.get("updated_at", datetime.now(UTC).isoformat()),
        }
        scene = dict(payload.scene or {})
        scene = {
            "current": scene.get("current", defaults.get("scene", "first_meet")),
            "turn_count": int(scene.get("turn_count", 0)),
            "flags": list(scene.get("flags", [])),
            "last_transition_reason": scene.get("last_transition_reason", "preview_started"),
            "updated_at": scene.get("updated_at", datetime.now(UTC).isoformat()),
        }
        result = await self.graph.ainvoke(
            {
                "conversation_id": 0,
                "user_id": "admin-preview",
                "user_message": payload.user_message,
                "preview_context": {
                    "character_id": character_id,
                    "code": character.code,
                    "name": payload.name,
                    "avatar_url": payload.avatar_url or character.avatar_path,
                    "profile": profile,
                    "recent_messages": payload.recent_messages,
                    "relationship": relationship,
                    "emotion": emotion,
                    "scene": scene,
                    "memories": payload.memories,
                },
                "reply_messages": [],
                "memory_candidates": [],
            }
        )
        now = datetime.now(UTC).isoformat()
        assistant_messages: list[dict[str, Any]] = []
        for index, item in enumerate(result.get("reply_messages", [])):
            assistant_messages.append(
                {
                    "id": -(int(datetime.now(UTC).timestamp() * 1000) + index),
                    "role": "assistant",
                    "message_type": item.get("message_type", "text"),
                    "content": item.get("content"),
                    "image_url": item.get("image_path"),
                    "audio_url": item.get("audio_path"),
                    "audio_duration_ms": item.get("audio_duration_ms"),
                    "metadata": item.get("metadata", {}),
                    "created_at": now,
                    "delay_ms": item.get("delay_ms", 0),
                }
            )
        persistence_patch = result.get("persistence_patch", {})
        return {
            "assistant_messages": assistant_messages,
            "state": {
                "relationship": persistence_patch.get("relationship", relationship),
                "emotion": persistence_patch.get("emotion", emotion),
                "scene": persistence_patch.get("scene", scene),
            },
            "debug": {
                "behavior_decision": self._dump_graph_value(result.get("behavior_decision")),
                "image_decision": self._dump_graph_value(result.get("image_decision")),
                "voice_decision": self._dump_graph_value(result.get("voice_decision")),
                "memory_candidates": result.get("memory_candidates", []),
            },
        }

    @staticmethod
    def _dump_graph_value(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return value or {}
