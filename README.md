# 1v1 虚拟角色聊天 Demo

一个基于 **FastAPI + Vue 3 + LangGraph** 的 1v1 虚拟角色聊天 Demo。用户可以选择不同人设的虚拟角色进行对话；系统会结合对话上下文、关系值、情绪和场景决定角色的行为，并按条件生成图片消息和语音消息。

> 本项目中的角色、头像、照片和剧情均为虚构内容。项目不接入支付、红包、转账或真实身份验证。

## 功能概览

- 多虚拟角色聊天：苏禾、林晚、沈砚等 Demo 角色。
- LangGraph 对话编排：上下文加载、行为决策、场景判断、回复生成、媒体判断、状态更新和记忆提取。
- 关系与情绪：维护关系数值、情绪状态、场景状态和长期记忆。
- 多模型模式：配置兼容 OpenAI Chat Completions 的 LLM，或使用内置确定性 fallback 完成演示。
- 图片消息：根据角色行为和场景条件发送角色照片。
- 语音消息：支持豆包双向流式 TTS，也支持 OpenAI Compatible `/audio/speech`。
- 角色后台：编辑草稿、校验配置、测试预览和发布角色配置。
- SQLite 持久化：保存角色、会话、消息和记忆。

## 技术栈

| 层次 | 技术 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite |
| 后端 | Python 3.12、FastAPI、Uvicorn |
| AI 编排 | LangGraph、LangChain、Pydantic 结构化输出 |
| 数据访问 | SQLAlchemy Async、aiosqlite、SQLite |
| 语音 | WebSocket 豆包双向 TTS / OpenAI Compatible TTS |
| 工程工具 | uv、Ruff、Pytest、Vue TSC |

## 系统架构

```text
Vue 3 + Vite 前端
        │ HTTP/JSON
        ▼
FastAPI API 层
        ▼
ChatService / CharacterAdminService
        ▼
LangGraph 对话编排
        ├── 上下文、行为、场景和回复节点
        ├── 图片判断与素材服务
        ├── 语音判断与 TTS 服务
        └── 状态更新与长期记忆提取
        ▼
Domain 规则 + Repository
        ▼
SQLAlchemy Async + SQLite
```

### 后端分层

- `app/api`：HTTP 路由、请求参数和响应 Schema。
- `app/services`：聊天、角色后台、LLM 配置、提示词、素材和 TTS 等应用服务。
- `app/graph`：LangGraph 状态定义、Graph 构建、运行时依赖和节点处理器。
- `app/domain`：关系值、情绪衰减、场景和照片策略等领域规则。
- `app/db`：SQLAlchemy 模型、异步 Session 和 Repository 数据访问。
- `app/static`：角色头像和照片等本地静态素材。

### 一轮消息的数据流

```text
用户消息
  -> POST /api/conversations/{id}/messages
  -> ChatService 加载会话、角色和历史记忆
  -> LangGraph 执行行为决策与回复生成
  -> 按条件追加图片、生成 TTS 音频
  -> 更新关系 / 情绪 / 场景 / 长期记忆
  -> 保存消息并返回前端
```

## LangGraph 执行流程

`app/graph/builder.py` 构建的主图如下：

```text
START
  -> load_context
  -> behavior_decision
  -> prepare_normal / prepare_avoid / prepare_advance / prepare_photo
  -> scene_judgment
  -> reply_generation
  -> image_judgment
  -> [可选] append_image_message
  -> voice_judgment
  -> [可选] tts_generation
  -> state_update
  -> memory_extraction
  -> END
```

行为决策、图片判断和语音判断分别控制条件分支。模型不可用或结构化输出异常时，系统会在有限重试后回退到确定性角色逻辑；图片或 TTS 失败不会丢失本轮文字回复。

## 项目结构

```text
.
├── app/
│   ├── api/                  # FastAPI 路由和 API Schema
│   ├── db/                   # 数据库模型、Session、Repository
│   ├── domain/               # 关系、情绪、场景和媒体策略
│   ├── graph/                # LangGraph 状态、节点和 Graph 构建
│   ├── services/             # 聊天、LLM、TTS、角色后台等服务
│   ├── static/characters/    # 角色头像和照片
│   ├── config.py             # 环境变量配置
│   ├── main.py               # FastAPI 应用入口
│   └── seed.py               # Demo 角色初始化
├── data/
│   └── characters.seed.json  # 首次初始化的角色数据
├── frontend/
│   ├── src/api/              # 前端 API 客户端
│   ├── src/components/       # 聊天和角色后台组件
│   ├── src/types/            # TypeScript 类型
│   └── src/App.vue           # 前端应用入口
├── tests/                    # Python 单元测试
├── pyproject.toml            # Python 和 uv 配置
├── uv.lock                   # Python 依赖锁定文件
└── README.md
```

`docs/` 是本地设计资料目录，已加入 `.gitignore`，不会提交到 Git 仓库。

## 环境要求

- Windows PowerShell（其他系统也可运行，但命令需要相应调整）。
- Python 3.12，项目约束为 `>=3.12,<3.13`。
- [uv](https://docs.astral.sh/uv/)。
- Node.js 18+ 和 npm。

## 快速开始

### 1. 安装后端依赖并创建配置

```powershell
uv venv --python 3.12
uv sync --dev
Copy-Item .env.example .env
```

不配置 LLM 时，项目仍可使用 fallback 模式启动并体验页面、SQLite、Graph 分支和状态变化。

### 2. 配置 LLM（可选）

编辑 `.env`：

```text
LLM_ENABLED=true
OPENAI_BASE_URL=https://your-compatible-endpoint/v1
OPENAI_API_KEY=your-key
OPENAI_MODEL=your-chat-model
```

兼容接口需要支持 Chat Completions，以及 LangChain 所需的结构化输出和工具调用格式。

### 3. 配置 TTS（可选）

豆包双向流式 TTS 示例：

```text
TTS_ENABLED=true
TTS_PROVIDER=doubao_bidirection
DOUBAO_BIDIRECTION_TTS_WEBSOCKET_URL=wss://openspeech.bytedance.com/api/v3/tts/bidirection
DOUBAO_BIDIRECTION_TTS_API_KEY=your-api-key
DOUBAO_BIDIRECTION_TTS_APP_ID=your-app-id
DOUBAO_BIDIRECTION_TTS_RESOURCE_ID=seed-tts-2.0
DOUBAO_BIDIRECTION_TTS_SPEAKER=your-speaker-id
```

如果 TTS 未配置或调用失败，本轮文字消息仍会正常返回。生成的 PCM 会封装为 WAV，保存到 `data/audio/`。

### 4. 初始化并启动后端

```powershell
uv run python -m app.seed
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. 启动前端

在另一个 PowerShell 窗口执行：

```powershell
Set-Location frontend
npm install
npm run dev
```

打开 [http://localhost:5173](http://localhost:5173)。后端健康检查地址为 [http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz)。

## API 概览

```text
GET  /healthz
GET  /api/characters
POST /api/conversations
GET  /api/conversations/{id}/messages?user_id=...
POST /api/conversations/{id}/messages
```

角色后台默认地址为 `http://localhost:5173/#/admin/characters`。开发环境且 `ADMIN_TOKEN` 为空时允许本地访问；非开发环境请配置 `ADMIN_TOKEN`，并通过 `X-Admin-Token` 请求头鉴权。

角色配置使用草稿与正式配置分离的方式：保存草稿不会立即替换聊天端角色，只有发布操作才会一次性更新正式配置。

## 数据与媒体

默认 SQLite 文件为 `data/chat.db`，核心数据表包括：

- `characters`：角色正式配置和草稿配置。
- `conversations`：用户与角色的会话、关系、情绪和场景状态。
- `messages`：对话文本、图片和语音消息。
- `memories`：从对话中提取的长期记忆。

角色图片位于 `app/static/characters/`，TTS 音频位于 `data/audio/`。数据库、环境变量、前端依赖和构建产物均已通过 `.gitignore` 排除。

## 验证命令

```powershell
uv run ruff check app
uv run pytest -q
Set-Location frontend
npm run build
```

以上命令覆盖静态检查、Python 单元测试和前端构建；它们不替代真实 LLM/TTS 供应商、浏览器交互和部署环境验收。

## 许可证

当前仓库为演示项目，未单独声明开源许可证。如需公开分发，请根据实际使用的代码和素材补充许可证及第三方声明。
