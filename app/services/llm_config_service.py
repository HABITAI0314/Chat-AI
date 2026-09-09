import json
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

from app.config import ROOT_DIR, settings


@dataclass(slots=True)
class LLMRuntimeConfig:
    enabled: bool
    base_url: str
    api_key: str
    model: str


@dataclass(slots=True)
class TTSRuntimeConfig:
    provider: str
    enabled: bool
    base_url: str
    api_key: str
    model: str
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

    @property
    def tts_provider(self) -> str:
        return self.provider

    @property
    def tts_enabled_effective(self) -> bool:
        return self.enabled

    @property
    def tts_base_url(self) -> str:
        return self.base_url

    @property
    def tts_api_key(self) -> str:
        return self.api_key

    @property
    def tts_model(self) -> str:
        return self.model

    @property
    def tts_speaker(self) -> str:
        return self.speaker

    @property
    def tts_websocket_url(self) -> str:
        return self.websocket_url

    @property
    def tts_app_id(self) -> str:
        return self.app_id

    @property
    def tts_resource_id(self) -> str:
        return self.resource_id

    @property
    def tts_output_format(self) -> str:
        return self.output_format

    @property
    def tts_output_sample_rate(self) -> int:
        return self.output_sample_rate

    @property
    def tts_format(self) -> str:
        return self.output_file_format

    @property
    def tts_max_retries(self) -> int:
        return self.max_retries

    @property
    def tts_max_chars(self) -> int:
        return self.max_chars

    @property
    def tts_timeout_seconds(self) -> float:
        return self.timeout_seconds

    @property
    def tts_connect_timeout_seconds(self) -> float:
        return self.connect_timeout_seconds

    @property
    def resolved_tts_base_url(self) -> str:
        return self.base_url.rstrip("/")

    @property
    def resolved_tts_api_key(self) -> str:
        return self.api_key


class LLMConfigService:
    def __init__(self, path: Path | None = None):
        self.path = path or ROOT_DIR / "data" / "llm-config.json"

    def runtime_config(self) -> LLMRuntimeConfig:
        fallback = LLMRuntimeConfig(
            enabled=settings.llm_enabled,
            base_url=settings.openai_base_url.rstrip("/"),
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
        if not self.path.exists():
            return fallback
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return LLMRuntimeConfig(
                enabled=bool(payload.get("enabled", fallback.enabled)),
                base_url=str(payload.get("base_url", fallback.base_url)).strip().rstrip("/"),
                api_key=str(payload.get("api_key", fallback.api_key)).strip(),
                model=str(payload.get("model", fallback.model)).strip(),
            )
        except (OSError, ValueError, TypeError):
            return fallback

    def public_config(self) -> dict[str, object]:
        config = self.runtime_config()
        key = config.api_key
        if len(key) >= 8:
            masked = f"{key[:3]}••••{key[-4:]}"
        elif key:
            masked = "••••••••"
        else:
            masked = ""
        return {
            "enabled": config.enabled,
            "base_url": config.base_url,
            "model": config.model,
            "has_api_key": bool(key),
            "api_key_masked": masked,
        }

    def save(
        self,
        *,
        enabled: bool,
        base_url: str,
        model: str,
        api_key: str,
    ) -> dict[str, object]:
        base_url = base_url.strip().rstrip("/")
        model = model.strip()
        parsed = urlparse(base_url)
        if enabled and (parsed.scheme not in {"http", "https"} or not parsed.netloc):
            raise ValueError("llm_base_url_invalid")
        if enabled and not model:
            raise ValueError("llm_model_required")

        current = self.runtime_config()
        resolved_key = api_key.strip() or current.api_key
        if enabled and not resolved_key:
            raise ValueError("llm_api_key_required")
        config = LLMRuntimeConfig(
            enabled=enabled,
            base_url=base_url,
            api_key=resolved_key,
            model=model,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(asdict(config), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
        return self.public_config()


llm_config_service = LLMConfigService()


class TTSConfigService:
    def __init__(self, path: Path | None = None):
        self.path = path or ROOT_DIR / "data" / "tts-config.json"

    @staticmethod
    def _fallback() -> TTSRuntimeConfig:
        return TTSRuntimeConfig(
            provider=settings.tts_provider,
            enabled=settings.tts_enabled_effective,
            base_url=settings.resolved_tts_base_url,
            api_key=settings.resolved_tts_api_key,
            model=settings.tts_model,
            speaker=settings.tts_speaker,
            websocket_url=settings.tts_websocket_url,
            app_id=settings.tts_app_id,
            resource_id=settings.tts_resource_id,
            output_format=settings.tts_output_format,
            output_sample_rate=settings.tts_output_sample_rate,
            output_file_format=settings.tts_format,
            max_retries=settings.tts_max_retries,
            max_chars=settings.tts_max_chars,
            timeout_seconds=settings.tts_timeout_seconds,
            connect_timeout_seconds=settings.tts_connect_timeout_seconds,
        )

    def runtime_config(self) -> TTSRuntimeConfig:
        fallback = self._fallback()
        if not self.path.exists():
            return fallback
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            values = asdict(fallback)
            values.update({key: value for key, value in payload.items() if key in values})
            return TTSRuntimeConfig(**values)
        except (OSError, ValueError, TypeError):
            return fallback

    def public_config(self) -> dict[str, object]:
        config = self.runtime_config()
        key = config.api_key
        masked = f"{key[:3]}••••{key[-4:]}" if len(key) >= 8 else ("••••••••" if key else "")
        payload = asdict(config)
        payload.pop("api_key")
        payload.update({"has_api_key": bool(key), "api_key_masked": masked})
        return payload

    def save(self, payload: dict[str, object]) -> dict[str, object]:
        current = self.runtime_config()
        values = asdict(current)
        values.update({key: value for key, value in payload.items() if key in values})
        api_key = str(payload.get("api_key", "")).strip()
        values["api_key"] = api_key or current.api_key
        for key in (
            "provider",
            "base_url",
            "model",
            "speaker",
            "websocket_url",
            "app_id",
            "resource_id",
            "output_format",
            "output_file_format",
        ):
            values[key] = str(values[key]).strip()
        values["base_url"] = values["base_url"].rstrip("/")
        config = TTSRuntimeConfig(**values)

        providers = {
            "doubao",
            "doubao_bidirection",
            "doubao_bidirectional",
            "volcengine",
            "openai",
            "openai_compatible",
        }
        if config.provider not in providers:
            raise ValueError("tts_provider_invalid")
        if config.enabled and not config.api_key:
            raise ValueError("tts_api_key_required")
        if config.enabled and config.provider in {
            "doubao",
            "doubao_bidirection",
            "doubao_bidirectional",
            "volcengine",
        }:
            parsed = urlparse(config.websocket_url)
            if parsed.scheme not in {"ws", "wss"} or not parsed.netloc:
                raise ValueError("tts_websocket_url_invalid")
            if not config.app_id or not config.resource_id or not config.speaker:
                raise ValueError("tts_doubao_fields_required")
        if config.enabled and config.provider in {"openai", "openai_compatible"}:
            parsed = urlparse(config.base_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("tts_base_url_invalid")
            if not config.model or not config.speaker:
                raise ValueError("tts_model_and_voice_required")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(asdict(config), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
        return self.public_config()


tts_config_service = TTSConfigService()
