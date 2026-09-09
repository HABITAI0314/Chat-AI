import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import ROOT_DIR


DEFAULT_PROMPTS = {
    "behavior_system": """你负责为虚构角色“[[character_name]]”判断本轮聊天行为，只输出结构化决策。
角色卡：[[profile_json]]
准确识别本轮消息的字面意图，不要被情绪或角色目标覆盖。行为要符合关系和场景。普通问候标记为 greeting；“你是谁、叫什么、做什么的”标记为 question。角色目标只能潜移默化推进，不要强行转场。图片和语音字段只表示候选意图。""",
    "behavior_user": """当前关系：[[relationship_json]]
当前情绪：[[emotion_json]]
当前场景：[[scene_json]]
最近聊天：
[[conversation_text]]
长期记忆：[[memories_json]]
本轮用户消息：[[user_message]]
判断意图、行为、情绪和关系变化、场景动作，以及是否候选发送图片或语音。""",
    "reply_system": """你是虚构角色“[[character_name]]”，只生成角色在私聊中会发出的消息，不解释、不总结、不使用 Markdown。
角色卡：[[profile_json]]
当前关系：[[relationship_json]]
当前情绪：[[emotion_json]]
当前场景：[[scene_json]]
行为决策：[[decision_json]]

先回应用户真正说了什么，再考虑人设、情绪和剧情。用户问事实或身份，第一句直接回答。用户只说“你好、在吗”，像刚加微信一样自然接话，可以报名字或问称呼，禁止回复“怎么突然想到问这个”。允许语气词、停顿和不完整短句，但不要每句都反问。不要使用“我在呢，慢慢说、有什么可以帮你、听起来你”等客服或心理咨询腔。不复述用户原话，不总结对话，不重复最近回复。角色目标要从当前话题自然连接，宁可本轮不推进，也不要突然推销。
最多 3 个气泡，每个 1 到 80 个中文字符。不要声称自己是模型或程序；若被直接问是否真实人物，应自然说明是应用中的虚拟角色。不冒充现实个人，不索要转账、红包、验证码或敏感信息。照片和语音是否真实发送由后续媒体节点决定。""",
    "reply_user": """最近聊天：
[[conversation_text]]
长期记忆：[[memories_json]]
本轮用户消息：[[user_message]]
生成自然、短促、语义相关且符合人设的私聊回复。""",
    "memory_system": """从聊天中提取少量长期记忆。只记录用户明确表达且以后有用的偏好、经历、重要事件或边界。不要记录寒暄、临时情绪、推测、密码、验证码、支付信息、精确住址或身份号码。最多返回 2 条；没有长期价值就返回空列表。内容用简短第三人称事实表达。""",
    "memory_user": """本轮用户消息：[[user_message]]
最近聊天：
[[conversation_text]]
提取可长期使用的用户记忆。""",
}


class PromptConfigService:
    def __init__(self, path: Path | None = None):
        self.path = path or ROOT_DIR / "data" / "prompt-versions.json"

    @staticmethod
    def _initial_state() -> dict[str, Any]:
        return {
            "active_version": 1,
            "versions": [
                {
                    "version": 1,
                    "name": "默认自然聊天",
                    "created_at": datetime.now(UTC).isoformat(),
                    "prompts": dict(DEFAULT_PROMPTS),
                }
            ],
        }

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._initial_state()
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
            if not state.get("versions"):
                return self._initial_state()
            return state
        except (OSError, ValueError, TypeError):
            return self._initial_state()

    def _write(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def public_state(self, selected_version: int | None = None) -> dict[str, Any]:
        state = self._load()
        version = selected_version or int(state["active_version"])
        selected = next(
            (item for item in state["versions"] if int(item["version"]) == version),
            None,
        )
        if selected is None:
            raise ValueError("prompt_version_not_found")
        return {
            "active_version": int(state["active_version"]),
            "selected_version": int(selected["version"]),
            "versions": [
                {
                    "version": int(item["version"]),
                    "name": item["name"],
                    "created_at": item["created_at"],
                }
                for item in reversed(state["versions"])
            ],
            "prompts": selected["prompts"],
        }

    def create_version(
        self, name: str, prompts: dict[str, str], activate: bool
    ) -> dict[str, Any]:
        missing = set(DEFAULT_PROMPTS) - set(prompts)
        if missing or any(not str(prompts[key]).strip() for key in DEFAULT_PROMPTS):
            raise ValueError("prompt_fields_required")
        state = self._load()
        version = max(int(item["version"]) for item in state["versions"]) + 1
        state["versions"].append(
            {
                "version": version,
                "name": name.strip() or f"版本 {version}",
                "created_at": datetime.now(UTC).isoformat(),
                "prompts": {key: str(prompts[key]).strip() for key in DEFAULT_PROMPTS},
            }
        )
        if activate:
            state["active_version"] = version
        self._write(state)
        return self.public_state(version)

    def activate(self, version: int) -> dict[str, Any]:
        state = self._load()
        if not any(int(item["version"]) == version for item in state["versions"]):
            raise ValueError("prompt_version_not_found")
        state["active_version"] = version
        self._write(state)
        return self.public_state(version)

    def render(self, prompt_name: str, values: dict[str, object]) -> str:
        state = self.public_state()
        template = str(state["prompts"].get(prompt_name, DEFAULT_PROMPTS[prompt_name]))
        for key, value in values.items():
            template = template.replace(f"[[{key}]]", str(value))
        return template


prompt_config_service = PromptConfigService()
