from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.admin_characters import router as admin_character_router
from app.api.admin_settings import router as admin_settings_router
from app.api.characters import router as character_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversation_router
from app.config import settings
from app.db.repositories import Repository
from app.db.session import close_db, init_db, session_factory
from app.seed import seed_demo_characters
from app.services.character_admin_service import CharacterAdminService
from app.services.chat_service import ChatService


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_demo_characters()
    repository = Repository(session_factory)
    app.state.chat_service = ChatService(repository)
    app.state.character_admin_service = CharacterAdminService(repository)
    yield
    await close_db()


app = FastAPI(
    title="Virtual Character Chat Demo",
    description="LangGraph-driven 1v1 fictional character chat demo.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static/audio", StaticFiles(directory=settings.audio_dir), name="generated-audio")
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
app.include_router(character_router)
app.include_router(admin_character_router)
app.include_router(admin_settings_router)
app.include_router(conversation_router)
app.include_router(chat_router)


@app.get("/healthz")
async def healthz():
    from app.services.llm_service import LLMService
    from app.services.tts_service import TTSService

    return {
        "status": "ok",
        "llm_enabled": LLMService().enabled,
        "tts_enabled": TTSService().enabled,
    }
