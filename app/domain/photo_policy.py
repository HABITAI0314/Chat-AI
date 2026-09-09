import re
from typing import Any

PHOTO_PATTERN = re.compile(r"(照片|自拍|图片|发一张|看看你|长什么样|照片吗)")


def is_photo_request(text: str) -> bool:
    return bool(PHOTO_PATTERN.search(text or ""))


def choose_photo(
    *,
    profile: dict[str, Any],
    relationship: dict[str, Any],
    scene: dict[str, Any],
    behavior: dict[str, Any],
    asset_resolver: Any,
) -> dict[str, Any]:
    if not is_photo_request(behavior.get("_user_message", "")):
        return {"outcome": "none", "asset_id": None, "image_url": None, "reason": "not_photo"}

    policy = profile.get("photo_policy", {})
    if not policy.get("enabled", True):
        return {"outcome": "decline", "asset_id": None, "image_url": None, "reason": "disabled"}

    assets = policy.get("assets", [])
    if not assets:
        return {"outcome": "delay", "asset_id": None, "image_url": None, "reason": "no_asset"}

    min_familiarity = int(policy.get("min_familiarity", 0))
    min_trust = int(policy.get("min_trust", 0))
    current_scene = scene.get("current", "first_meet")
    meets_threshold = (
        int(relationship.get("familiarity", 0)) >= min_familiarity
        and int(relationship.get("trust", 0)) >= min_trust
    )
    if current_scene == "first_meet" and not meets_threshold:
        return {
            "outcome": policy.get("early_outcome", "delay"),
            "asset_id": None,
            "image_url": None,
            "reason": "relationship_not_ready",
        }

    if not behavior.get("should_send_image", False) and not policy.get(
        "send_on_explicit_request", True
    ):
        return {
            "outcome": "delay",
            "asset_id": None,
            "image_url": None,
            "reason": "character_choice",
        }

    asset_id = assets[0] if isinstance(assets[0], str) else assets[0].get("id")
    image_url = asset_resolver.resolve_character_asset(
        profile.get("code", "unknown"), asset_id, kind="photo"
    )
    if image_url is None:
        return {"outcome": "delay", "asset_id": None, "image_url": None, "reason": "asset_missing"}
    return {
        "outcome": "send",
        "asset_id": asset_id,
        "image_url": image_url,
        "reason": "policy_allowed",
    }
