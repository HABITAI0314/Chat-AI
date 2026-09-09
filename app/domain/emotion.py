from datetime import UTC, datetime
from typing import Any

from app.domain.relationship import clamp

EMOTION_VALENCE = {
    "happy": 35,
    "curious": 20,
    "calm": 5,
    "shy": 8,
    "guarded": -5,
    "annoyed": -35,
    "sad": -30,
}


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def decay_emotion(emotion: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(UTC)
    updated_at = _parse_datetime(emotion.get("updated_at"))
    if updated_at is None:
        updated_at = now
    elapsed_minutes = max(0, int((now - updated_at).total_seconds() // 60))
    decay_steps = elapsed_minutes // 30
    intensity = clamp(int(emotion.get("intensity", 35)) - decay_steps * 3)
    valence = int(emotion.get("valence", 0))
    if decay_steps:
        valence = int(valence * max(0.0, 1 - min(decay_steps * 0.08, 0.8)))
    result = dict(emotion)
    result["intensity"] = intensity
    result["valence"] = max(-100, min(100, valence))
    result["updated_at"] = now.isoformat()
    return result


def apply_emotion_signal(
    emotion: dict[str, Any],
    signal: dict[str, Any] | None,
) -> dict[str, Any]:
    result = decay_emotion(emotion)
    if signal:
        target = signal.get("target") or result.get("dominant", "calm")
        result["dominant"] = target
        result["intensity"] = clamp(
            int(result.get("intensity", 35)) + int(signal.get("intensity_delta", 0))
        )
        target_valence = EMOTION_VALENCE.get(target, 0)
        result["valence"] = max(
            -100,
            min(100, int((int(result.get("valence", 0)) * 0.65) + (target_valence * 0.35))),
        )
    result["updated_at"] = datetime.now(UTC).isoformat()
    return result
