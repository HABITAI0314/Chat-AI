from datetime import UTC, datetime, timedelta

from app.domain.emotion import decay_emotion
from app.domain.relationship import apply_relationship_delta
from app.domain.scene import judge_scene


def test_relationship_delta_is_clamped_and_turn_count_increments():
    result = apply_relationship_delta(
        {
            "familiarity": 99,
            "trust": 0,
            "affection": 5,
            "annoyance": 98,
            "turn_count": 4,
        },
        {
            "familiarity": 10,
            "trust": -5,
            "affection": 2,
            "annoyance": 10,
        },
    )
    assert result == {
        "familiarity": 100,
        "trust": 0,
        "affection": 7,
        "annoyance": 100,
        "turn_count": 5,
    }


def test_emotion_decays_without_resetting_to_default():
    old = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    result = decay_emotion(
        {"dominant": "happy", "intensity": 80, "valence": 70, "updated_at": old}
    )
    assert result["dominant"] == "happy"
    assert result["intensity"] < 80
    assert result["valence"] < 70


def test_scene_moves_forward_only_when_threshold_is_met():
    result = judge_scene(
        {"current": "first_meet", "turn_count": 2},
        {"familiarity": 25, "trust": 10, "affection": 10},
        {"scene_action": "keep"},
    )
    assert result["current"] == "familiar"
