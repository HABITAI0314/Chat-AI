# 1v1 虚拟角色聊天 Demo

这是一个以 LangGraph 为核心聊天编排的 1v1 虚拟角色聊天 Demo。

当前第一版已经包含：

- Python 3.12 + uv。
- FastAPI + SQLAlchemy + SQLite。
- LangGraph 主链：加载上下文 -> 行为决策 -> 场景判断 -> 回复生成 -> 图片判断 -> 语音判断/TTS -> 状态更新 -> 记忆提取。
- Vue 3 + TypeScript + Vite 聊天页面。
- 三个有独立人设的 Demo 角色。
- 同一前端项目中的角色后台：结构化编辑、草稿校验、测试预览和发布。
- 关系数值、情绪衰减、场景流转、长期记忆提取。
- 本地图片消息和可选豆包双向流式 TTS 语音消息。
- 没有配置 LLM 时仍可用确定性角色兜底完成演示。

页面会持续显示“虚拟角色”标识。角色和茶叶剧情均为虚构，不代表现实个人或真实门店；Demo 不接入支付、红包、转账或真实身份验证。

## 1. 环境要求

- Windows PowerShell。
- Python 3.12。项目的 uv 配置限制为 >=3.12,<3.13。
- uv。
- Node.js 18+ 和 npm。

## 2. 安装 Python 依赖

在项目根目录执行：

~~~powershell
uv venv --python 3.12
uv sync --dev
Copy-Item .env.example .env
~~~

如果当前机器没有 Python 3.12，uv 会按项目约束准备对应解释器。

## 3. 配置 LLM

编辑 .env：

~~~text
LLM_ENABLED=true
OPENAI_BASE_URL=https://your-compatible-endpoint/v1
OPENAI_API_KEY=your-key
OPENAI_MODEL=your-chat-model
~~~

兼容接口需要支持 Chat Completions 和 LangChain 的结构化输出/工具调用格式。没有配置时，将使用代码中的 Demo fallback；这可以用于先验收页面、SQLite、Graph 分支和状态变化。

## 4. 配置 TTS

TTS 默认使用你在 YQ `StudentMockInterview` V2 链路中使用的豆包双向流式接口：

接口参考：[你提供的豆包语音文档](https://docs.volcengine.com/docs/6561/1719100?lang=zh)；当前 V3 双向接口的 [官方 API 参考](https://www.volcengine.com/docs/6561/2532486?lang=zh)。

~~~text
TTS_ENABLED=true
TTS_PROVIDER=doubao_bidirection
DOUBAO_BIDIRECTION_TTS_WEBSOCKET_URL=wss://openspeech.bytedance.com/api/v3/tts/bidirection
DOUBAO_BIDIRECTION_TTS_API_KEY=your-api-key
DOUBAO_BIDIRECTION_TTS_APP_ID=your-app-id
DOUBAO_BIDIRECTION_TTS_RESOURCE_ID=seed-tts-2.0
DOUBAO_BIDIRECTION_TTS_SPEAKER=zh_female_shuangkuaisisi_uranus_bigtts
DOUBAO_BIDIRECTION_TTS_OUTPUT_FORMAT=pcm
DOUBAO_BIDIRECTION_TTS_OUTPUT_SAMPLE_RATE=24000
DOUBAO_BIDIRECTION_TTS_CONNECT_TIMEOUT_SECONDS=10
TTS_MAX_CHARS=180
TTS_TIMEOUT_SECONDS=20
~~~

调用流程是：建立 WebSocket -> 发送连接开始事件 -> 创建会话 -> 提交短文本 -> 接收 PCM 音频块 -> 结束会话。PCM 会在 `data/audio/{conversation_id}` 下封装成 WAV，前端可以直接点击播放。角色卡里的 `fictional-*` 音色标签会安全地回退到 `DOUBAO_BIDIRECTION_TTS_SPEAKER`；如果要使用其他已开通的豆包音色，可直接把真实音色 ID 写进角色的 `voice_policy.voice_id`。

如果要继续使用 OpenAI Compatible `POST /audio/speech`，设置 `TTS_PROVIDER=openai_compatible`，并补充 `TTS_BASE_URL`、`TTS_API_KEY`、`TTS_MODEL`、`TTS_FORMAT`。无论哪种供应商未配置或调用失败，本轮文字回复都会保留，不会让聊天请求失败。

第一版只使用合成音色或已授权的虚构音色，不支持现实人物声音克隆；浏览器不会自动播放语音。

## 5. 初始化和启动

初始化 SQLite 和 Demo 角色：

~~~powershell
uv run python -m app.seed
~~~

启动 FastAPI：

~~~powershell
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
~~~

另开一个 PowerShell 窗口启动前端：

~~~powershell
Set-Location frontend
npm install
npm run dev
~~~

如果本机 8000 端口被其他服务占用，可以临时设置 `VITE_API_TARGET=http://127.0.0.1:8001`，再执行 `npm run dev` 将前端代理切到其他后端端口。

浏览器打开：

~~~text
http://localhost:5173
~~~

后端健康检查：

~~~text
http://127.0.0.1:8000/healthz
~~~

## 6. 主要接口

~~~text
GET  /api/characters
POST /api/conversations
GET  /api/conversations/{id}/messages?user_id=...
POST /api/conversations/{id}/messages
~~~

角色后台默认地址为 `http://localhost:5173/#/admin/characters`，也可以从聊天页左侧的“打开角色后台”进入。后台在 `APP_ENV=dev` 且 `ADMIN_TOKEN` 为空时允许本地访问；非开发环境请设置 `ADMIN_TOKEN`，请求使用 `X-Admin-Token` 请求头。

角色配置保存在 `characters` 表：`profile_json` 是已发布配置，`draft_profile_json` 是草稿；角色编码、名称和头像也分别保存正式值与草稿值。已发布角色保存草稿后仍继续出现在聊天端，发布时才会一次性替换全部正式配置。`data/characters.seed.json` 只负责首次创建苏禾、林晚和沈砚，应用启动时不会覆盖已经由后台修改的角色。

浏览器首次打开时会在 localStorage 中生成 demo user_id，因此同一个浏览器刷新后可以继续已有角色会话。

## 7. Graph 行为

app/graph/builder.py 构建的 Graph 有以下节点：

~~~text
START
  -> load_context
  -> behavior_decision
  -> conditional behavior route
  -> scene_judgment
  -> reply_generation
  -> image_judgment
  -> conditional image route
  -> voice_judgment
  -> conditional voice route
  -> tts_generation
  -> state_update
  -> memory_extraction
  -> END
~~~

当图片或语音条件不满足时，分支会跳过对应媒体节点。行为决策和回复计划使用 Pydantic 结构化输出；模型不可用或输出异常时最多有限重试，之后使用角色 fallback。

## 8. 数据和素材

SQLite 文件默认是 data/chat.db，核心表只有：

- characters
- conversations
- messages
- memories

关系、情绪和场景直接保存在 conversations 的 JSON 字段。角色头像和照片在 app/static/characters，TTS 生成的音频在 data/audio。

## 9. 验证命令

~~~powershell
uv run ruff check app
uv run pytest -q
Set-Location frontend
npm run build
~~~

静态检查和单测不等于真实 LLM/TTS 供应商验收。配置真实兼容接口后，再通过页面验证模型回复、图片条件和语音播放。
