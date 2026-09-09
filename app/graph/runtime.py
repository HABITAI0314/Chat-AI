from dataclasses import dataclass

from app.db.repositories import Repository
from app.services.asset_service import AssetResolver
from app.services.llm_service import LLMService
from app.services.tts_service import TTSService


@dataclass(slots=True)
class GraphRuntime:
    repository: Repository
    llm: LLMService
    tts: TTSService
    assets: AssetResolver
