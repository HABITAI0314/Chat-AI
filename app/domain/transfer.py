from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal, TypedDict

TransferStatus = Literal["accepted", "returned"]


class TransferDecision(TypedDict):
    status: TransferStatus
    reason: str
    reply: str
    relationship_delta: dict[str, int]


def format_transfer_amount(amount_cents: int) -> str:
    """Format virtual money without exposing floating-point rounding to callers."""
    amount = Decimal(amount_cents) / Decimal(100)
    return f"¥{amount:.2f}"


def _as_int(value: Any, fallback: int = 0) -> int:
    if isinstance(value, bool):
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _policy_from_personality(profile: dict[str, Any]) -> dict[str, Any]:
    """Provide a stable, conservative default for older profiles without a policy."""
    personality = {str(item).strip() for item in profile.get("personality", [])}
    if personality & {"克制", "有边界", "慢熟", "谨慎"}:
        return {
            "mode": "return",
            "return_reply": "不用转给我，心意我知道了，钱退给你。",
        }
    if personality & {"热情", "大方", "外向"}:
        return {
            "mode": "conditional",
            "min_familiarity": 0,
            "min_trust": 0,
            "max_accept_amount_cents": 20000,
            "accept_reply": "那我就先收下啦，谢谢你。",
            "return_reply": "不用给我转这么多，心意收到了，钱退给你。",
        }
    return {
        "mode": "conditional",
        "min_familiarity": 30,
        "min_trust": 20,
        "max_accept_amount_cents": 20000,
        "accept_reply": "那我先收下，谢谢你。",
        "return_reply": "不用转给我，真的不用。",
    }


def resolve_transfer(
    profile: dict[str, Any],
    relationship: dict[str, Any],
    amount_cents: int,
) -> TransferDecision:
    """Resolve a simulated transfer using published character policy and relationship state."""
    configured = profile.get("transfer_policy")
    policy = dict(configured) if isinstance(configured, dict) else _policy_from_personality(profile)
    if policy.get("enabled", True) is False:
        return {
            "status": "returned",
            "reason": "transfer_disabled",
            "reply": str(policy.get("return_reply") or "这个不用转给我，退回给你。"),
            "relationship_delta": {"familiarity": 1, "trust": 0, "affection": 0, "annoyance": 0},
        }

    mode = str(policy.get("mode", "conditional"))
    if mode not in {"accept", "return", "conditional"}:
        mode = "conditional"

    familiarity = _as_int(relationship.get("familiarity"))
    trust = _as_int(relationship.get("trust"))
    min_familiarity = _as_int(policy.get("min_familiarity"))
    min_trust = _as_int(policy.get("min_trust"))
    max_amount = _as_int(policy.get("max_accept_amount_cents"), 20000)

    accepted = mode == "accept" and amount_cents <= max_amount
    reason = "policy_accept"
    if mode == "accept" and not accepted:
        reason = "amount_threshold"
    if mode == "return":
        accepted = False
        reason = "policy_return"
    elif mode == "conditional":
        accepted = (
            familiarity >= min_familiarity
            and trust >= min_trust
            and amount_cents <= max_amount
        )
        if not accepted:
            reason = "relationship_or_amount_threshold"

    if accepted:
        return {
            "status": "accepted",
            "reason": reason,
            "reply": str(policy.get("accept_reply") or "那我就收下啦，谢谢你。"),
            "relationship_delta": {"familiarity": 1, "trust": 2, "affection": 1, "annoyance": 0},
        }
    return {
        "status": "returned",
        "reason": reason,
        "reply": str(policy.get("return_reply") or "不用转给我，心意我收到了，钱退给你。"),
        "relationship_delta": {"familiarity": 1, "trust": 0, "affection": 0, "annoyance": 0},
    }
