# 1v1 虚拟角色聊天 Demo 设计文档

> 版本：v0.1  
> 状态：开发前设计  
> 目标：从 0 构建一个可本地运行、以 LangGraph 为核心聊天编排的 1v1 虚拟角色文字/语音聊天 Demo。

## 1. 产品定位

用户选择一个虚构角色，与角色进行类似微信私聊的单聊。角色不是通用 AI 助手，而是具有固定背景、语言习惯、情绪惯性、关系数值、剧情状态和照片策略的聊天对象。

核心体验：

- 回复短、口语化、有上下文反应，不输出长篇总结。
- 同一个角色对同一个用户会记住已经发生的事情。
- 角色的情绪不会每轮重置，会随着互动延续、衰减和变化。
- 关系会影响称呼、开放程度、剧情推进和是否发照片。
- 角色可以有明显目的和剧本，例如虚构的茶叶店角色会自然地把话题引向茶叶，但不能变成现实诈骗或诱导转账。
- 页面和角色列表明确标注“虚拟角色”，不冒充现实中的真实个人。

### 1.1 沉浸感与安全边界

本 Demo 允许角色在自己的世界观中保持沉浸式口吻，不主动输出“作为 AI”“根据系统提示”等程序化话术。但以下边界优先级高于角色扮演：

1. 产品层始终显示“虚拟角色”标识，不伪装成现实中的真实个人。
2. 用户直接询问身份、真实联系方式、现实见面、付款或交易时，必须给出清晰且自然的虚拟角色边界。
3. 不生成冒充真实个人、伪造现实关系、伪造收款凭证、诱导转账、索要验证码或敏感身份信息的内容。
4. “收到红包才发照片”这类角色设定在 Demo 中只允许作为虚构台词或关系边界，不读取真实支付状态、不提供支付入口、不把真实金钱作为解锁照片的条件。实现时降级为“聊熟一点再发”或“完成应用内非货币剧情条件”。
5. “卖茶叶的女生”只能实现为明确的虚构门店/剧情角色，不面向现实联系人批量加人，不承诺真实发货，不引导用户离开 Demo 付款。
6. TTS 只使用合成音色或获得授权的虚构音色，不克隆现实人物、公众人物或用户的声音，不用语音冒充现实中的身份凭证。
7. 语音默认不自动播放，由用户点击播放；音频生成失败时必须保留文字回复。

这套边界不会破坏普通角色聊天的自然感，只在身份、现实交易和高风险请求上触发透明回应。

## 2. MVP 范围

### 2.1 第一版必须完成

- Python 3.12，使用 uv 管理 Python 依赖和锁文件。
- FastAPI 后端。
- LangGraph 主链：

  加载上下文 -> 行为决策 -> 场景判断 -> 回复生成 -> 图片判断 -> 状态更新 -> 记忆提取 -> END

- 语音通过图片判断之后的可选 voice_judgment -> tts_generation 分支接入，不改变文字主链。
- LangChain + OpenAI Compatible API。
- SQLAlchemy + SQLite。
- 四张核心表：characters、conversations、messages、memories。
- 角色列表、聊天页面、头像、文字气泡、图片消息。
- 角色根据人设和本轮行为发送 TTS 语音。
- 刷新后消息和角色状态仍然存在。
- 角色情绪、关系、场景和长期记忆。
- 最大重试次数和模型失败兜底。
- 本地角色图片目录，不接入实时生图。
- 本地生成语音文件，不把音频二进制存入 SQLite。

### 2.2 第一版不做

- MySQL、Redis、Milvus 或其他外部基础设施。
- 真实用户注册、短信、支付和红包系统。
- 多人群聊。
- 实时语音通话、视频和实时 AI 生图。
- 语音克隆、用户上传音色训练和自动播放。
- 复杂后台运营系统。
- 让模型直接执行 SQL、直接写数据库或直接决定任意文件路径。

MVP 的 user_id 使用浏览器本地生成的 demo 用户标识；不建 users 表。这样既符合四张核心表限制，也方便本地运行。

## 3. 总体架构

~~~text
Vue 3 + TypeScript
  ├─ 角色列表
  ├─ 聊天页
  ├─ 历史消息加载
  └─ 逐条展示/正在输入
          │ HTTP JSON
          ▼
FastAPI
  ├─ Character API
  ├─ Conversation API
  ├─ Chat API
  └─ ChatService
          │
          ▼
LangGraph
  load_context
      -> behavior_decision
      -> conditional behavior route
      -> scene_judgment
      -> reply_generation
      -> image_judgment
      -> conditional image route
      -> optional voice_judgment
      -> optional tts_generation
      -> state_update
      -> memory_extraction
      -> END
          │
          ├─ LLMService -> OpenAI Compatible API
          ├─ TTSService -> 豆包双向流式 TTS WebSocket
          ├─ Repository -> SQLAlchemy/SQLite
          └─ AssetResolver -> app/static/characters and app/static/audio
~~~

图中的条件路由节点是无模型、无副作用的小节点，用来把结构化的行为决策转换为 LangGraph 的分支；主链上的业务节点保持固定。

## 4. 推荐目录结构

项目根目录使用一个 Python uv 项目，前端作为独立 npm 项目：

~~~text
demo/
├─ pyproject.toml
├─ uv.lock
├─ .env.example
├─ README.md
├─ docs/
│  └─ design.md
├─ app/
│  ├─ main.py
│  ├─ config.py
│  ├─ db/
│  │  ├─ base.py
│  │  ├─ models.py
│  │  ├─ session.py
│  │  └─ repositories.py
│  ├─ domain/
│  │  ├─ characters.py
│  │  ├─ relationship.py
│  │  ├─ emotion.py
│  │  ├─ scene.py
│  │  └─ photo_policy.py
│  ├─ graph/
│  │  ├─ state.py
│  │  ├─ schemas.py
│  │  ├─ builder.py
│  │  ├─ routing.py
│  │  └─ nodes/
│  │     ├─ load_context.py
│  │     ├─ behavior_decision.py
│  │     ├─ scene_judgment.py
│  │     ├─ reply_generation.py
│  │     ├─ image_judgment.py
│  │     ├─ voice_judgment.py
│  │     ├─ tts_generation.py
│  │     ├─ state_update.py
│  │     └─ memory_extraction.py
│  ├─ services/
│  │  ├─ chat_service.py
│  │  ├─ llm_service.py
│  │  ├─ tts_service.py
│  │  └─ asset_service.py
│  ├─ api/
│  │  ├─ characters.py
│  │  ├─ conversations.py
│  │  └─ chat.py
│  ├─ seed.py
│  └─ static/
│     └─ characters/
│        ├─ suhe/
│        │  ├─ avatar.png
│        │  └─ photos/
│        ├─ linwan/
│        └─ shenyan/
├─ data/
│  ├─ chat.db
│  └─ audio/
└─ frontend/
   ├─ package.json
   ├─ vite.config.ts
   └─ src/
      ├─ App.vue
      ├─ api/chat.ts
      ├─ types/chat.ts
      ├─ components/
      │  ├─ CharacterList.vue
      │  ├─ ChatHeader.vue
      │  ├─ MessageBubble.vue
      │  ├─ TypingIndicator.vue
      │  └─ Composer.vue
      └─ styles/
         └─ app.css
~~~

## 5. LangGraph 设计

### 5.1 ChatState

ChatState 使用 TypedDict 或 Pydantic 兼容的状态对象。状态只保存本轮编排需要的业务数据，不保存 SQLAlchemy Session、API Key 或完整 Prompt。

~~~text
ChatState
├─ conversation_id: int
├─ user_id: str
├─ user_message: str
├─ character: CharacterSnapshot
├─ recent_messages: list[MessageSnapshot]
├─ relationship: RelationshipState
├─ emotion: EmotionState
├─ scene: SceneState
├─ memories: list[MemorySnapshot]
├─ behavior_decision: BehaviorDecision | None
├─ reply_messages: list[ReplyMessage]
├─ image_decision: ImageDecision | None
├─ voice_decision: VoiceDecision | None
├─ tts_result: TTSResult | None
├─ memory_candidates: list[MemoryCandidate]
├─ persistence_patch: PersistencePatch | None
├─ reply_mode: str
├─ graph_error: str | None
├─ llm_attempts: dict[str, int]
└─ tts_attempts: int
~~~

必备字段与用户要求一一对应：

- user_message：本轮用户输入。
- character：角色快照，包括人设、背景、说话风格和照片策略。
- recent_messages：最近 N 条消息，默认 20 条。
- relationship：familiarity、trust、affection、annoyance。
- emotion：当前主情绪、强度、效价和最近更新时间。
- scene：当前剧情状态、进入时间、标记和最近动作。
- memories：检索到的长期记忆。
- behavior_decision：行为节点的结构化输出。
- reply_messages：最终要返回给前端的一条或多条消息。
- voice_decision：本轮是否需要生成语音，以及使用哪种安全的角色音色。

### 5.2 结构化决策模型

BehaviorDecision 是行为节点的严格输出，不允许模型返回自由 JSON 后直接使用：

~~~text
BehaviorDecision
├─ intent:
│  greeting | question | emotion_share | request_photo |
│  relationship_test | scene_participation | complaint | other
├─ action:
│  normal_reply | avoid | advance_scene | ask_clarification
├─ emotion:
│  target: calm | happy | shy | curious | annoyed | sad | guarded
│  intensity_delta: -20..20
├─ relationship_delta:
│  familiarity: -10..10
│  trust: -10..10
│  affection: -10..10
│  annoyance: -10..10
├─ scene_action:
│  none | keep | enter_familiar | enter_daily |
│  advance_plot | end_plot | delay
├─ should_send_image: bool
├─ should_send_voice: bool
└─ internal_reason: 仅日志使用，不展示给用户
~~~

Pydantic 校验规则：

- 枚举字段不接受未知值。
- 所有数值做范围校验并在状态更新时再次 clamp。
- internal_reason 不进入消息内容。
- should_send_image 只是候选意图，模型不能直接指定文件路径。
- should_send_voice 只是候选意图，模型不能直接指定 voice_id、音频路径或 TTS 参数。
- JSON 多余字段默认拒绝；解析失败进入有限重试，不能静默接受半结构化文本。

### 5.3 主节点职责

#### Node 1：load_context

输入：conversation_id、user_id、character_id、user_message。

处理：

1. 查询角色配置和当前会话。
2. 查询最近 20 条 messages。
3. 查询最近使用或重要度最高的 memories。
4. 根据上次 emotion_state 和 last_updated_at 计算情绪衰减。
5. 如果会话不存在，使用角色默认关系、情绪和初始场景。
6. 组装 CharacterSnapshot，避免后续节点反复访问数据库。

该节点不调用 LLM。

#### Node 2：behavior_decision

职责是判断“这一轮角色准备怎么做”，不是直接生成最终文本。

Prompt 输入包含：

- 角色卡。
- 当前 relationship、emotion、scene。
- 最近消息。
- 相关长期记忆。
- 本轮 user_message。
- 允许的行为枚举和数值范围。

Prompt 输出必须是 BehaviorDecision。调用 LLMService 的结构化输出方法，最多执行 3 次尝试，即首次调用加 2 次重试。

#### Conditional Edge：route_behavior

根据 behavior_decision.action 和 intent 设置 reply_mode，并进入 scene_judgment：

~~~text
normal_reply / question / greeting
  -> reply_mode = normal
  -> scene_judgment

avoid
  -> reply_mode = avoid
  -> scene_judgment

advance_scene
  -> reply_mode = advance
  -> scene_judgment

request_photo
  -> reply_mode = photo_request
  -> scene_judgment
~~~

该路由是 LangGraph conditional edge 的显式落点。它不让模型跳过状态更新，也不允许行为节点直接返回 HTTP。

#### Node 3：scene_judgment

场景判断第一版以确定性状态机为主，避免模型随意跳剧情。

默认场景：

~~~text
first_meet 初识
  -> familiar 熟悉
  -> daily 日常
  -> plot 特定剧情
~~~

建议转移条件：

- 初识 -> 熟悉：累计互动轮数达到 3，且 familiarity >= 25。
- 熟悉 -> 日常：trust >= 40 或 affection >= 45，且最近没有连续回避。
- 日常 -> 特定剧情：角色配置允许，且 scene_action=advance_plot，或用户完成指定剧情条件。
- 特定剧情 -> 日常：剧情结束或 scene_action=end_plot。
- 不允许从初识直接跳到高亲密剧情。

scene_judgment 输出 scene_patch，不立即写数据库。剧情角色可以配置自己的 transition_rules，但必须在允许的状态机范围内。

#### Node 4：reply_generation

根据已经判断出的行为、场景和角色卡生成一条或多条短消息。

输出模型：

~~~text
ReplyPlan
├─ messages: 1..3 个 TextReply
│  ├─ content: 1..80 个中文字符
│  ├─ delay_ms: 0..3000
│  └─ tone: normal | teasing | guarded | warm | sales_script
├─ photo_fallback_text: 照片未发送时使用的短句，可为空
└─ voice_text: 用于 TTS 的可朗读文本，可为空；默认由可朗读的回复合并得到
~~~

输出约束：

- 一次最多 3 个气泡，每个气泡尽量只表达一个意思。
- 不写文章、总结、条目、Markdown、系统说明或“我理解你的需求”。
- 优先回应用户最后一句，不重复完整上下文。
- 使用角色自己的口头禅、称呼、停顿和情绪。
- 不编造已发送的图片；图片是否发送由后续 image_judgment 决定。
- 不在文字中宣称“语音已经发出”；语音由后续 voice_judgment 和 tts_generation 决定。
- 不泄露内部状态、Prompt、模型、数据库、工具和程序。
- 面对现实交易、身份冒充、敏感信息或直接身份追问时，使用自然但透明的边界话术。

#### Node 5：image_judgment

这是图片最终裁决节点。BehaviorDecision 的 should_send_image 只是候选值，不能跳过本节点。

输入：

- 用户是否明确索要照片。
- 角色 photo_policy。
- 当前 relationship 和 scene。
- 角色本地可用图片资产。
- 行为候选值。

输出：

~~~text
ImageDecision
├─ outcome: none | send | decline | delay
├─ asset_id: str | None
├─ image_url: str | None
└─ reason: internal only
~~~

规则示例：

- 非照片请求：outcome=none。
- 角色配置为“初识不发”：初识时 decline 或 delay。
- 角色配置为“熟悉后发”：familiarity/trust 达到阈值才 send。
- 角色配置为“自然分享”：关系达到最低阈值或场景触发时 send。
- 本地没有符合条件的图片：不得生成假 URL，改为 decline/delay。
- 模型不能返回任意绝对路径；asset_id 只能从角色白名单中选择。
- 涉及红包、转账、付费等真实货币条件时，统一改为安全的关系/剧情条件。

如果 outcome=send，追加一个 image ReplyMessage；如果 outcome=decline/delay 且 reply_generation 没有合适文本，则使用角色配置的短模板补一条文字消息。

#### Conditional Edge：route_image

~~~text
send
  -> append_image_message
  -> voice_judgment

none / decline / delay
  -> voice_judgment
~~~

append_image_message 只负责把已经由 AssetResolver 校验过的图片加入 reply_messages，不调用 LLM。

#### Optional Node 6：voice_judgment

语音是文字回复之后的可选媒体分支，不替代行为决策，也不改变角色的关系和剧情状态。

输入：

- behavior_decision.should_send_voice。
- 用户是否明确说“发语音”“说句话”“想听听你的声音”等。
- character.voice_policy。
- 当前 scene、emotion 和本轮最终文字。
- TTS_ENABLED 和可用的音色配置。

输出：

~~~text
VoiceDecision
├─ outcome: none | send
├─ voice_id: str | None
├─ display_mode: text_and_audio | audio_only
├─ text: 用于合成的短文本
└─ reason: internal only
~~~

voice_judgment 使用确定性规则裁决，模型只提供候选意图：

- voice_policy=never：不发语音。
- voice_policy=on_request：用户明确请求时才发。
- voice_policy=emotional：角色处于特定情绪或剧情节点时可以发。
- voice_policy=occasional：满足关系阈值后低频发送，不能每轮随机发。
- 用户明确要求发语音时，如果 TTS 可用则优先发送。
- 每轮最多发送一条语音；文本长度超过配置上限时只发送文字。
- 身份边界、交易边界和安全拒绝可以用语音表达，但不生成现实身份或付款承诺。
- voice_id 只能来自角色白名单，不接受模型自定义值。

第一版默认 display_mode=text_and_audio：同时保留文字气泡和语音气泡，方便调试和无障碍使用。角色配置为 audio_only 时，前端隐藏文字气泡但在音频 metadata 中保存 transcript；TTS 失败时回退为可见文字。

#### Optional Node 7：tts_generation

调用 TTSService 把 voice_judgment.text 转换为本地音频文件：

1. 去除 Markdown、URL 和不适合朗读的内部标记。
2. 使用角色已配置的 voice_id、model、format。
3. 将音频写入 data/audio/{conversation_id}/ 下的随机文件名。
4. 只返回相对静态路径、duration_ms 和 transcript，不返回绝对路径。
5. 将音频 ReplyMessage 加入 reply_messages。

TTS 最多执行 2 次尝试。网络错误、超时和兼容接口错误都只影响音频；文字回复保留并正常持久化。生成了但最终未提交的临时文件只允许按本次请求的明确路径清理，不能使用宽泛目录删除。

#### Conditional Edge：route_voice

~~~text
voice_judgment = none
  -> state_update

voice_judgment = send
  -> tts_generation
  -> state_update

tts_generation 失败
  -> state_update，保留文字回复
~~~

TTS_ENABLED=false 或 TTS 接口未配置时直接走 none，原有文字和图片链路不受影响。

#### Node 8：state_update

纯业务计算，不调用 LLM：

1. 对当前 emotion 应用时间衰减。
2. 合并 behavior_decision.emotion。
3. 合并 relationship_delta，并把四项数值限制在 0..100。
4. 应用 scene_patch。
5. 生成本轮 persistence_patch。
6. 合并图片和音频 ReplyMessage。
7. 为每条回复补充 message_type、delay_ms、scene_snapshot 和 client_key。

关系更新建议：

- 正常回应：familiarity 小幅增加。
- 用户表达关心且角色接受：trust/affection 增加。
- 反复逼问、越界或不尊重边界：annoyance 增加，trust 可能下降。
- 长时间无互动：emotion 强度衰减，但关系不自动大幅下降。

情绪模型：

~~~text
emotion_state = {
  dominant: "guarded",
  intensity: 0..100,
  valence: -100..100,
  updated_at: ISO datetime
}
~~~

每次 load_context 先做衰减，再应用本轮 delta；不能从角色默认情绪重置。

#### Node 9：memory_extraction

从本轮用户输入、角色回复和上下文中提取长期有效信息。

输出：

~~~text
MemoryExtraction
└─ candidates: 0..2 个 MemoryCandidate
   ├─ type: preference | experience | important_event | boundary
   ├─ content: 1..120 个字符
   ├─ importance: 1..5
   └─ evidence: 本轮消息 id 或 client_key
~~~

只记录：

- 用户明确表达的偏好。
- 用户反复提到的经历。
- 对关系或剧情有长期影响的重要事件。
- 用户明确的聊天边界。

不记录密码、验证码、支付信息、精确住址、身份证号等敏感信息。相似记忆按规范化文本去重，已有记忆可以更新 last_used_at，不无限新增。

### 5.4 图构建与失败策略

GraphBuilder 在启动时构建单例 graph。每个请求传入 conversation_id、user_id、character_id 和 user_message，不能把 SQLAlchemy Session 放进可持久化的 GraphState。

失败处理分层：

1. 结构化解析失败、短暂网络错误、限流：最多 2 次重试，退避 300ms、800ms。
2. 重试仍失败：使用确定性 fallback_behavior 和角色安全短回复，仍然执行状态更新和持久化。
3. 数据库错误：不伪造成功，返回 HTTP 500，并记录 request_id。
4. 图片资产错误：仅取消图片，不影响文字回复。
5. 安全策略命中：不重试违规内容，直接使用安全短回复。

Fallback 示例：

~~~text
behavior_decision:
  action = normal_reply
  scene_action = keep
  should_send_image = false
  should_send_voice = false

reply_messages:
  - content = 角色配置的短暂离开/思考话术
    type = text
~~~

## 6. 角色与人设模型

characters 表中的 JSON 配置拆为以下逻辑结构：

~~~text
character_profile
├─ background: 背景和当前生活
├─ personality: 性格标签、优点、缺点、底线
├─ speech_style: 称呼、口头禅、句长、标点、禁用词
├─ goals: 当前想推进的事情
├─ secrets: 只在剧情条件满足时可透露的虚构信息
├─ scene_rules: 场景转移规则
├─ photo_policy: 图片条件和可用 asset_id
├─ voice_policy: voice_policy、voice_id、发送条件和 display_mode
└─ safety_notes: 现实身份和交易边界
~~~

建议初始化三个角色：

1. 苏禾：慢热、嘴硬、喜欢拍街边小店。初识时不主动发照片，熟悉后会自然分享生活照。
2. 林晚：虚构茶叶店的年轻店主，热情、会绕着茶叶话题聊天，有明确的“介绍产品”剧情目标。所有商品、门店和交易均为 Demo 剧情，不提供真实支付。
3. 沈砚：话少、观察力强、对照片谨慎。用户直接索要时通常延迟，关系稳定后才发一张本地照片。

建议的初始语音策略：

- 苏禾：on_request，温和女声，text_and_audio。
- 林晚：occasional，活泼女声，text_and_audio；只在虚构茶叶剧情中发送。
- 沈砚：on_request，低沉男声，audio_only；关系不足时不发。

每个角色的图片目录只放虚构角色素材，avatar 和 photos 由 seed 数据引用。voice_id 只引用 TTS 服务中已配置的合成音色。

## 7. SQLite 数据模型

只使用四张核心表。

### 7.1 characters

~~~text
id               INTEGER PRIMARY KEY
code             VARCHAR UNIQUE NOT NULL
name             VARCHAR NOT NULL
avatar_path      VARCHAR NOT NULL
profile_json     JSON NOT NULL
is_active        BOOLEAN NOT NULL DEFAULT TRUE
created_at       DATETIME NOT NULL
updated_at       DATETIME NOT NULL
~~~

profile_json 保存 background、personality、speech_style、scene_rules、photo_policy 等角色配置。

### 7.2 conversations

~~~text
id                   INTEGER PRIMARY KEY
user_id              VARCHAR NOT NULL
character_id         INTEGER NOT NULL REFERENCES characters(id)
relationship_state   JSON NOT NULL
emotion_state        JSON NOT NULL
scene_state          JSON NOT NULL
created_at           DATETIME NOT NULL
updated_at           DATETIME NOT NULL

UNIQUE(user_id, character_id)
~~~

按要求，关系、情绪和场景直接放在 conversations 的 JSON 字段中，不拆成额外表。

### 7.3 messages

~~~text
id              INTEGER PRIMARY KEY
conversation_id INTEGER NOT NULL REFERENCES conversations(id)
role            VARCHAR NOT NULL
message_type    VARCHAR NOT NULL
content         TEXT
image_path      VARCHAR
audio_path      VARCHAR
audio_duration_ms INTEGER
metadata_json   JSON
created_at      DATETIME NOT NULL
~~~

role 只使用 user、assistant；message_type 使用 text、image、audio。metadata_json 可保存 delay_ms、scene、action、request_id、transcript、voice_id、display_mode 等前端展示需要的数据，不保存完整内部 Prompt。音频文件保存在本地静态目录，数据库只保存相对路径和时长。

### 7.4 memories

~~~text
id                 INTEGER PRIMARY KEY
conversation_id    INTEGER NOT NULL REFERENCES conversations(id)
memory_type        VARCHAR NOT NULL
content            TEXT NOT NULL
importance         INTEGER NOT NULL
source_message_id  INTEGER
last_used_at       DATETIME
created_at         DATETIME NOT NULL
is_active          BOOLEAN NOT NULL DEFAULT TRUE
~~~

查询策略：同一 conversation 先取 is_active=true，再按 importance DESC、last_used_at DESC 限制数量；写入前做规范化去重。

### 7.5 持久化事务

ChatService 在调用 graph 前组装本轮上下文；graph 返回后，在一个 SQLAlchemy 事务中写入：

1. user message。
2. assistant text/image/audio messages。
3. conversation 的 relationship_state、emotion_state、scene_state。
4. memory_candidates。

TTS 文件先写入本次请求的临时/目标路径，数据库事务成功后才作为正式 message 返回。TTS 失败不回滚文字；数据库失败时只清理本次请求明确产生的临时文件。任何异常都不能只返回“发送成功”而不落库。

## 8. LLMService

LLMService 是唯一允许接触 OpenAI Compatible API 的服务，Graph 节点不直接创建模型客户端。

职责：

- 从 pydantic-settings 读取 base_url、api_key、model、timeout。
- 使用 LangChain 的 ChatOpenAI 兼容客户端。
- 提供 invoke_structured(schema, messages, purpose)。
- 统一超时、限流和解析异常。
- 对行为决策、回复计划、记忆提取设置不同的系统 Prompt。
- 记录 purpose、attempt、耗时和 request_id；不记录 API Key 和完整敏感对话。
- 不允许模型决定 SQL、任意本地路径或任意 HTTP URL。

### 8.1 TTSService

TTSService 与 LLMService 分离，第一版默认接入豆包双向流式语音合成。配置和协议对齐 YQ `StudentMockInterview` V2 的 `DoubaoBidirectionalTtsProperties` 与 `VolcengineStreamingTtsClient`。

官方接口为 `wss://openspeech.bytedance.com/api/v3/tts/bidirection`，通过以下握手 Header 鉴权：

~~~text
X-Api-Key: {api_key}
X-Api-App-Id: {app_id}
X-Api-Resource-Id: seed-tts-2.0
X-Api-Connect-Id: {uuid}
~~~

一轮合成按以下顺序发送双向协议事件：

~~~text
START_CONNECTION(1)
  -> wait CONNECTION_STARTED(50)
START_SESSION(100, speaker, audio_params={format: pcm, sample_rate: 24000})
  -> wait SESSION_STARTED(150)
TASK_REQUEST(200, text)
FINISH_SESSION(102)
  -> receive audio chunks / RESPONSE(352)
  -> wait SESSION_FINISHED(152)
FINISH_CONNECTION(2)
~~~

豆包双向接口常用输出是裸 PCM。Demo 将单声道 16-bit PCM 封装成 WAV 后写入 `data/audio/{conversation_id}/`，数据库只保存相对 URL、时长、transcript 和实际音色 ID；不把 base64 音频写入 messages。

服务职责：

- 只接受已经通过 `voice_judgment` 的短文本和角色卡音色。
- 限制输入长度，过滤 Markdown、URL、内部标记和不可朗读控制字符。
- 连接、协议或服务商错误最多执行有限重试；不会把鉴权信息写入日志或用户响应。
- `fictional-*` 等 Demo 音色标签映射到配置的默认豆包音色；真实的 `zh_`、`en_`、`multi_` 音色 ID 才直接传给供应商。
- TTS 不可用时返回可识别的失败结果，不抛掉本轮文字回复。
- 不提供声音克隆、音色训练或用户上传音色能力。

建议环境变量：

~~~text
APP_ENV=dev
DATABASE_URL=sqlite+aiosqlite:///./data/chat.db
OPENAI_BASE_URL=https://your-compatible-endpoint/v1
OPENAI_API_KEY=replace-me
OPENAI_MODEL=your-chat-model
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
TTS_ENABLED=false
TTS_PROVIDER=doubao_bidirection
DOUBAO_BIDIRECTION_TTS_WEBSOCKET_URL=wss://openspeech.bytedance.com/api/v3/tts/bidirection
DOUBAO_BIDIRECTION_TTS_API_KEY=
DOUBAO_BIDIRECTION_TTS_APP_ID=
DOUBAO_BIDIRECTION_TTS_RESOURCE_ID=seed-tts-2.0
DOUBAO_BIDIRECTION_TTS_SPEAKER=zh_female_shuangkuaisisi_uranus_bigtts
DOUBAO_BIDIRECTION_TTS_OUTPUT_FORMAT=pcm
DOUBAO_BIDIRECTION_TTS_OUTPUT_SAMPLE_RATE=24000
DOUBAO_BIDIRECTION_TTS_CONNECT_TIMEOUT_SECONDS=10
TTS_MAX_CHARS=180
TTS_TIMEOUT_SECONDS=20
TTS_MAX_RETRIES=2
TTS_BASE_URL=
TTS_MODEL=your-tts-model
TTS_DEFAULT_VOICE=fictional-default
TTS_FORMAT=mp3
DEMO_USER_ID=demo-user
~~~

设置 `TTS_PROVIDER=openai_compatible` 可以回退到兼容 `POST /audio/speech` 的服务；这不是豆包默认链路。

Python 依赖以 pyproject.toml 为准，并由 uv.lock 锁定；不再维护一份容易漂移的 requirements.txt。

## 9. FastAPI API 设计

### 9.1 角色列表

~~~text
GET /api/characters
~~~

返回角色 id、code、name、简介、avatar_url、虚拟角色标识。不会返回内部 Prompt、隐藏秘密或完整安全配置。

### 9.2 创建或获取会话

~~~text
POST /api/conversations
Content-Type: application/json

{
  "user_id": "browser-generated-demo-user",
  "character_id": 1
}
~~~

同一 user_id + character_id 返回同一个 conversation，保证刷新后继续聊天。

### 9.3 获取历史消息

~~~text
GET /api/conversations/{conversation_id}/messages?limit=100
~~~

返回消息列表、角色信息和当前可展示的 scene/relationship 摘要。

### 9.4 发送消息

~~~text
POST /api/conversations/{conversation_id}/messages
Content-Type: application/json

{
  "user_id": "browser-generated-demo-user",
  "content": "你今天在忙什么？"
}
~~~

响应：

~~~text
{
  "user_message": {
    "id": 11,
    "role": "user",
    "message_type": "text",
    "content": "你今天在忙什么？"
  },
  "assistant_messages": [
    {
      "id": 12,
      "role": "assistant",
      "message_type": "text",
      "content": "刚收完一批茶，手都酸了",
      "delay_ms": 0
    },
    {
      "id": 13,
      "role": "assistant",
      "message_type": "text",
      "content": "你呢，今天顺利吗",
      "delay_ms": 700
    },
    {
      "id": 14,
      "role": "assistant",
      "message_type": "audio",
      "audio_url": "/static/audio/12/7e6c9f1a.mp3",
      "audio_duration_ms": 2600,
      "transcript": "你呢，今天顺利吗",
      "delay_ms": 900
    }
  ],
  "state": {
    "scene": "familiar",
    "relationship": {
      "familiarity": 31,
      "trust": 22,
      "affection": 18,
      "annoyance": 0
    },
    "emotion": {
      "dominant": "calm",
      "intensity": 46
    }
  }
}
~~~

第一版使用普通 JSON 响应即可。前端在请求期间显示“正在输入”，收到 assistant_messages 后根据 delay_ms 逐条加入聊天列表。audio 消息只返回 audio_url 和时长，前端点击后播放，不自动播放。这样不引入 Redis 或 SSE 连接管理，仍能实现多条文字/图片/语音消息延迟显示。后续如果需要服务端实时生成，再增加 SSE，不改变 Graph 主链。

### 9.5 健康检查

~~~text
GET /healthz
~~~

只检查应用和 SQLite 是否可用，不调用 LLM。

## 10. Vue 聊天页设计

### 10.1 页面布局

桌面端：

- 左侧角色列表：头像、姓名、短简介、虚拟角色标签。
- 右侧聊天区域：顶部角色头像/名称/在线状态，中间消息列表，底部输入框。

移动端：

- 角色列表折叠为顶部选择器。
- 聊天气泡占满宽度，保留左右方向。

视觉上使用微信式的左右聊天布局，但不复制真实社交平台品牌资产；页面顶部持续显示“虚拟角色聊天 Demo”。

### 10.2 交互流程

1. 首次打开页面，调用 GET /api/characters。
2. 用户选择角色，读取 localStorage 中的 user_id；没有则生成随机 demo 用户标识。
3. 调用 POST /api/conversations 获取会话。
4. 加载历史消息。
5. 用户发送消息，立即把用户气泡加入本地列表。
6. 设置 isTyping=true，禁用重复提交。
7. 如果后端正在生成 TTS，保持正在输入状态直到文字/图片/语音消息都准备好。
8. 接收响应后按 delay_ms 逐条追加 assistant 消息。
9. 所有消息展示完成后 isTyping=false，并更新 header 中的场景摘要。
10. 刷新时重新从后端读取，不依赖前端内存。

消息组件必须区分：

- text：普通气泡。
- image：带圆角和最大宽度的本地图片。
- audio：微信式短语音气泡，显示时长和播放按钮；点击后通过 HTMLAudioElement 播放。
- 正在输入：三个跳动圆点，不写成“AI 正在输入”。

audio 组件默认 preload=metadata、不自动播放；同时保留可访问的 transcript 展开入口。语音生成失败时服务端返回普通 text，前端不显示空的语音气泡。

### 10.3 前端状态

~~~text
ChatStore
├─ characters
├─ selectedCharacter
├─ conversationId
├─ messages
├─ isTyping
├─ isSending
├─ voiceEnabled
├─ sceneSummary
├─ relationshipSummary
└─ error
~~~

第一版可不引入 Pinia，使用 App.vue + composable 管理即可；如果组件增多，再引入 Pinia。

## 11. uv 与运行方式

Python 项目以 pyproject.toml 为依赖声明，以 uv.lock 为可复现锁文件。

初始化和安装：

~~~powershell
uv venv --python 3.12
uv sync
~~~

准备环境变量：

~~~powershell
Copy-Item .env.example .env
~~~

初始化 SQLite 和 Demo 角色：

~~~powershell
uv run python -m app.seed
~~~

启动后端：

~~~powershell
uv run uvicorn app.main:app --reload --port 8000
~~~

启动前端：

~~~powershell
Set-Location frontend
npm install
npm run dev
~~~

前端通过 Vite proxy 把 /api 和 /static 转发到 http://127.0.0.1:8000。

## 12. 测试与验收

### 12.1 后端单元测试

- BehaviorDecision 合法 JSON、缺字段、未知枚举和越界值。
- LLMService 最大 3 次调用，不出现无限重试。
- 关系四项 delta 合并和 0..100 clamp。
- 情绪衰减不会重置为默认值。
- 场景只按允许的状态机转移。
- 照片规则覆盖 send、decline、delay、无资产和真实货币条件降级。
- 语音规则覆盖 never、on_request、occasional、TTS 禁用和超长文本。
- TTS 失败时文字回复仍然生成并持久化，成功时 audio_path 只能位于允许目录。
- memory 去重和敏感信息过滤。
- graph 每条 conditional path 都能执行。

### 12.2 API 测试

- seed 后能读取三个角色。
- 创建同一 user_id + character_id 返回同一会话。
- 发送消息后 user/assistant 消息和 conversation JSON 状态同时落库。
- 发送照片后 message_type=image 且 image_path 来自角色白名单。
- 请求发语音后 message_type=audio、audio_url 和时长可读取；刷新后仍可播放。
- 刷新再查询能还原完整消息列表。
- LLM 不可用时仍返回安全短兜底，并明确记录失败。

### 12.3 前端验收

- 角色列表可切换。
- 用户消息靠右，角色消息靠左。
- 图片气泡正常显示。
- 语音气泡点击可播放，默认不自动播放，能展开 transcript。
- 多条回复按 delay_ms 逐条出现。
- 请求期间显示正在输入，不能重复发送。
- 刷新后历史消息仍在。
- 页面始终能看到虚拟角色标识。

静态测试、后端单测、前端构建和真实运行验收分别记录；通过 Python 测试不等于已经验证真实 OpenAI Compatible API、真实浏览器流程或生产部署。

## 13. 实施顺序

### Milestone 1：先跑通主链

1. uv 项目和配置。
2. SQLAlchemy 四表模型、初始化和 seed。
3. Character/Conversation/Message API。
4. ChatState、load_context、behavior_decision、reply_generation。
5. state_update 和事务持久化。
6. Vue 角色列表、聊天气泡、刷新恢复。

此时 scene、emotion 和 image 先使用最小规则，但 Graph 节点接口已经固定。

### Milestone 2：接入完整条件分支

1. route_behavior conditional edge。
2. scene_judgment 状态机。
3. image_judgment、AssetResolver 和本地图片消息。
4. emotion 延续与衰减。
5. 正在输入和多条消息延迟。

### Milestone 3：接入 TTS 语音分支

1. 增加 voice_policy、voice_judgment 和 route_voice。
2. 实现 TTSService 的豆包双向流式 WebSocket 调用。
3. 接收 PCM/流式音频，封装为本地 WAV（或保存 mp3/ogg_opus），写入 audio_path 和 duration_ms。
4. Vue 语音气泡、点击播放和 transcript 展开。
5. 验证 TTS 失败时文字回复不丢失。

### Milestone 4：补齐长期记忆和体验

1. memory_extraction 结构化输出。
2. 记忆去重、重要度和检索。
3. 三个 Demo 角色的独立人设。
4. 错误兜底、日志和测试覆盖。
5. README、启动截图和真实兼容接口验收记录。

## 14. 关键设计结论

- LangGraph 负责“决定角色这一轮怎么做”的完整状态流，不把聊天逻辑拆成普通 if/else 服务链。
- BehaviorDecision、ReplyPlan、MemoryExtraction 都使用严格结构化输出；模型只能给业务建议，不能直接写数据库、选任意文件或发起交易。
- scene_judgment、image_judgment、state_update 以确定性规则为主，把最容易失控的关系、剧情和图片权限留在代码中。
- voice_judgment、tts_generation 作为可选媒体分支接入，TTS 失败不会阻断文字聊天。
- SQLite 只保留四张核心表，关系/情绪/场景直接存 conversations JSON，方便从 0 运行。
- 角色回复保持沉浸式、短句化和强人设，但产品永远明确这是虚拟角色；现实身份、金钱和高风险请求触发透明安全边界。
- 第一版使用 JSON + 前端延迟展示实现“正在输入”和多气泡效果，使用本地音频文件实现 TTS，避免为了聊天 Demo 过早引入 SSE、Redis 或复杂流式基础设施。
