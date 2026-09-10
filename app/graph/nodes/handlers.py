import json
import logging
import re
from typing import Any

from app.config import settings
from app.domain.emotion import apply_emotion_signal, decay_emotion
from app.domain.photo_policy import choose_photo, is_photo_request
from app.domain.relationship import apply_relationship_delta
from app.domain.scene import judge_scene
from app.graph.runtime import GraphRuntime
from app.graph.schemas import (
    BehaviorDecision,
    ChatState,
    ImageDecision,
    MemoryExtraction,
    ReplyPlan,
    TextReply,
    VoiceDecision,
)
from app.services.llm_service import LLMUnavailableError
from app.services.prompt_config_service import prompt_config_service
from app.services.tts_service import TTSUnavailableError

logger = logging.getLogger(__name__)


def _model_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return dict(value)


def _profile(state: ChatState) -> dict[str, Any]:
    return state.get("character", {}).get("profile", {})


def _conversation_text(state: ChatState) -> str:
    lines = []
    for message in state.get("recent_messages", []):
        content = message.get("content")
        if content:
            lines.append(f'{message.get("role", "unknown")}: {content}')
    return "\n".join(lines[-20:])


async def load_context_node(runtime: GraphRuntime, state: ChatState) -> dict[str, Any]:
    preview_context = state.get("preview_context")
    if preview_context:
        profile = dict(preview_context.get("profile", {}))
        name = str(preview_context.get("name") or profile.get("name") or "测试角色")
        code = str(preview_context.get("code") or profile.get("code") or "preview")
        return {
            "character": {
                "id": int(preview_context.get("character_id", 0)),
                "code": code,
                "name": name,
                "avatar_url": str(preview_context.get("avatar_url", "")),
                "profile": profile,
            },
            "recent_messages": list(preview_context.get("recent_messages", []))[-20:],
            "memories": list(preview_context.get("memories", []))[-10:],
            "relationship": dict(preview_context.get("relationship", {})),
            "emotion": decay_emotion(dict(preview_context.get("emotion", {}))),
            "scene": dict(preview_context.get("scene", {})),
            "llm_attempts": {},
            "graph_error": None,
        }
    bundle = await runtime.repository.load_context(
        int(state["conversation_id"]),
        str(state["user_id"]),
    )
    conversation = bundle["conversation"]
    character_model = bundle["character"]
    profile = dict(character_model.profile_json or {})
    profile["code"] = character_model.code
    profile["name"] = character_model.name
    character = {
        "id": character_model.id,
        "code": character_model.code,
        "name": character_model.name,
        "avatar_url": character_model.avatar_path,
        "profile": profile,
    }
    return {
        "character": character,
        "recent_messages": bundle["recent_messages"],
        "memories": bundle["memories"],
        "relationship": dict(conversation.relationship_state or {}),
        "emotion": decay_emotion(dict(conversation.emotion_state or {})),
        "scene": dict(conversation.scene_state or {}),
        "llm_attempts": {},
        "graph_error": None,
    }


def _fallback_behavior(state: ChatState) -> BehaviorDecision:
    text = state.get("user_message", "")
    profile = _profile(state)
    lowered = text.lower()
    if is_photo_request(text):
        return BehaviorDecision(
            intent="request_photo",
            action="normal_reply",
            emotion={"target": "shy", "intensity_delta": 2},
            relationship_delta={"familiarity": 1, "trust": 0, "affection": 0, "annoyance": 0},
            scene_action="keep",
            should_send_image=True,
            should_send_voice=False,
            internal_reason="deterministic_photo_fallback",
        )
    if re.search(r"(语音|声音|说句话|发一段)", text):
        return BehaviorDecision(
            intent="request_voice",
            action="normal_reply",
            emotion={"target": "curious", "intensity_delta": 1},
            relationship_delta={"familiarity": 1, "trust": 0, "affection": 0, "annoyance": 0},
            scene_action="keep",
            should_send_image=False,
            should_send_voice=True,
            internal_reason="deterministic_voice_fallback",
        )
    if re.search(r"(你好|嗨|哈喽|在吗|早上好|晚上好)", text):
        intent = "greeting"
    elif re.search(r"(烦|不想聊|算了|无语)", text):
        intent = "complaint"
    else:
        intent = "question" if "?" in text or "？" in text else "other"
    tea_goal = profile.get("goals", {}).get("primary") == "sell_tea"
    advance = tea_goal and bool(re.search(r"(茶|口味|喝什么|买|推荐)", lowered))
    return BehaviorDecision(
        intent=intent,
        action="advance_scene" if advance else "normal_reply",
        emotion={"target": "guarded" if intent == "complaint" else "curious", "intensity_delta": 2},
        relationship_delta={
            "familiarity": 1,
            "trust": -1 if intent == "complaint" else 0,
            "affection": 1 if intent != "complaint" else 0,
            "annoyance": 2 if intent == "complaint" else 0,
        },
        scene_action="advance_plot" if advance else "keep",
        should_send_image=False,
        should_send_voice=False,
        internal_reason="deterministic_demo_fallback",
    )


async def behavior_decision_node(runtime: GraphRuntime, state: ChatState) -> dict[str, Any]:
    profile = _profile(state)
    values = {
        "character_name": state.get("character", {}).get("name", "虚构角色"),
        "profile_json": json.dumps(profile, ensure_ascii=False),
        "relationship_json": json.dumps(state.get("relationship", {}), ensure_ascii=False),
        "emotion_json": json.dumps(state.get("emotion", {}), ensure_ascii=False),
        "scene_json": json.dumps(state.get("scene", {}), ensure_ascii=False),
        "conversation_text": _conversation_text(state),
        "memories_json": json.dumps(state.get("memories", []), ensure_ascii=False),
        "user_message": state.get("user_message", ""),
    }
    system_prompt = prompt_config_service.render("behavior_system", values)
    user_prompt = prompt_config_service.render("behavior_user", values)
    try:
        decision = await runtime.llm.invoke_structured(
            BehaviorDecision,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            purpose="behavior_decision",
        )
    except LLMUnavailableError as exc:
        logger.info("using behavior fallback reason=%s", exc)
        decision = _fallback_behavior(state)
    except Exception:
        logger.exception("behavior decision failed; using fallback")
        decision = _fallback_behavior(state)
    return {"behavior_decision": decision}


def behavior_route(state: ChatState) -> str:
    decision = _model_dict(state.get("behavior_decision"))
    if decision.get("action") == "avoid":
        return "avoid"
    if decision.get("action") == "advance_scene":
        return "advance"
    if decision.get("intent") == "request_photo":
        return "photo_request"
    return "normal"


def prepare_normal_node(state: ChatState) -> dict[str, Any]:
    return {"reply_mode": "normal"}


def prepare_avoid_node(state: ChatState) -> dict[str, Any]:
    return {"reply_mode": "avoid"}


def prepare_advance_node(state: ChatState) -> dict[str, Any]:
    return {"reply_mode": "advance"}


def prepare_photo_node(state: ChatState) -> dict[str, Any]:
    return {"reply_mode": "photo_request"}


def scene_judgment_node(state: ChatState) -> dict[str, Any]:
    decision = _model_dict(state.get("behavior_decision"))
    return {
        "scene": judge_scene(
            dict(state.get("scene", {})),
            dict(state.get("relationship", {})),
            decision,
        )
    }


def _fallback_reply_plan(state: ChatState) -> ReplyPlan:
    profile = _profile(state)
    mode = state.get("reply_mode", "normal")
    text = state.get("user_message", "")
    templates = profile.get("fallback_replies", {})
    if mode == "photo_request":
        return ReplyPlan(
            messages=[
                TextReply(
                    content=templates.get("photo", "照片啊，先不急，等熟一点再说。"),
                    tone="guarded",
                )
            ],
            photo_send_text=templates.get("photo_send", "好吧，给你看一张。"),
            photo_fallback_text=templates.get("photo", "照片啊，先不急，等熟一点再说。"),
            voice_text=templates.get("photo", ""),
        )
    if re.search(r"(语音|声音|说句话|发一段)", text):
        return ReplyPlan(
            messages=[TextReply(content=templates.get("voice", "好呀，等我一下。"), tone="warm")],
            voice_text=templates.get("voice", "好呀，等我一下。"),
        )
    if mode == "avoid":
        content = templates.get("avoid", "这个先不聊，好不好。")
        return ReplyPlan(messages=[TextReply(content=content, tone="guarded")])
    character_name = state.get("character", {}).get("name", "")
    background = str(profile.get("background", "")).strip()
    if re.search(r"(你是ai|你是机器人|你是电脑|你是程序|你是不是真人|是真人吗|是不是ai)", text, re.IGNORECASE):
        return ReplyPlan(
            messages=[
                TextReply(content="大白天说什么胡话呢，我看你才像机器人。", tone="teasing"),
            ]
        )
    if re.search(r"(你是谁|你叫什么|叫什么名字|怎么称呼你|做什么的)", text):
        identity = f"我叫{character_name}。" if character_name else "先叫我现在这个名字吧。"
        if background:
            identity += background.split("，", 1)[0].rstrip("。") + "。"
        return ReplyPlan(messages=[TextReply(content=identity[:80], tone="normal")])
    if re.fullmatch(r"\s*(你好|嗨|哈喽|在吗|早上好|晚上好)[呀啊哦～~！!。.]*\s*", text):
        greetings = {
            "sell_tea": "嗨，我是林晚。你怎么称呼？",
            "observe": f"嗯，我在。叫我{character_name or '沈砚'}就好。",
        }
        goal = str(profile.get("goals", {}).get("primary", ""))
        return ReplyPlan(
            messages=[TextReply(content=greetings.get(goal, "嗨。你怎么称呼？"), tone="normal")]
        )
    if profile.get("goals", {}).get("primary") == "sell_tea" and re.search(
        r"(茶|口味|喝什么|买|推荐)", text
    ):
        return ReplyPlan(
            messages=[
                TextReply(content="你平时喝浓一点还是清一点的？", tone="sales_script"),
                TextReply(
                    content="我可以按你的口味挑，不会乱推荐。",
                    delay_ms=650,
                    tone="sales_script",
                ),
            ],
            voice_text="你平时喝浓一点还是清一点的？我可以按你的口味挑，不会乱推荐。",
        )
    emotion = state.get("emotion", {}).get("dominant", "calm")
    candidates = {
        "happy": "今天心情还不错，你呢？",
        "shy": "你突然这么问，我有点不知道怎么接。",
        "guarded": "嗯，先这样聊着吧。",
        "annoyed": "你别一直追着问嘛。",
        "sad": "没什么，就是有点累。",
        "curious": "你怎么突然想到问这个？",
        "calm": "我在呢，慢慢说。",
    }
    return ReplyPlan(messages=[TextReply(content=candidates.get(emotion, "我在呢。"))])


async def reply_generation_node(runtime: GraphRuntime, state: ChatState) -> dict[str, Any]:
    profile = _profile(state)
    decision = _model_dict(state.get("behavior_decision"))
    values = {
        "character_name": state.get("character", {}).get("name", "角色"),
        "profile_json": json.dumps(profile, ensure_ascii=False),
        "relationship_json": json.dumps(state.get("relationship", {}), ensure_ascii=False),
        "emotion_json": json.dumps(state.get("emotion", {}), ensure_ascii=False),
        "scene_json": json.dumps(state.get("scene", {}), ensure_ascii=False),
        "decision_json": json.dumps(decision, ensure_ascii=False),
        "conversation_text": _conversation_text(state),
        "memories_json": json.dumps(state.get("memories", []), ensure_ascii=False),
        "user_message": state.get("user_message", ""),
    }
    system_prompt = prompt_config_service.render("reply_system", values)
    user_prompt = prompt_config_service.render("reply_user", values)
    try:
        plan = await runtime.llm.invoke_structured(
            ReplyPlan,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            purpose="reply_generation",
        )
    except Exception as exc:
        logger.info("using reply fallback reason=%s", type(exc).__name__)
        plan = _fallback_reply_plan(state)

    messages = [
        {
            "message_type": "text",
            "content": item.content,
            "delay_ms": item.delay_ms,
            "metadata": {"tone": item.tone},
        }
        for item in plan.messages
    ]
    return {
        "reply_plan": plan,
        "reply_messages": messages,
    }


def image_judgment_node(runtime: GraphRuntime, state: ChatState) -> dict[str, Any]:
    behavior = _model_dict(state.get("behavior_decision"))
    behavior["_user_message"] = state.get("user_message", "")
    result = choose_photo(
        profile=_profile(state),
        relationship=state.get("relationship", {}),
        scene=state.get("scene", {}),
        behavior=behavior,
        asset_resolver=runtime.assets,
    )
    decision = ImageDecision.model_validate(result)
    plan = _model_dict(state.get("reply_plan"))
    reply_messages = list(state.get("reply_messages", []))
    replacement = None
    if decision.outcome == "send":
        replacement = plan.get("photo_send_text") or "好吧，给你看一张。"
    elif decision.outcome in {"decline", "delay"}:
        replacement = plan.get("photo_fallback_text")
    if replacement:
        for message in reply_messages:
            if message.get("message_type") == "text":
                message["content"] = replacement
                break
    return {"image_decision": decision, "reply_messages": reply_messages}


def image_route(state: ChatState) -> str:
    decision = _model_dict(state.get("image_decision"))
    return "send" if decision.get("outcome") == "send" else "no_image"


def append_image_message_node(state: ChatState) -> dict[str, Any]:
    decision = _model_dict(state.get("image_decision"))
    messages = list(state.get("reply_messages", []))
    messages.append(
        {
            "message_type": "image",
            "content": None,
            "image_path": decision.get("image_url"),
            "delay_ms": 650,
            "metadata": {"asset_id": decision.get("asset_id")},
        }
    )
    return {"reply_messages": messages}


def _is_voice_request(text: str) -> bool:
    return bool(re.search(r"(语音|声音|说句话|发一段)", text or ""))


def voice_judgment_node(runtime: GraphRuntime, state: ChatState) -> dict[str, Any]:
    profile = _profile(state)
    policy = profile.get("voice_policy", {})
    behavior = _model_dict(state.get("behavior_decision"))
    explicit_request = _is_voice_request(state.get("user_message", ""))
    enabled = runtime.tts.enabled and not state.get("preview_context")
    policy_mode = policy.get("mode", "on_request")
    wants_voice = bool(behavior.get("should_send_voice")) or explicit_request
    allowed = (
        enabled
        and policy_mode != "never"
        and wants_voice
        and (explicit_request or policy_mode in {"emotional", "occasional"})
    )
    plan = _model_dict(state.get("reply_plan"))
    voice_text = (plan.get("voice_text") or "").strip()
    if not voice_text:
        voice_text = " ".join(
            item.get("content", "")
            for item in state.get("reply_messages", [])
            if item.get("message_type") == "text"
        ).strip()
    if len(voice_text) > settings.tts_max_chars:
        allowed = False
    if not allowed:
        return {
            "voice_decision": VoiceDecision(
                outcome="none",
                reason="voice_policy_or_tts_unavailable",
            )
        }
    return {
        "voice_decision": VoiceDecision(
            outcome="send",
            voice_id=policy.get("voice_id") or settings.tts_default_voice,
            display_mode=policy.get("display_mode", "text_and_audio"),
            text=voice_text,
            reason="voice_allowed",
        )
    }


def voice_route(state: ChatState) -> str:
    decision = _model_dict(state.get("voice_decision"))
    return "send" if decision.get("outcome") == "send" else "no_voice"


async def tts_generation_node(runtime: GraphRuntime, state: ChatState) -> dict[str, Any]:
    decision = _model_dict(state.get("voice_decision"))
    messages = list(state.get("reply_messages", []))
    try:
        result = await runtime.tts.synthesize(
            decision.get("text", ""),
            voice_id=decision.get("voice_id") or settings.tts_default_voice,
            conversation_id=int(state["conversation_id"]),
        )
    except TTSUnavailableError as exc:
        logger.info("tts fallback reason=%s", exc)
        return {"tts_result": {"status": "failed", "reason": str(exc)}}
    if decision.get("display_mode") == "audio_only":
        messages = [item for item in messages if item.get("message_type") != "text"]
    messages.append(
        {
            "message_type": "audio",
            "content": None,
            "audio_path": result["audio_path"],
            "audio_duration_ms": result["audio_duration_ms"],
            "delay_ms": 850,
            "metadata": {
                "transcript": result["transcript"],
                "voice_id": result["voice_id"],
                "display_mode": decision.get("display_mode"),
            },
        }
    )
    return {"tts_result": {"status": "sent", **result}, "reply_messages": messages}


def state_update_node(state: ChatState) -> dict[str, Any]:
    decision = _model_dict(state.get("behavior_decision"))
    relationship = apply_relationship_delta(
        dict(state.get("relationship", {})),
        decision.get("relationship_delta", {}),
    )
    emotion = apply_emotion_signal(
        dict(state.get("emotion", {})),
        decision.get("emotion", {}),
    )
    scene = dict(state.get("scene", {}))
    reply_messages = list(state.get("reply_messages", []))
    if not reply_messages:
        reply_messages = [
            {
                "message_type": "text",
                "content": "我在呢，刚刚有点走神。",
                "delay_ms": 0,
                "metadata": {},
            }
        ]
    for message in reply_messages:
        metadata = dict(message.get("metadata") or {})
        metadata["scene"] = scene.get("current", "first_meet")
        message["metadata"] = metadata
    return {
        "relationship": relationship,
        "emotion": emotion,
        "scene": scene,
        "reply_messages": reply_messages,
        "persistence_patch": {
            "relationship": relationship,
            "emotion": emotion,
            "scene": scene,
        },
    }


def _fallback_memories(state: ChatState) -> list[dict[str, Any]]:
    text = state.get("user_message", "").strip()
    patterns = [
        (r"我喜欢(.{1,30})", "preference"),
        (r"我不喜欢(.{1,30})", "boundary"),
        (r"我最近在(.{1,30})", "experience"),
    ]
    for pattern, memory_type in patterns:
        match = re.search(pattern, text)
        if match:
            return [
                {
                    "type": memory_type,
                    "content": text[:120],
                    "importance": 3,
                    "evidence": "current_turn",
                }
            ]
    return []


async def memory_extraction_node(runtime: GraphRuntime, state: ChatState) -> dict[str, Any]:
    values = {
        "user_message": state.get("user_message", ""),
        "conversation_text": _conversation_text(state),
    }
    system_prompt = prompt_config_service.render("memory_system", values)
    user_prompt = prompt_config_service.render("memory_user", values)
    try:
        extraction = await runtime.llm.invoke_structured(
            MemoryExtraction,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            purpose="memory_extraction",
        )
        candidates = [item.model_dump() for item in extraction.candidates]
    except Exception:
        candidates = _fallback_memories(state)
    return {"memory_candidates": candidates}
