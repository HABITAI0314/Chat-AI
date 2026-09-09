import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db.models import Character, utcnow
from app.db.session import init_db, session_factory

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "characters.seed.json"


def load_seed_characters() -> list[dict[str, Any]]:
    return json.loads(SEED_FILE.read_text(encoding="utf-8"))


async def seed_demo_characters() -> None:
    """Create initial characters without overwriting admin-managed profiles."""
    async with session_factory() as session:
        for item in load_seed_characters():
            result = await session.execute(
                select(Character).where(Character.code == item["code"])
            )
            character = result.scalar_one_or_none()
            if character is not None:
                continue

            character = Character(
                code=item["code"],
                name=item["name"],
                avatar_path=item["avatar_path"],
                profile_json=item["profile_json"],
                draft_profile_json=None,
                profile_version=1,
                config_status="published",
                published_at=utcnow(),
                is_active=True,
            )
            session.add(character)
        await session.commit()


async def main() -> None:
    await init_db()
    await seed_demo_characters()
    print("Demo characters seeded without overwriting existing configuration.")


if __name__ == "__main__":
    asyncio.run(main())
