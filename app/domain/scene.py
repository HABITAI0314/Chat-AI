from datetime import UTC, datetime
from typing import Any

SCENE_ORDER = ("first_meet", "familiar", "daily", "plot")


def judge_scene(
    scene: dict[str, Any],
    relationship: dict[str, Any],
    behavior: dict[str, Any],
) -> dict[str, Any]:
    result = dict(scene)
    current = result.get("current", "first_meet")
    action = behavior.get("scene_action", "keep")
    turn_count = int(result.get("turn_count", 0)) + 1
    familiarity = int(relationship.get("familiarity", 0))
    trust = int(relationship.get("trust", 0))
    affection = int(relationship.get("affection", 0))
    next_scene = current
    reason = "keep"

    if current == "first_meet" and (
        action == "enter_familiar" or (turn_count >= 3 and familiarity >= 25)
    ):
        next_scene = "familiar"
        reason = "初识互动达到熟悉阈值"
    elif current == "familiar" and (
        action == "enter_daily" or (trust >= 40 or affection >= 45)
    ):
        next_scene = "daily"
        reason = "关系达到日常聊天阈值"
    elif current == "daily" and action == "advance_plot":
        next_scene = "plot"
        reason = "角色或用户触发特定剧情"
    elif current == "plot" and action == "end_plot":
        next_scene = "daily"
        reason = "特定剧情结束"

    result.update(
        {
            "current": next_scene,
            "turn_count": turn_count,
            "last_transition_reason": reason,
            "updated_at": datetime.now(UTC).isoformat(),
        }
    )
    return result
