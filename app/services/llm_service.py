import asyncio
import logging
from typing import Any, TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.config import settings
from app.services.llm_config_service import llm_config_service

logger = logging.getLogger(__name__)
SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMUnavailableError(RuntimeError):
    pass


class LLMService:
    def __init__(self):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        config = llm_config_service.runtime_config()
        return bool(
            config.enabled
            and config.base_url
            and config.api_key
            and config.model
        )

    async def invoke_structured(
        self,
        schema: type[SchemaT],
        *,
        system_prompt: str,
        user_prompt: str,
        purpose: str,
    ) -> SchemaT:
        if not self.enabled:
            raise LLMUnavailableError("llm_disabled_or_not_configured")

        config = llm_config_service.runtime_config()
        model_kwargs: dict[str, Any] = {
            "model": config.model,
            "api_key": config.api_key,
            "base_url": config.base_url,
            "temperature": 0.85,
            "timeout": self.settings.llm_timeout_seconds,
            "max_retries": 0,
        }

        model_lower = config.model.lower()
        base_url_lower = config.base_url.lower()
        if any(keyword in model_lower for keyword in ("qwen", "qwq")) or "aliyuncs.com" in base_url_lower:
            model_kwargs["extra_body"] = {"enable_thinking": False}
        model = ChatOpenAI(**model_kwargs)
        structured_model = model.with_structured_output(schema, method="function_calling")
        attempts = max(1, self.settings.llm_max_retries + 1)
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                result = await structured_model.ainvoke(
                    [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=user_prompt),
                    ]
                )
                if isinstance(result, schema):
                    return result
                return schema.model_validate(result)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "structured llm call failed purpose=%s attempt=%s/%s error=%s: %s",
                    purpose,
                    attempt,
                    attempts,
                    type(exc).__name__,
                    exc,
                )
                if attempt < attempts:
                    await asyncio.sleep(0.3 if attempt == 1 else 0.8)
        raise LLMUnavailableError(f"structured_call_failed:{purpose}") from last_error
