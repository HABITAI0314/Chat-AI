import re
from pathlib import Path

from app.config import settings

SAFE_ASSET_ID = re.compile(r"^[a-zA-Z0-9_-]+$")
IMAGE_SUFFIXES = (".svg", ".png", ".jpg", ".jpeg", ".webp")


class AssetResolver:
    def __init__(self, static_dir: Path | None = None):
        self.static_dir = static_dir or settings.static_dir

    def resolve_character_asset(
        self, character_code: str, asset_id: str | None, *, kind: str
    ) -> str | None:
        if not asset_id or not SAFE_ASSET_ID.fullmatch(asset_id):
            return None
        if not SAFE_ASSET_ID.fullmatch(character_code):
            return None
        folder = self.static_dir / "characters" / character_code
        if kind == "photo":
            folder = folder / "photos"
        for suffix in IMAGE_SUFFIXES:
            candidate = folder / f"{asset_id}{suffix}"
            if candidate.is_file():
                relative = candidate.relative_to(self.static_dir).as_posix()
                return f"/static/{relative}"
        return None
