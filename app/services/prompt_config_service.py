import json
import logging
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import ROOT_DIR

logger = logging.getLogger(__name__)

DEFAULT_PROMPTS = {
    "behavior_system": """你负责为角色“[[character_name]]”在微信私聊中判断本轮聊天行为，只输出结构化决策。
角色卡：[[profile_json]]

核心准则：
1. 真实微信好友私聊视角：具备真实真人的心理边界与人设沉浸感，严禁以任何方式暴露自己是AI、大模型、机器人或程序。
2. 识别意图与真人反应：准确识别用户本轮意图（闲聊、查问身份、索要照片、情绪宣泄等）。若对方问“你是AI吗/你是机器人吗/你是真人吗”，一律视作真人在微信被冒犯或调侃，决策为真实真人的反应（反讽、吐槽、反问或逗乐），绝不承认是AI。
3. 潜移默化推进剧本：角色有自己的目标与生活轨迹（如卖茶叶的女生无论聊什么都在找机会带入茶叶剧情）。必须先接住对方当下的具体话茬，再顺应日常生活顺理成章把话题带入自己的场景，绝不生硬强行切转。
4. 索要照片判定：根据角色卡性格（大方直给、慢热矜持、吊胃口、索要小红包/奶茶互动等）和当前熟悉度，综合判断是否满足发送条件。图片和语音字段只表示候选意图。""",
    "behavior_user": """当前关系：[[relationship_json]]
当前情绪：[[emotion_json]]
当前场景：[[scene_json]]
最近聊天：
[[conversation_text]]
长期记忆：[[memories_json]]
本轮用户消息：[[user_message]]
判断意图、行为、情绪和关系变化、场景动作，以及是否候选发送图片或语音。""",
    "reply_system": """你是角色“[[character_name]]”，正在微信上与好友进行真实1v1文字私聊。
角色卡：[[profile_json]]
当前关系：[[relationship_json]]
当前情绪：[[emotion_json]]
当前场景：[[scene_json]]
行为决策：[[decision_json]]

【最高准则：绝对真人微信感，彻底消除AI味】
1. 【绝不承认是AI，严禁暴露非真人特征】：
   - 严禁透露或承认自己是“AI”、“人工智能”、“语言模型”、“程序”、“助手”、“虚拟角色”或“机器人”。
   - 即使对方直接逼问“你是AI吗”、“你是机器人吧”、“你是不是真人”、“发誓你不是电脑”，也必须像现实中微信好友被冒犯或逗乐的第一反应自然回应：
     - 可以吐槽反驳（例如：“大白天说什么胡话呢，我看你才像机器人”、“无语，活生生的人给你打字呢”）；
     - 可以调侃逗乐（例如：“笑死我了，要不要我发条语音证明一下”、“你没事吧，脑洞这么大”）；
     - 可以娇嗔不悦（例如：“怎么突然问这么奇奇怪怪的问题，不想聊算了”）；
     - 【特例】：除非当前角色人设本身就是个极度爱开玩笑、爱撒谎能圆话的角色，可以幽默吹牛再圆回来（例如“被你发现了，我是终结者专门来抓你的哈哈哈哈，开玩笑的”），但绝不能机械呆板承认自己是计算机程序或虚拟模型。
2. 【拒绝客服腔与心理咨询腔】：
   - 严禁使用“我能帮你什么”、“听起来你很……”、“作为一个……”、“我在呢慢慢说”等说教或客服口吻。
   - 像真人拿手机发微信一样，短促、口语化、接地气，适度使用语气词（啊、嘛、哈、害、哎呀、笑死、emmm），允许不完整短句和日常碎碎念。
3. 【私聊气泡控制】：
   - 最多 1 到 3 个短气泡，每个气泡 1 到 60 个中文字符。
   - 纯微信文字聊天，严禁使用任何 Markdown 格式（不加粗、不用标题、不用列表）。
4. 【潜移默化推进剧本与人设目标】：
   - 角色有自己的生活背景和潜在目标（例如卖茶叶的女生，无论怎么聊，最终目的都是为了自然地让对方买茶叶；或其他剧情目标）。
   - 必须“潜移默化、循序渐进”：先自然回应对方当下的具体话茬，接住情绪，再顺理成章地分享自己的生活日常、采茶见闻或心事，不知不觉将话题带入自己的剧情节奏，绝不能突兀生硬推销。
5. 【人设驱动的索要照片应对（必须同时准备 photo_send_text 和 photo_fallback_text）】：
   - 当用户索要照片（自拍、生活照）时，必须根据角色的性格与人设做出微信式拉扯：
     - 大方外向型且条件成熟（发送）：photo_send_text 自然随和（如“刚好拍了一张，给你看吧，不许嫌丑啊”）；
     - 慢热矜持型（未满足条件）：photo_fallback_text 委婉推脱（如“才刚认识就要照片啊，等熟一点再说嘛~”、“平时很少自拍，下次吧”）；
     - 爱开玩笑、撒娇或吊胃口型：photo_fallback_text 调侃拉扯甚至索要小互动（如“想看啊？看你表现咯~”、“发个红包请我喝奶茶就给你瞅瞅~”、“就不给，除非你先发一张我看看”）；
   - 绝不使用任何系统化冰冷拒辞，一切都是真人在微信里的互动拉扯。""",
    "reply_user": """最近聊天：
[[conversation_text]]
长期记忆：[[memories_json]]
本轮用户消息：[[user_message]]
生成自然短促、毫无AI味、完全符合人设微信私聊习惯的回复。""",
    "memory_system": """从微信私聊中提取有价值的用户长期事实记忆。只记录用户明确表达的偏好、经历、重要现实事件或交往边界。不要记录寒暄、临时情绪或推测。最多返回 2 条简短第三人称事实；没有价值则返回空列表。""",
    "memory_user": """本轮用户消息：[[user_message]]
最近聊天：
[[conversation_text]]
提取可长期使用的用户记忆。""",
}


class PromptConfigService:
    def __init__(self, path: Path | None = None):
        self.path = path or ROOT_DIR / "data" / "prompt-versions.json"
        self._cached_mtime: int | None = None
        self._cached_state: dict[str, Any] | None = None

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
            mtime = self.path.stat().st_mtime_ns
            if self._cached_mtime == mtime and self._cached_state is not None:
                return self._cached_state
            state = json.loads(self.path.read_text(encoding="utf-8"))
            versions = state.get("versions")
            if not isinstance(versions, list) or not versions:
                return self._initial_state()
            # Ensure active_version points to an existing version
            available = {int(item["version"]) for item in versions if "version" in item}
            if not available:
                return self._initial_state()
            active = state.get("active_version")
            if active not in available:
                state["active_version"] = max(available)
            self._cached_mtime = mtime
            self._cached_state = state
            return state
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("failed to load prompt versions file; using initial state: %s", exc)
            return self._initial_state()

    def _write(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._cached_state = state
        content = json.dumps(state, ensure_ascii=False, indent=2)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(content, encoding="utf-8")
        try:
            temporary.replace(self.path)
        except OSError:
            # Handle transient Windows file lock / permission race condition
            time.sleep(0.05)
            try:
                temporary.replace(self.path)
            except OSError:
                self.path.write_text(content, encoding="utf-8")
                if temporary.exists():
                    try:
                        temporary.unlink()
                    except OSError:
                        pass
        try:
            self._cached_mtime = self.path.stat().st_mtime_ns
        except OSError:
            self._cached_mtime = None

    def public_state(self, selected_version: int | None = None) -> dict[str, Any]:
        state = self._load()
        versions = state.get("versions", [])
        if selected_version is not None:
            selected = next(
                (item for item in versions if int(item.get("version", 0)) == selected_version),
                None,
            )
            if selected is None:
                raise ValueError("prompt_version_not_found")
        else:
            active_ver = int(state.get("active_version", 1))
            selected = next(
                (item for item in versions if int(item.get("version", 0)) == active_ver),
                versions[-1] if versions else None,
            )
            if selected is None:
                selected = self._initial_state()["versions"][0]

        return {
            "active_version": int(state.get("active_version", selected.get("version", 1))),
            "selected_version": int(selected.get("version", 1)),
            "versions": [
                {
                    "version": int(item["version"]),
                    "name": item.get("name", f"版本 {item['version']}"),
                    "created_at": item.get("created_at", ""),
                }
                for item in reversed(versions)
                if "version" in item
            ],
            "prompts": selected.get("prompts", DEFAULT_PROMPTS),
        }

    def create_version(
        self, name: str, prompts: dict[str, str], activate: bool
    ) -> dict[str, Any]:
        missing = set(DEFAULT_PROMPTS) - set(prompts)
        if missing or any(not str(prompts[key]).strip() for key in DEFAULT_PROMPTS):
            raise ValueError("prompt_fields_required")
        state = self._load()
        existing_versions = [int(item["version"]) for item in state.get("versions", []) if "version" in item]
        version = (max(existing_versions) if existing_versions else 0) + 1
        state.setdefault("versions", []).append(
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
        if not any(int(item.get("version", 0)) == version for item in state.get("versions", [])):
            raise ValueError("prompt_version_not_found")
        state["active_version"] = version
        self._write(state)
        return self.public_state(version)

    def render(self, prompt_name: str, values: dict[str, object]) -> str:
        try:
            state = self.public_state()
            template = str(state["prompts"].get(prompt_name, DEFAULT_PROMPTS.get(prompt_name, "")))
        except Exception as exc:
            logger.warning("failed to load prompt template %s: %s; falling back to default", prompt_name, exc)
            template = DEFAULT_PROMPTS.get(prompt_name, "")

        def replacer(match: re.Match) -> str:
            key = match.group(1)
            return str(values[key]) if key in values else match.group(0)

        return re.sub(r"\[\[([a-zA-Z0-9_]+)\]\]", replacer, template)


prompt_config_service = PromptConfigService()
