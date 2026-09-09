from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.graph.builder import build_graph
from app.graph.runtime import GraphRuntime
from app.services.asset_service import AssetResolver
from app.services.llm_service import LLMUnavailableError


class FakeRepository:
    def __init__(self, *, code: str, profile: dict):
        self.character = SimpleNamespace(
            id=1,
            code=code,
            name="测试角色",
            avatar_path=f"/static/characters/{code}/avatar.svg",
            profile_json=profile,
            is_active=True,
        )
        self.conversation = SimpleNamespace(
            id=1,
            user_id="test-user",
            relationship_state=profile["defaults"],
            emotion_state={
                "dominant": profile["defaults"]["emotion"],
                "intensity": profile["defaults"]["emotion_intensity"],
                "valence": 0,
                "updated_at": datetime.now(UTC).isoformat(),
            },
            scene_state={"current": "first_meet", "turn_count": 0},
        )

    async def load_context(self, conversation_id: int, user_id: str):
        return {
            "conversation": self.conversation,
            "character": self.character,
            "recent_messages": [],
            "memories": [],
        }


class DisabledLLM:
    async def invoke_structured(self, *args, **kwargs):
        raise LLMUnavailableError("test_disabled")


class DisabledTTS:
    enabled = False


@pytest.mark.asyncio
async def test_graph_fallback_completes_without_llm():
    profile = {
        "description": "test",
        "goals": {"primary": "get_familiar"},
        "photo_policy": {"enabled": True, "assets": ["photo-1"]},
        "voice_policy": {"mode": "on_request", "voice_id": "fictional"},
        "defaults": {
            "familiarity": 8,
            "trust": 5,
            "affection": 4,
            "annoyance": 0,
            "emotion": "calm",
            "emotion_intensity": 30,
        },
        "fallback_replies": {},
    }
    runtime = GraphRuntime(
        repository=FakeRepository(code="suhe", profile=profile),
        llm=DisabledLLM(),
        tts=DisabledTTS(),
        assets=AssetResolver(),
    )
    result = await build_graph(runtime).ainvoke(
        {
            "conversation_id": 1,
            "user_id": "test-user",
            "user_message": "你好",
            "reply_messages": [],
            "memory_candidates": [],
        }
    )
    assert result["reply_messages"][0]["message_type"] == "text"
    assert result["persistence_patch"]["scene"]["current"] == "first_meet"
    assert result["memory_candidates"] == []


@pytest.mark.asyncio
async def test_graph_photo_branch_uses_allowlisted_local_asset():
    profile = {
        "description": "test",
        "goals": {"primary": "get_familiar"},
        "photo_policy": {
            "enabled": True,
            "assets": ["photo-1"],
            "min_familiarity": 0,
            "min_trust": 0,
            "early_outcome": "delay",
        },
        "voice_policy": {"mode": "never"},
        "defaults": {
            "familiarity": 10,
            "trust": 10,
            "affection": 4,
            "annoyance": 0,
            "emotion": "calm",
            "emotion_intensity": 30,
        },
        "fallback_replies": {},
    }
    runtime = GraphRuntime(
        repository=FakeRepository(code="suhe", profile=profile),
        llm=DisabledLLM(),
        tts=DisabledTTS(),
        assets=AssetResolver(),
    )
    result = await build_graph(runtime).ainvoke(
        {
            "conversation_id": 1,
            "user_id": "test-user",
            "user_message": "可以发照片吗",
            "reply_messages": [],
            "memory_candidates": [],
        }
    )
    assert any(item["message_type"] == "image" for item in result["reply_messages"])
    text = next(item for item in result["reply_messages"] if item["message_type"] == "text")
    assert text["content"] == "好吧，给你看一张。"
    image = next(item for item in result["reply_messages"] if item["message_type"] == "image")
    assert image["image_path"] == "/static/characters/suhe/photos/photo-1.svg"
