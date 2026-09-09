from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "dev"
    database_url: str = "sqlite+aiosqlite:///./data/chat.db"
    admin_token: str = ""

    openai_base_url: str = ""
    openai_api_key: str = ""
    openai_model: str = "your-chat-model"
    llm_enabled: bool = False
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2

    # TTS 默认按 YQ 项目使用的豆包双向流式接口配置。为了方便切换，
    # 同一组字段也兼容较短的 TTS_* 环境变量名。
    tts_provider: str = "doubao_bidirection"
    tts_enabled: bool = Field(default=False, validation_alias=AliasChoices("TTS_ENABLED"))
    doubao_tts_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "DOUBAO_BIDIRECTION_TTS_ENABLED",
            "DOUBAO_TTS_ENABLED",
        ),
    )
    tts_websocket_url: str = Field(
        default="wss://openspeech.bytedance.com/api/v3/tts/bidirection",
        validation_alias=AliasChoices(
            "TTS_WEBSOCKET_URL",
            "DOUBAO_BIDIRECTION_TTS_WEBSOCKET_URL",
        ),
    )
    tts_app_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "TTS_APP_ID",
            "DOUBAO_BIDIRECTION_TTS_APP_ID",
        ),
    )
    tts_resource_id: str = Field(
        default="seed-tts-2.0",
        validation_alias=AliasChoices(
            "TTS_RESOURCE_ID",
            "DOUBAO_BIDIRECTION_TTS_RESOURCE_ID",
        ),
    )
    tts_output_format: str = Field(
        default="pcm",
        validation_alias=AliasChoices(
            "TTS_OUTPUT_FORMAT",
            "DOUBAO_BIDIRECTION_TTS_OUTPUT_FORMAT",
        ),
    )
    tts_output_sample_rate: int = Field(
        default=24000,
        validation_alias=AliasChoices(
            "TTS_OUTPUT_SAMPLE_RATE",
            "DOUBAO_BIDIRECTION_TTS_OUTPUT_SAMPLE_RATE",
        ),
    )
    tts_connect_timeout_seconds: float = Field(
        default=10.0,
        validation_alias=AliasChoices(
            "TTS_CONNECT_TIMEOUT_SECONDS",
            "DOUBAO_BIDIRECTION_TTS_CONNECT_TIMEOUT_SECONDS",
        ),
    )
    tts_base_url: str = ""
    tts_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "TTS_API_KEY",
            "DOUBAO_BIDIRECTION_TTS_API_KEY",
        ),
    )
    tts_max_retries: int = 2
    tts_model: str = "your-tts-model"
    tts_speaker: str = Field(
        default="zh_female_shuangkuaisisi_uranus_bigtts",
        validation_alias=AliasChoices(
            "DOUBAO_BIDIRECTION_TTS_SPEAKER",
            "TTS_SPEAKER",
        ),
    )
    tts_default_voice: str = "fictional-default"
    tts_format: str = "mp3"
    tts_max_chars: int = 180
    tts_timeout_seconds: float = 20.0

    demo_user_id: str = "demo-user"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def static_dir(self) -> Path:
        return ROOT_DIR / "app" / "static"

    @property
    def audio_dir(self) -> Path:
        return ROOT_DIR / "data" / "audio"

    @property
    def resolved_tts_base_url(self) -> str:
        return (self.tts_base_url or self.openai_base_url).rstrip("/")

    @property
    def resolved_tts_api_key(self) -> str:
        return self.tts_api_key or self.openai_api_key

    @property
    def tts_enabled_effective(self) -> bool:
        return self.tts_enabled or self.doubao_tts_enabled


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
