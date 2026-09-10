from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class RelationshipDelta(StrictModel):
    familiarity: int = Field(default=0, ge=-10, le=10)
    trust: int = Field(default=0, ge=-10, le=10)
    affection: int = Field(default=0, ge=-10, le=10)
    annoyance: int = Field(default=0, ge=-10, le=10)


class EmotionSignal(StrictModel):
    target: Literal["calm", "happy", "shy", "curious", "annoyed", "sad", "guarded"] = "calm"
    intensity_delta: int = Field(default=0, ge=-20, le=20)


class BehaviorDecision(StrictModel):
    intent: Literal[
        "greeting",
        "question",
        "emotion_share",
        "request_photo",
        "request_voice",
        "relationship_test",
        "scene_participation",
        "complaint",
        "other",
    ] = "other"
    action: Literal["normal_reply", "avoid", "advance_scene", "ask_clarification"] = (
        "normal_reply"
    )
    emotion: EmotionSignal = Field(default_factory=EmotionSignal)
    relationship_delta: RelationshipDelta = Field(default_factory=RelationshipDelta)
    scene_action: Literal[
        "none",
        "keep",
        "enter_familiar",
        "enter_daily",
        "advance_plot",
        "end_plot",
        "delay",
    ] = "keep"
    should_send_image: bool = False
    should_send_voice: bool = False
    internal_reason: str = ""


class TextReply(StrictModel):
    content: str = Field(min_length=1, max_length=200)
    delay_ms: int = Field(default=0, ge=0, le=10000)
    tone: str = "normal"

    @field_validator("tone", mode="before")
    @classmethod
    def normalize_tone(cls, v: Any) -> str:
        if not isinstance(v, str):
            return "normal"
        v = v.strip().lower()
        allowed = {"normal", "teasing", "guarded", "warm", "sales_script"}
        return v if v in allowed else "normal"


class ReplyPlan(StrictModel):
    messages: list[TextReply] = Field(min_length=1)
    photo_send_text: str = Field(default="好吧，给你看一张。", max_length=200)
    photo_fallback_text: str = Field(default="", max_length=200)
    voice_text: str = Field(default="", max_length=300)

    @field_validator("messages", mode="before")
    @classmethod
    def normalize_messages(cls, v: Any) -> list[Any]:
        if isinstance(v, list):
            cleaned = [item for item in v if item]
            return cleaned[:3] if len(cleaned) > 3 else (cleaned or [{"content": "我在呢。"}])
        elif isinstance(v, dict):
            return [v]
        elif isinstance(v, str) and v.strip():
            return [{"content": v.strip()}]
        return [{"content": "我在呢。"}]


class ImageDecision(StrictModel):
    outcome: Literal["none", "send", "decline", "delay"] = "none"
    asset_id: str | None = None
    image_url: str | None = None
    reason: str = ""


class VoiceDecision(StrictModel):
    outcome: Literal["none", "send"] = "none"
    voice_id: str | None = None
    display_mode: Literal["text_and_audio", "audio_only"] = "text_and_audio"
    text: str = ""
    reason: str = ""


class MemoryCandidate(StrictModel):
    type: Literal["preference", "experience", "important_event", "boundary"] = "preference"
    content: str = Field(min_length=1, max_length=120)
    importance: int = Field(default=3, ge=1, le=5)
    evidence: str = ""


class MemoryExtraction(StrictModel):
    candidates: list[MemoryCandidate] = Field(default_factory=list, max_length=2)


class ChatState(TypedDict, total=False):
    conversation_id: int
    user_id: str
    user_message: str
    preview_context: dict[str, Any]
    character: dict[str, Any]
    recent_messages: list[dict[str, Any]]
    relationship: dict[str, Any]
    emotion: dict[str, Any]
    scene: dict[str, Any]
    memories: list[dict[str, Any]]
    behavior_decision: BehaviorDecision | dict[str, Any] | None
    reply_messages: list[dict[str, Any]]
    reply_plan: ReplyPlan | dict[str, Any] | None
    image_decision: ImageDecision | dict[str, Any] | None
    voice_decision: VoiceDecision | dict[str, Any] | None
    tts_result: dict[str, Any] | None
    memory_candidates: list[dict[str, Any]]
    persistence_patch: dict[str, Any] | None
    reply_mode: str
    graph_error: str | None
    llm_attempts: dict[str, int]
    tts_attempts: int
