from typing import Any

RELATIONSHIP_KEYS = ("familiarity", "trust", "affection", "annoyance")


def clamp(value: int | float, minimum: int = 0, maximum: int = 100) -> int:
    return max(minimum, min(maximum, int(round(value))))


def apply_relationship_delta(
    relationship: dict[str, Any],
    delta: dict[str, int] | None,
) -> dict[str, Any]:
    result = {key: clamp(relationship.get(key, 0)) for key in RELATIONSHIP_KEYS}
    for key in RELATIONSHIP_KEYS:
        result[key] = clamp(result[key] + int((delta or {}).get(key, 0)))
    result["turn_count"] = int(relationship.get("turn_count", 0)) + 1
    return result
