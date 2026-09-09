from typing import Any

from pydantic import BaseModel, Field


class CharacterSummary(BaseModel):
    id: int
    code: str
    name: str
    description: str
    avatar_url: str
    is_virtual: bool = True


class AdminCharacterSummary(CharacterSummary):
    is_active: bool
    config_status: str
    has_draft: bool = False
    profile_version: int
    updated_at: str


class AdminCharacterDetail(AdminCharacterSummary):
    avatar_path: str
    profile: dict[str, Any] = Field(default_factory=dict)
    draft_profile: dict[str, Any] = Field(default_factory=dict)
    published_profile: dict[str, Any] = Field(default_factory=dict)
    published_at: str | None = None


class CharacterDraftRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=100)
    avatar_path: str = Field(min_length=1, max_length=255)
    profile: dict[str, Any] = Field(default_factory=dict)


class CharacterCreateRequest(CharacterDraftRequest):
    pass


class CharacterActiveRequest(BaseModel):
    is_active: bool


class LLMConfigRequest(BaseModel):
    enabled: bool = True
    base_url: str = Field(default="", max_length=500)
    model: str = Field(default="", max_length=100)
    api_key: str = Field(default="", max_length=500)


class LLMConfigResponse(BaseModel):
    enabled: bool
    base_url: str
    model: str
    has_api_key: bool
    api_key_masked: str


class TTSConfigRequest(BaseModel):
    enabled: bool = False
    provider: str = "doubao_bidirection"
    base_url: str = Field(default="", max_length=500)
    model: str = Field(default="", max_length=100)
    api_key: str = Field(default="", max_length=500)
    speaker: str = Field(default="", max_length=200)
    websocket_url: str = Field(default="", max_length=500)
    app_id: str = Field(default="", max_length=200)
    resource_id: str = Field(default="", max_length=200)
    output_format: str = Field(default="pcm", max_length=20)
    output_sample_rate: int = Field(default=24000, ge=8000, le=48000)
    output_file_format: str = Field(default="mp3", max_length=20)
    max_retries: int = Field(default=2, ge=0, le=3)
    max_chars: int = Field(default=180, ge=1, le=500)
    timeout_seconds: float = Field(default=20, ge=1, le=120)
    connect_timeout_seconds: float = Field(default=10, ge=1, le=60)


class TTSConfigResponse(BaseModel):
    enabled: bool
    provider: str
    base_url: str
    model: str
    has_api_key: bool
    api_key_masked: str
    speaker: str
    websocket_url: str
    app_id: str
    resource_id: str
    output_format: str
    output_sample_rate: int
    output_file_format: str
    max_retries: int
    max_chars: int
    timeout_seconds: float
    connect_timeout_seconds: float


class PromptBundle(BaseModel):
    behavior_system: str = Field(min_length=1)
    behavior_user: str = Field(min_length=1)
    reply_system: str = Field(min_length=1)
    reply_user: str = Field(min_length=1)
    memory_system: str = Field(min_length=1)
    memory_user: str = Field(min_length=1)


class PromptVersionCreateRequest(BaseModel):
    name: str = Field(default="新版本", min_length=1, max_length=100)
    prompts: PromptBundle
    activate: bool = True


class PromptVersionSummary(BaseModel):
    version: int
    name: str
    created_at: str

class PromptConfigResponse(BaseModel):
    active_version: int
    selected_version: int
    versions: list[PromptVersionSummary]
    prompts: PromptBundle


class ValidationIssue(BaseModel):
    path: str
    message: str
    level: str = "error"


class CharacterValidationResponse(BaseModel):
    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)


class AdminPreviewRequest(BaseModel):
    profile: dict[str, Any] = Field(default_factory=dict)
    name: str = Field(default="测试角色", min_length=1, max_length=100)
    avatar_url: str = ""
    user_message: str = Field(min_length=1, max_length=2000)
    recent_messages: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    relationship: dict[str, Any] = Field(default_factory=dict)
    emotion: dict[str, Any] = Field(default_factory=dict)
    scene: dict[str, Any] = Field(default_factory=dict)
    memories: list[dict[str, Any]] = Field(default_factory=list, max_length=10)


class ConversationCreateRequest(BaseModel):
    user_id: str = Field(default="demo-user", min_length=1, max_length=128)
    character_id: int


class ConversationResponse(BaseModel):
    id: int
    user_id: str
    character: CharacterSummary
    relationship: dict[str, Any]
    emotion: dict[str, Any]
    scene: dict[str, Any]


class MessageResponse(BaseModel):
    id: int
    role: str
    message_type: str
    content: str | None = None
    image_url: str | None = None
    audio_url: str | None = None
    audio_duration_ms: int | None = None
    transcript: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    delay_ms: int = 0


class HistoryResponse(BaseModel):
    conversation: ConversationResponse
    messages: list[MessageResponse]


class MemoryResponse(BaseModel):
    id: int
    memory_type: str
    content: str
    importance: int
    created_at: str


class ChatRequest(BaseModel):
    user_id: str = Field(default="demo-user", min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=2000)


class ChatStateResponse(BaseModel):
    relationship: dict[str, Any]
    emotion: dict[str, Any]
    scene: dict[str, Any]


class ChatResponse(BaseModel):
    user_message: MessageResponse
    assistant_messages: list[MessageResponse]
    state: ChatStateResponse


class AdminPreviewResponse(BaseModel):
    assistant_messages: list[MessageResponse]
    state: ChatStateResponse
    debug: dict[str, Any] = Field(default_factory=dict)
