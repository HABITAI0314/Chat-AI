from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.base import Base

engine = create_async_engine(settings.database_url, echo=False, future=True)
session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    settings.audio_dir.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        if connection.dialect.name == "sqlite":
            result = await connection.execute(text("PRAGMA table_info(characters)"))
            existing_columns = {row[1] for row in result.fetchall()}
            migrations = {
                "draft_code": "VARCHAR(64)",
                "draft_name": "VARCHAR(100)",
                "draft_avatar_path": "VARCHAR(255)",
                "draft_profile_json": "JSON",
                "profile_version": "INTEGER NOT NULL DEFAULT 1",
                "config_status": "VARCHAR(20) NOT NULL DEFAULT 'published'",
                "published_at": "DATETIME",
            }
            for column, definition in migrations.items():
                if column not in existing_columns:
                    await connection.execute(
                        text(f"ALTER TABLE characters ADD COLUMN {column} {definition}")
                    )


async def close_db() -> None:
    await engine.dispose()
