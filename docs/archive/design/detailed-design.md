# 详细设计

> ⚠️ **过时声明**：本文档为初始设计基准，系统已迭代至 P4 阶段，部分设计已演进。当前实际实现状态请以 `docs/已实现功能.md` 为准。
> 主要变更：
> - 模板从 3 套扩展到 7 套，引入 template.json 元数据规范 + 注册表
> - SkillLoaderTool 从仅支持 resume-skill 扩展为支持所有已注册技能，引入 Front Matter 规范
> - memory_write 白名单从 3 个文件扩展到 4 个（+custom_instructions.md）
> - MCP 新增 McpServerBase 共享框架、annotations 规范、JD 抓取服务
> - 系统提示词外置为 .md 模板文件，新增用户自定义指令注入
> - LLM 配置供应商中立化
> - 简历新增评分、多轮优化、原地编辑、拖拽排序、DOCX/HTML 下载、分享链接

## 1. 精简版 RuntimeBundle 构建

### 1.1 设计目标

原版 `build_runtime()` 为本地 CLI 场景设计，创建了 MCP 子进程、43+ 本地工具、沙箱等重量级对象。Resume Agent 只需要 LLM 对话 + 记忆 + MCP HTTP + Skill，需精简构建。

### 1.2 精简构建函数

```python
# resume_agent/runtime.py

async def build_resume_runtime(
    *,
    user_id: str,
    session_id: str | None = None,
    model: str | None = None,
    system_prompt: str | None = None,
    session_backend: SessionBackend | None = None,
    extra_skill_dirs: tuple[str, ...] = (),
) -> RuntimeBundle:
    """构建精简版 RuntimeBundle，跳过本地工具和 MCP stdio。"""
```

### 1.3 与原版 build_runtime() 的差异

| 环节 | 原版 | 精简版 |
|------|------|--------|
| API Client | 多 Provider 支持 | 仅 OpenAICompatibleClient → DeepSeek |
| MCP Manager | stdio + HTTP，每会话创建 | 仅 HTTP，进程级单例共享 |
| Tool Registry | 43+ 内置工具 + MCP 工具 | 仅 MCP 工具 + skill 工具 + web_fetch + memory_write |
| Permission | DEFAULT 模式需交互确认 | 固定 AUTO 模式 |
| Hook | 加载项目级 + 用户级 hooks | 仅加载全局 hooks |
| Sandbox | 可选 | 不创建 |
| Swarm | 可选 | 不创建 |
| System Prompt | 注入环境信息 + CLAUDE.md | 注入用户记忆 + resume-skill.md |

### 1.4 共享单例 vs 每会话创建

| 对象 | 生命周期 | 原因 |
|------|----------|------|
| OpenAICompatibleClient | 进程级单例 | 连接池复用，10 并发共享；支持多 API Key 轮询 |
| McpClientManager | 进程级单例 | HTTP 连接复用，避免重复建立 |
| ToolRegistry | 进程级单例 | 工具定义不变，动态 MCP 工具由 McpClientManager 管理；用户级 MCP 认证信息在执行层按 user_id 动态注入（详见 7.3 节） |
| HookExecutor | 进程级单例 | 全局钩子共享 |
| QueryEngine | 每会话 | 对话历史独立 |
| Conversation Messages | 每会话 | 隔离 |
| User Memory | 每用户 | 按 user_id 加载对应记忆目录 |

### 1.5 开发模式默认 user_id

P0/P1 阶段为开发模式，不要求认证。默认 user_id 通过环境变量 `DEFAULT_USER_ID` 配置，未设置时默认为 `dev_user`。所有请求在无认证中间件时使用此默认值。

---

## 2. 会话池管理

### 2.1 设计

```python
# resume_agent/session_pool.py

class ResumeSessionPool:
    """管理多用户并发会话，LRU 淘汰空闲会话。"""

    def __init__(self, max_sessions: int = 20, idle_timeout: int = 1800):
        self._bundles: dict[str, RuntimeBundle] = {}   # session_key → bundle
        self._last_access: dict[str, float] = {}        # session_key → timestamp
        self._max_sessions = max_sessions
        self._idle_timeout = idle_timeout

    async def get_or_create(self, user_id: str, session_id: str | None = None) -> RuntimeBundle:
        """获取已有会话或创建新会话。"""

    async def release(self, session_key: str) -> None:
        """标记会话空闲，不立即销毁。"""

    async def evict_idle(self) -> int:
        """淘汰超时空闲会话，返回淘汰数量。"""
```

### 2.2 会话 Key 设计

```
session_key = f"{channel}:{user_id}:{session_id or 'default'}"

示例:
  web:user_abc:default        — Web 端用户 abc 的默认会话
  feishu:user_xyz:thread_123  — 飞书用户 xyz 的线程会话
  wechat:user_123:default     — 微信用户 123 的默认会话
```

### 2.3 淘汰策略

- 定时任务每 5 分钟扫描 `_last_access`
- 超过 `idle_timeout`（30 分钟）未访问的会话，保存快照后销毁
- 会话数超过 `max_sessions`（20）时，强制淘汰最早访问的会话
- 销毁前调用 `session_storage.save_snapshot()` 持久化对话历史

---

## 3. 用户记忆系统

### 3.1 记忆文档结构

每个用户目录下维护以下记忆文件：

| 文件 | 内容 | 更新时机 |
|------|------|----------|
| `memory/简历原文.md` | 用户上传的原始简历内容 | 用户上传/更新简历时 |
| `memory/职业偏好.md` | 用户表达的求职偏好和写作风格 | 对话中提取 + 用户手动编辑 |
| `memory/优化历史.md` | 历次简历优化的要点记录 | 每次生成简历后追加 |
| `memory/技能标签.md` | 用户的技能标签和经验年限 | 对话中提取 + 用户手动编辑 |

### 3.2 记忆注入方式

复用 OpenHarness 的 `prompts/context.py` 机制，在构建 system prompt 时注入用户记忆：

```python
# resume_agent/prompts.py

async def build_resume_system_prompt(
    user_id: str,
    latest_user_prompt: str | None = None,
) -> str:
    """构建简历 Agent 的系统提示词，注入用户专属记忆。"""

    # 1. 基础角色提示词
    base_prompt = RESUME_AGENT_SYSTEM_PROMPT

    # 2. 加载用户记忆文件
    memory_dir = get_user_memory_dir(user_id)
    memory_texts = load_memory_documents(memory_dir)

    # 3. 加载 resume-skill.md
    skill_text = load_resume_skill()

    # 4. 组装
    parts = [base_prompt]
    if memory_texts:
        parts.append("\n## 用户专属记忆\n" + memory_texts)
    if skill_text:
        parts.append("\n## 简历优化技能指南\n" + skill_text)
    return "\n".join(parts)
```

### 3.3 "越用越好用"的实现路径

```
第 1 次使用: 用户上传简历 → 存入 memory/简历原文.md
             → 生成时提示词包含原文 + resume-skill.md

第 2 次使用: 提示词包含原文 + 上次优化记录 + resume-skill.md
             → 用户反馈"不要用 STAR 法式" → LLM 调用 memory_write 写入 memory/职业偏好.md

第 3 次使用: 提示词包含原文 + 偏好 + 历史记录 + resume-skill.md
             → 自动遵循用户偏好生成，无需重复说明
```

### 3.4 记忆容量控制

- `简历原文.md` 最大 16KB（超出自动摘要），其他记忆文件最大 4KB（超出自动摘要）
- 优化历史只保留最近 10 条
- 总记忆注入不超过 8K tokens，超出时按相关性截断
- 复用 `services/compact/` 的 token 估算逻辑

### 3.5 记忆自动提取机制

用户在对话中表达的偏好、技能等信息，通过 LLM 主动调用 `memory_write` 工具写入记忆文件，实现"越用越好用"。

#### 3.5.1 memory_write 工具定义

```python
# resume_agent/tools/memory_write.py

class MemoryWriteTool:
    """记忆写入工具，供 LLM 在对话中主动调用。"""

    name = "memory_write"
    description = (
        "将用户表达的偏好、技能、经验等信息写入用户记忆文件。"
        "当用户在对话中明确表达了求职偏好、写作风格、技能标签等信息时，"
        "应主动调用此工具持久化，以便后续对话自动遵循。"
    )

    parameters = {
        "doc_name": {
            "type": "string",
            "enum": ["职业偏好.md", "技能标签.md", "优化历史.md"],
            "description": "目标记忆文件名"
        },
        "content": {
            "type": "string",
            "description": "要追加或更新的内容（Markdown 格式）"
        },
        "mode": {
            "type": "string",
            "enum": ["append", "replace"],
            "description": "追加还是替换（偏好用 append）"
        }
    }
```

#### 3.5.2 触发时机

- 用户说"我偏好 XX 风格" → LLM 调用 `memory_write(doc_name="职业偏好.md", content="...", mode="append")`
- 用户提到新的技能 → LLM 调用 `memory_write(doc_name="技能标签.md", content="...", mode="append")`
- 每次简历生成完成后 → LLM 调用 `memory_write(doc_name="优化历史.md", content="...", mode="append")`
- 用户上传/更新简历 → 通过 API 端点直接写入 `简历原文.md`（不经过 LLM）

#### 3.5.3 写入保护

- `简历原文.md` 不允许 LLM 通过 `memory_write` 修改（仅通过上传 API）
- 每次写入前检查文件大小，超出容量则自动摘要旧内容再追加
- 写入操作记录日志，便于追溯

---

## 4. Web API 设计

### 4.1 SSE 对话端点（主方案）

SSE 为对话流式传输的主要协议，其余数据通信使用 FastAPI JSON。

```
POST /api/chat
Content-Type: application/json
Authorization: Bearer {jwt_token}   // P2 阶段启用，P0/P1 开发模式下不要求

请求体:
{
  "prompt": "帮我优化简历，投递这个岗位：...",
  "session_id": "abc123"            // 可选，续接已有会话
}

→ Response: text/event-stream

data: {"type": "text_delta", "text": "根据您的简历和岗位需求..."}

data: {"type": "tool_execution_started", "tool_name": "mcp__pdf__convert", "tool_input": {"content": "...", "format": "pdf"}}

data: {"type": "tool_execution_completed", "tool_name": "mcp__pdf__convert", "output": "PDF 已生成", "is_error": false}

data: {"type": "assistant_turn_complete", "usage": {"input_tokens": 1200, "output_tokens": 800}}
```

#### 4.1.1 SSE 认证方式

- **P0/P1（开发模式）**：不要求认证，请求中无需 Authorization header，使用默认 user_id `dev_user`
- **P2（正式模式）**：通过 `Authorization: Bearer {jwt_token}` header 传递 JWT，中间件验证后注入 user_id
- 不支持 URL query 传 token（避免日志泄露风险）

#### 4.1.2 SSE 连接生命周期

- **超时**：单个 SSE 连接最长 30 分钟，超时后发送 `data: {"type": "connection_timeout"}` 并关闭
- **心跳**：每 15 秒发送 `data: {"type": "ping"}` 保持连接活跃
- **断连重连**：客户端重连时携带 `session_id` 续接已有会话
- **并发限制**：同一用户同时只允许 1 个活跃 SSE 连接，新连接自动关闭旧连接

#### 4.1.3 SSE 事件类型

| 事件类型 | 方向 | 说明 |
|----------|------|------|
| `text_delta` | 服务端→客户端 | 逐字文本增量 |
| `tool_execution_started` | 服务端→客户端 | 工具开始执行通知 |
| `tool_execution_completed` | 服务端→客户端 | 工具执行结果 |
| `status` | 服务端→客户端 | 系统状态消息（重试/压缩等） |
| `error` | 服务端→客户端 | 错误事件 |
| `assistant_turn_complete` | 服务端→客户端 | 本轮对话完成（含 usage） |
| `ping` | 服务端→客户端 | 心跳保活 |

### 4.2 REST API 端点

| 方法 | 路径 | 说明 | 阶段 |
|------|------|------|------|
| POST | `/api/chat` | SSE 流式对话 | P0 |
| GET | `/api/resume/{resume_id}/download` | 下载生成的简历 (PDF/Markdown) | P1 |
| GET | `/api/resume/{resume_id}/preview` | 预览简历内容 | P1 |
| GET | `/api/resume/templates` | 获取可用简历模板列表 | P1 |
| GET | `/api/memory` | 获取当前用户记忆文档列表 | P1 |
| PUT | `/api/memory/{doc_name}` | 更新记忆文档内容 | P1 |
| DELETE | `/api/memory/{doc_name}` | 删除记忆文档 | P1 |
| POST | `/api/memory/upload` | 上传简历原文 | P1 |
| GET | `/api/tools` | 查询可用工具列表 | P1 |
| GET | `/api/mcp/status` | MCP 服务状态 | P1 |
| GET | `/api/skills` | Skill 列表 | P1 |
| GET | `/api/sessions` | 列出用户历史会话 | P1 |
| GET | `/api/sessions/{id}` | 加载历史会话 | P1 |
| POST | `/api/auth/register` | 用户注册 | P2 |
| POST | `/api/auth/login` | 用户登录，返回 JWT | P2 |
| GET | `/api/auth/profile` | 获取当前用户信息 | P2 |

### 4.3 WebSocket 备选方案（暂不实现）

如后续有双向实时通信需求（如权限交互弹窗），可补充 WebSocket 端点。当前以 SSE 为主，不实现 WebSocket。

### 4.4 端到端请求处理管线

```
用户发送消息
  ↓
POST /api/chat {prompt, session_id}
  ↓
[认证中间件] JWT 解析 → user_id（P0/P1 开发模式下跳过，使用默认 user_id dev_user）
  ↓
SessionPool.get_or_create(user_id, session_id)
  ↓
加载用户上下文：
  ├── 用户记忆文件（memory/简历原文.md、职业偏好.md 等）
  ├── 用户偏好 Settings（简历模板偏好、语言风格等）
  └── resume-skill.md 领域技能
  ↓
build_resume_system_prompt() 组装系统提示词
  ↓
QueryEngine.submit_message(prompt)
  ↓
run_query() — Agent Loop
  ├── auto_compact_if_needed()
  ├── OpenAICompatibleClient.stream_message() → DeepSeek API
  ├── tool_use? → execute_tool()
  │   ├── memory_write (记忆写入)
  │   ├── web_fetch (网页抓取)
  │   ├── mcp__pdf__convert (HTTP MCP)
  │   ├── mcp__email__send (HTTP MCP)
  │   └── skill (resume-skill.md 加载)
  └── StreamEvent 流
  ↓
StreamEvent → SSE event 序列化 → 流式推送
  ↓
客户端接收 SSE 事件流，渲染对话内容
```

---

## 5. 飞书/微信渠道适配

### 5.1 飞书适配

复用 OpenHarness 已有的 `channels/impl/feishu.py`，核心流程：

```
飞书开放平台 → Event Subscription (HTTP Webhook)
  → FeishuAdapter.handle_event()
  → 验证 signature + token
  → 解析为 InboundMessage(channel="feishu", sender_id=..., content=...)
  → MessageBus.publish_inbound()
  → GatewayBridge → SessionPool → QueryEngine
  → 回复 → OutboundMessage → FeishuAdapter.send_message()
```

用户映射：飞书 `open_id` → 系统 `user_id`，首次消息自动创建用户并初始化记忆目录。

### 5.2 微信/企微适配

新增 `resume_agent/wechat_adapter.py`，实现 `ChannelAdapter` 接口：

```python
class WeChatAdapter:
    """微信/企业微信渠道适配器。"""

    async def start(self, bus: MessageBus) -> None:
        """启动 Webhook 监听。"""

    async def stop(self) -> None:
        """停止监听。"""

    async def send_message(self, message: OutboundMessage) -> None:
        """发送消息到微信用户。"""
```

**企业微信**：使用企业微信 API 的接收消息 + 发送消息接口
**个人微信**：使用微信客服 API 或第三方 webhook（如 Server酱）

消息长度限制处理：
- 微信单条消息限制 2048 字符
- 超长简历分多条发送，附加"完整版请访问 Web 端下载"链接

### 5.3 ohmo 复用边界

从 OpenHarness 的 `ohmo/` 模块中仅复用以下具体类/模块，其他不引入：

| 复用类 | 来源 | 用途 |
|--------|------|------|
| `MessageBus` | `ohmo/gateway/` | 消息总线，inbound/outbound 分发 |
| `GatewayBridge` | `ohmo/gateway/` | 渠道消息到 SessionPool 的桥接 |
| `ChannelAdapter` 基类 | `ohmo/channels/` | 渠道适配器接口定义 |
| `InboundMessage` / `OutboundMessage` | `ohmo/channels/` | 消息数据模型 |

---

## 6. 简历渲染与下载

### 6.1 渲染管线

采用**结构化数据驱动**的渲染管线，将 LLM 输出的 Markdown 解析为结构化的 `ResumeData` 对象，再通过 Jinja2 HTML 模板渲染为 PDF/HTML，实现数据与展示完全分离。

```
LLM 输出 Markdown 简历（使用标记分隔简历正文与建议内容）
  ↓
【流式阶段】Markdown 通过 SSE text_delta 推送到前端（自动过滤标记标签）→ 前端显示 Markdown 文本
  ↓
LLM 输出完毕
  ↓
_extract_resume_content(): 基于标记提取纯净简历 Markdown（主路径）/ 白名单章节过滤（降级路径）
  ↓
resume_parser.py: Markdown → ResumeData 结构化解析
  ↓
【完成阶段】
  ├── 保存简历快照：
  │   ├── ResumeData JSON → ~/.resume_agent/users/{user_id}/resumes/{resume_id}.json
  │   └── Markdown 原文  → ~/.resume_agent/users/{user_id}/resumes/{resume_id}.md
  ├── SSE resume_data 事件推送结构化数据到前端
  └── 前端收到后自动升级为 ResumePreview 组件渲染
  ↓
【PDF 下载】
GET /api/resume/{resume_id}/download?format=pdf&template=professional
  ↓
ResumeData + Jinja2 HTML 模板 → 完整 HTML
  ↓
weasyprint / xhtml2pdf → PDF 文件流
```

#### 6.1.1 渲染管线设计原则

| 原则 | 说明 |
|------|------|
| 数据与展示分离 | `ResumeData` 是唯一数据源，前端组件和 PDF 渲染共用 |
| 模板完全自由 | 每套模板是独立的 Jinja2 HTML+CSS 文件，布局完全自由 |
| 流式优先 | Markdown 流式输出保证用户体验（有进度感），完成后自动升级 |
| 容错解析 | Markdown 解析器对 LLM 输出格式不一致有容错能力 |
| 渲染引擎降级 | weasyprint → xhtml2pdf → fpdf2（逐级降级） |
| 标记分隔 | LLM 输出用 `<!--RESUME-->` / `<!--/RESUME-->` 标记包裹简历正文，确保截取边界可靠 |

#### 6.1.2 简历输出标记分隔机制

LLM 生成简历时，经常在简历正文后附带"优化要点"、"修改建议"等非简历内容。传统黑名单截断方式无法穷举所有可能的标题变体，导致非简历内容泄漏到 ResumeData 渲染中。

**解决方案**：在系统提示词中要求 LLM 使用 HTML 注释标记 `<!--RESUME-->` / `<!--/RESUME-->` 包裹简历正文，建议内容放在标记之外。

```
LLM 输出示例：
<!--RESUME-->
# 张三
联系方式 | zhangsan@email.com | 138xxxx1234 | 北京

## 个人简介
5年前端开发经验...

## 工作经历
### 高级前端工程师 - XX科技（2021.06 - 至今）
- **核心成果1**：...
- **核心成果2**：...

## 教育背景
### 本科 - 计算机科学 - XX大学（2014.09 - 2018.06）

## 专业技能
- **前端框架**：React、Vue、Angular
- **工程化**：Webpack、Vite、CI/CD

## 项目经历
### 电商平台重构 - 核心开发（2022.01 - 2022.12）
- **项目描述**：...
- **核心贡献**：...
<!--/RESUME-->

## 优化要点
- 建议增加量化数据
- 建议突出团队协作经验
```

**截取策略（双路径保障）**：

| 路径 | 触发条件 | 实现方式 | 可靠性 |
|------|----------|----------|--------|
| **标记提取**（主路径） | LLM 输出包含 `<!--RESUME-->` 标记 | 正则提取标记间内容 | 高：标记边界明确，不受标题变体影响 |
| **白名单过滤**（降级路径） | LLM 未使用标记（违反提示词约束） | 只保留已知简历章节（个人简介/工作经历/教育背景/专业技能/项目经历），丢弃其他章节 | 中高：无需穷举黑名单，仅保留已知有效章节 |

**流式标记过滤**：流式推送 `text_delta` 时，自动过滤 `<!--RESUME-->` / `<!--/RESUME-->` 标记文本，确保前端 Markdown 预览不显示标记标签。

**设计优势**：
1. **边界可靠**：标记比黑名单正则可靠得多，不依赖 LLM 对"优化要点"等标题的措辞
2. **向后兼容**：未使用标记时自动降级到白名单过滤，不破坏已有功能
3. **前端无感**：标记在流式推送中被过滤，用户看不到标记标签
4. **建议可见**：标记外的建议内容仍通过 `text_delta` 推送，用户可在 Markdown 中看到

#### 6.1.2 weasyprint 渲染安全限制

weasyprint 渲染 PDF 时内存峰值较高（单个复杂 PDF 可达 200-500MB），10 并发场景下可能 OOM。

应对策略：
- **渲染队列**：同时只允许 1 个 weasyprint 渲染任务，其余排队等待
- **超时保护**：单个渲染任务最长 60 秒，超时则返回错误
- **P3 优化**：使用 MCP PDF 服务（独立进程/容器）隔离渲染，避免影响主服务

### 6.2 简历结构化数据模型

```python
# resume_agent/models/resume_data.py

class ContactInfo(BaseModel):
    """联系方式"""
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    website: str | None = None
    linkedin: str | None = None
    wechat: str | None = None
    raw_text: str | None = None      # 原始文本（兜底）

class WorkExperience(BaseModel):
    """工作经历"""
    title: str                        # 职位
    company: str                      # 公司名称
    period: str                       # 时间段（YYYY.MM - YYYY.MM）
    highlights: list[str]             # 核心成果列表

class Education(BaseModel):
    """教育背景"""
    degree: str                       # 学位
    major: str                        # 专业
    school: str                       # 学校
    period: str                       # 时间段
    achievements: list[str] = []      # 关键成就

class SkillCategory(BaseModel):
    """技能分类"""
    category: str                     # 技能类别名称
    skills: list[str]                 # 技能列表

class ProjectExperience(BaseModel):
    """项目经历"""
    name: str                         # 项目名称
    role: str | None = None           # 角色
    period: str | None = None         # 时间段
    description: str | None = None    # 项目描述
    contributions: list[str]          # 核心贡献

class ResumeData(BaseModel):
    """简历结构化数据模型"""
    name: str                         # 姓名
    contact: ContactInfo              # 联系方式
    summary: str | None = None        # 个人简介
    experience: list[WorkExperience] = []   # 工作经历
    education: list[Education] = []         # 教育背景
    skills: list[SkillCategory] = []        # 专业技能
    projects: list[ProjectExperience] = []  # 项目经历
```

#### 6.2.1 数据模型设计要点

- **Pydantic v2 模型**：所有字段可选值用 `| None`，必填字段无默认值
- **容错字段**：`ContactInfo.raw_text` 保留原始文本，当联系方式无法结构化时兜底
- **列表有序**：`experience`、`education` 等列表保持 LLM 输出的顺序（已按时间倒序）
- **JSON 序列化**：`ResumeData.model_dump_json()` / `ResumeData.model_validate_json()` 用于持久化和 SSE 传输

### 6.3 Markdown → ResumeData 解析器

```python
# resume_agent/resume_parser.py

def parse_markdown_to_resume_data(markdown_content: str) -> ResumeData:
    """将 LLM 输出的 Markdown 简历解析为结构化 ResumeData 对象。

    解析策略：
    1. 按 ## 二级标题分割章节（个人简介/工作经历/教育背景/专业技能/项目经历）
    2. 按三级标题 ### 分割条目（每个工作/教育/项目条目）
    3. 按列表项提取要点
    4. 联系方式从姓名下方的文本行解析
    5. 对格式不一致的 LLM 输出做容错处理
    """
```

#### 6.3.1 解析容错策略

| 场景 | 处理方式 |
|------|----------|
| 缺少某个章节 | 对应列表为空，不影响其他章节解析 |
| 联系方式格式不统一 | 尝试正则匹配 email/phone/location，失败时存入 `raw_text` |
| 三级标题格式不一致 | 容忍 `-`、`—`、`()`、`（）` 等分隔符变体 |
| 列表项不是粗体开头 | 整行作为 highlights/contributions 的一个条目 |
| 章节标题用词不同（如"工作经历"vs"工作经验"） | 维护标题别名映射表 |

### 6.4 Jinja2 HTML 模板

每套简历模板是一个**完整的 Jinja2 HTML+CSS 文件**，不依赖 python-markdown 生成 HTML，布局完全自由。

#### 6.4.1 模板文件结构

```
resume_agent/templates/
├── professional.html    # 简洁商务风（双栏侧边栏布局）
├── academic.html        # 学术风（传统单栏居中布局）
└── creative.html        # 创意排版（卡片式布局）
```

#### 6.4.2 模板变量

所有模板接收统一的 `resume_data` 变量（`ResumeData` 实例）：

```html
<!-- 示例：professional.html 关键片段 -->
<h1>{{ resume_data.name }}</h1>
<div class="contact">
    {% if resume_data.contact.email %}<span>{{ resume_data.contact.email }}</span>{% endif %}
    {% if resume_data.contact.phone %}<span>{{ resume_data.contact.phone }}</span>{% endif %}
</div>

{% if resume_data.summary %}
<section class="summary">
    <h2>个人简介</h2>
    <p>{{ resume_data.summary }}</p>
</section>
{% endif %}

{% for exp in resume_data.experience %}
<section class="experience-item">
    <h3>{{ exp.title }} - {{ exp.company }}（{{ exp.period }}）</h3>
    <ul>
    {% for h in exp.highlights %}
        <li>{{ h }}</li>
    {% endfor %}
    </ul>
</section>
{% endfor %}
```

#### 6.4.3 模板设计规范

| 规范 | 说明 |
|------|------|
| A4 页面 | `@page { size: A4; margin: 2cm; }` |
| 中文字体 | `font-family: "SimHei", "Microsoft YaHei", "PingFang SC", sans-serif;` |
| 打印优化 | `@media print` 中避免分页断裂 |
| 容错渲染 | 所有 `{% if %}` 判断，章节为空时不渲染 |
| 双栏布局 | professional 使用 CSS float/flexbox 实现侧边栏（技能+联系方式）+ 主内容区 |

#### 6.4.4 模板渲染代码

```python
# resume_agent/render_pdf_engine.py（新增 Jinja2 渲染方法）

def render_resume_data_to_html(resume_data: ResumeData, template: str = "professional") -> str:
    """使用 Jinja2 模板引擎将 ResumeData 渲染为完整 HTML。

    Args:
        resume_data: 简历结构化数据
        template: 模板名称

    Returns:
        完整 HTML 字符串
    """
    from jinja2 import Environment, FileSystemLoader

    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)
    tmpl = env.get_template(f"{template}.html")

    return tmpl.render(resume_data=resume_data)
```

### 6.5 SSE resume_data 事件

LLM 输出完毕后，后端解析 Markdown 为 `ResumeData`，通过 SSE 推送结构化数据事件，前端收到后自动从 Markdown 显示升级为组件渲染。

#### 6.5.1 事件格式

```json
{
    "type": "resume_data",
    "resume_id": "resume_20260502_abc123",
    "data": {
        "name": "张三",
        "contact": {
            "email": "zhangsan@example.com",
            "phone": "138-xxxx-xxxx",
            "location": "北京"
        },
        "summary": "5年前端开发经验...",
        "experience": [...],
        "education": [...],
        "skills": [...],
        "projects": [...]
    },
    "template_hint": "professional"
}
```

#### 6.5.2 前端处理流程

```
SSE text_delta 流式到达 → 前端 Markdown 渲染（用户看到进度）
  ↓
SSE resume_data 事件到达 → 前端自动替换为 ResumePreview 组件渲染
  ↓
ResumePreview 组件接收 ResumeData → 按 template_hint 选择样式 → 所见即所得
```

### 6.6 简历快照持久化

LLM 生成简历后，将 Markdown 内容和 ResumeData JSON 同时持久化，与对话会话解耦：

```
当 Agent 检测到本轮输出了简历内容时：
  ↓
1. Markdown → ResumeData 解析
2. 保存双格式快照：
   ├── ~/.resume_agent/users/{user_id}/resumes/{resume_id}.json  （ResumeData JSON）
   └── ~/.resume_agent/users/{user_id}/resumes/{resume_id}.md    （Markdown 原文，保留降级能力）
3. SSE 推送：
   ├── resume_generated 事件（resume_id）
   └── resume_data 事件（结构化数据）
```

**设计要点**：
- `resume_id` 格式：`resume_{timestamp}_{random_suffix}`，全局唯一
- 同时保存 JSON 和 MD 两种格式：JSON 用于渲染，MD 用于降级和可读性
- 即使会话被 LRU 淘汰，简历下载端点仍可正常工作
- 每个用户最多保留最近 20 份简历快照，超出自动清理最旧的

### 6.7 简历模板

提供多套简历模板，每套模板是独立的 Jinja2 HTML+CSS 文件，布局完全自由：

| 模板 | 风格 | 布局特征 | 适用场景 |
|------|------|----------|----------|
| `professional` | 简洁商务 | 双栏侧边栏（左：技能+联系方式，右：经历+教育） | 互联网/科技 |
| `academic` | 学术风格 | 传统单栏居中，标题下划线装饰 | 高校/研究所 |
| `creative` | 创意排版 | 卡片式布局，圆角阴影，渐变色块 | 设计/市场 |

模板存储在 `resume_agent/templates/` 目录下，为 Jinja2 HTML+CSS 模板文件。

> **扩展性**：新增模板只需在 `templates/` 目录下添加一个 `.html` 文件，并在 `AVAILABLE_TEMPLATES` 列表中注册，零代码改动。

### 6.8 下载 API

```
GET /api/resume/{resume_id}/download?format=pdf&template=professional

Response:
  Content-Type: application/pdf
  Content-Disposition: attachment; filename="resume_张三_前端工程师.pdf"
```

**渲染路径**：

1. 加载 `{resume_id}.json` → `ResumeData` 对象
2. 若 JSON 不存在（旧快照），加载 `{resume_id}.md` → 解析为 `ResumeData`
3. `ResumeData` + Jinja2 模板 → 完整 HTML → weasyprint/xhtml2pdf → PDF

> **注意**：下载端点使用 `resume_id`（而非 `session_id`），确保会话淘汰后简历仍可下载。

---

## 7. DeepSeek API 集成

### 7.1 配置

复用 `OpenAICompatibleClient`，DeepSeek 走 OpenAI 兼容协议。API Key 等凭证由服务端内置管理，用户无需感知或配置。

#### 7.1.1 配置加载优先级

```
1. 环境变量 DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL
2. 全局配置文件 ~/.resume_agent/settings.json
3. 代码内默认值
```

启动时按优先级加载，若 API Key 缺失则拒绝启动并输出明确错误提示。

#### 7.1.2 配置文件格式

```json
// ~/.resume_agent/settings.json（服务端内置，用户不可见）
{
  "api_format": "openai",
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-chat",
  "api_keys": [
    "sk-xxx",
    "sk-yyy",
    "sk-zzz"
  ]
}
```

> **注意**：`api_keys` 支持配置多个 API Key，用于轮询分摊请求量，避免单 Key 触发速率限制。

#### 7.1.3 启动校验

```python
# resume_agent/runtime.py
def validate_api_config():
    """启动时校验 API 配置，缺少必要配置则抛出异常拒绝启动。"""
    if not settings.api_keys:
        raise ConfigurationError(
            "DeepSeek API Key 未配置。请设置环境变量 DEEPSEEK_API_KEY "
            "或在 ~/.resume_agent/settings.json 中配置 api_keys。"
        )
```

### 7.2 速率限制与多 Key 轮询

DeepSeek Chat 默认约 30 RPM / 1M TPM。10 并发共享单个 Key 可能触发 429。

#### 7.2.1 多 Key 轮询机制

```python
# resume_agent/api_key_pool.py

class ApiKeyPool:
    """API Key 轮询池，按 Key 维护令牌桶，公平分配请求。"""

    def __init__(self, api_keys: list[str], rpm_per_key: int = 30):
        self._keys = api_keys
        self._buckets: dict[str, TokenBucket] = {
            key: TokenBucket(rpm_per_key) for key in api_keys
        }

    async def acquire(self) -> str:
        """获取一个可用的 API Key，若全部达到限额则排队等待。"""

    def report_429(self, key: str) -> None:
        """报告某 Key 收到 429，暂时停用该 Key。"""
```

#### 7.2.2 应对策略

1. **多 Key 轮询**：配置 2-3 个 API Key，通过 `ApiKeyPool` 轮询分配请求
2. **令牌桶限流**：按 API Key 维护令牌桶，请求排队
3. **429 自动重试**：复用 OpenHarness 已有的指数退避重试机制
4. **公平调度**：按用户维度公平排队，避免单用户占满配额

> 注：DeepSeek API Key 由服务端内置管理，用户无需感知或配置。

### 7.3 用户级 MCP 认证动态注入

ToolRegistry 为进程级单例，工具定义全局共享。但部分 MCP 工具（如邮件发送）需要按用户传入不同的认证信息。解决方案：

```
工具执行时：
  1. ToolRegistry 查找工具定义（全局共享）
  2. 执行层从用户上下文获取该用户对应的 MCP headers/auth token
  3. 合并全局配置 + 用户级认证信息，发起 MCP 调用
```

```python
# resume_agent/mcp_auth.py

async def get_mcp_headers(tool_name: str, user_id: str) -> dict:
    """获取 MCP 工具调用时的 headers，合并全局 + 用户级认证。"""
    global_headers = settings.mcp_servers[tool_name].get("headers", {})
    user_headers = load_user_mcp_auth(user_id, tool_name)
    return {**global_headers, **user_headers}
```

### 7.4 模型选择

| 场景 | 推荐模型 | 原因 |
|------|----------|------|
| 简历生成 | deepseek-chat | 综合能力强，性价比高 |
| 长文本分析（多页 JD + 简历） | deepseek-chat | 支持 64K 上下文 |
| 对话压缩 | deepseek-chat | 降级使用，成本可控 |

---

## 8. 用户认证详细设计

> **注意**：认证功能在 P2 阶段实现。P0/P1 阶段为开发模式，不要求认证，使用默认 user_id `dev_user` 直接访问。

### 8.1 JWT 认证流程

```
注册: POST /api/auth/register {username, password, email}
  → 创建用户 → 初始化 ~/.resume_agent/users/{user_id}/ 目录
  → 返回 JWT token

登录: POST /api/auth/login {username, password}
  → 验证密码 → 返回 JWT token

请求: Authorization: Bearer {jwt_token}
  → 中间件验证 → 注入 user_id → 路由处理
```

### 8.2 IM 渠道免登录

飞书/微信用户无需显式登录：
- 首次消息 → 通过 `sender_id` 自动创建用户 → 生成 JWT → 关联 channel + sender_id
- 后续消息 → 通过 channel + sender_id 查找 user_id → 直接处理

### 8.3 Token 存储

```
~/.resume_agent/credentials/
├── jwt_secret.key          # JWT 签名密钥 (启动时自动生成)
└── user_tokens.json        # IM 渠道 token 映射 (channel:sender_id → user_id)
```

---

## 9. web_fetch 工具设计

### 9.1 功能定义

`web_fetch` 工具用于抓取指定 URL 的网页内容，主要场景是用户在对话中提供招聘 JD 链接，Agent 自动抓取并解析岗位需求。

```python
# resume_agent/tools/web_fetch.py

class WebFetchTool:
    """网页内容抓取工具，供 LLM 在对话中主动调用。"""

    name = "web_fetch"
    description = (
        "抓取指定 URL 的网页内容，提取纯文本。"
        "当用户提供招聘链接或需要获取网页内容时，调用此工具。"
        "抓取结果将作为上下文参与后续简历生成。"
    )

    parameters = {
        "url": {
            "type": "string",
            "description": "要抓取的网页 URL"
        },
        "max_length": {
            "type": "integer",
            "description": "返回内容的最大字符数，默认 4000",
            "default": 4000
        }
    }
```

### 9.2 实现要点

- 使用 httpx 异步请求，设置 10 秒超时
- 使用 readability-lxml 或 BeautifulSoup 提取正文，去除导航/广告等噪声
- 返回内容截断到 `max_length` 字符，避免占用过多上下文
- 仅允许 HTTP/HTTPS 协议，禁止 file:// 等本地协议
- 同一 URL 在 5 分钟内缓存结果，避免重复请求

### 9.3 使用流程

```
用户: "帮我优化简历，投递这个岗位：https://job.example.com/position/123"
  ↓
LLM 识别到 URL → 调用 web_fetch(url="https://job.example.com/position/123")
  ↓
web_fetch 抓取网页 → 提取正文 → 返回 JD 描述
  ↓
LLM 结合用户简历 + JD 需求 → 生成匹配岗位的优化简历
```

---

## 10. Skill-to-Tool 映射机制

### 10.1 映射方式

`resume-skill.md` 是领域知识文件，不直接作为可调用工具。Skill 通过以下方式参与 Agent Loop：

- **系统提示词注入**：`resume-skill.md` 的内容在构建 system prompt 时直接注入，LLM 始终拥有简历优化领域知识
- **Skill 工具**：注册一个 `skill` 工具，LLM 可主动调用以重新加载/刷新 skill 内容（用于长对话中 skill 被压缩后重新注入）

```python
# resume_agent/tools/skill_loader.py

class SkillLoaderTool:
    """技能加载工具，供 LLM 主动加载指定 Skill 的完整内容。"""

    name = "skill_loader"
    description = (
        "加载指定技能文件的完整内容到当前上下文。"
        "当需要重新获取简历优化知识时调用。"
    )

    parameters = {
        "skill_name": {
            "type": "string",
            "enum": ["resume-skill"],
            "description": "要加载的技能名称"
        }
    }
```

### 10.2 与 OpenHarness 的对应关系

OpenHarness 中 Skill 系统的设计：skill 文件内容注入 system prompt + 可通过 tool_use 主动加载。Resume Agent 复用此机制，不做额外改造。

---

## 11. 数据存储方案

### 11.1 P0/P1：文件存储

P0/P1 阶段单用户场景，使用文件系统存储：

```
~/.resume_agent/
├── settings.json                    # 全局配置
├── users/
│   └── dev_user/                    # 开发模式默认用户
│       ├── settings.json            # 用户级配置
│       ├── memory/                  # 用户专属记忆
│       ├── sessions/                # 对话历史
│       └── resumes/                 # 生成的简历文件
└── credentials/                     # 认证数据
```

### 11.2 P2：SQLite 迁移

P2 多用户阶段，将用户数据（认证信息、会话元数据、记忆索引）迁移到 SQLite，提升并发安全和查询性能：

```python
# resume_agent/db.py

class ResumeAgentDB:
    """SQLite 数据库管理，替代文件存储。"""

    def __init__(self, db_path: str = "~/.resume_agent/data.db"):
        self._db_path = db_path

    # 用户认证数据
    async def create_user(self, username: str, password_hash: str, email: str) -> str: ...
    async def get_user_by_username(self, username: str) -> dict | None: ...
    async def get_user_by_channel_sender(self, channel: str, sender_id: str) -> dict | None: ...

    # 会话元数据
    async def save_session_meta(self, user_id: str, session_id: str, meta: dict) -> None: ...
    async def list_sessions(self, user_id: str) -> list[dict]: ...

    # 简历快照索引
    async def save_resume_index(self, user_id: str, resume_id: str, path: str, meta: dict) -> None: ...
    async def list_resumes(self, user_id: str) -> list[dict]: ...
    async def get_resume_path(self, resume_id: str) -> str | None: ...

    # 记忆文件内容（大文本仍存文件，SQLite 存索引和元数据）
    async def get_memory_meta(self, user_id: str) -> list[dict]: ...
```

**迁移策略**：
- P2-1 阶段引入 SQLite，认证数据优先迁移
- 记忆文件内容仍保留在文件系统（大文本读写效率更高），SQLite 仅存索引
- 会话快照元数据迁移到 SQLite，快照文件仍存磁盘
- 简历快照索引迁移到 SQLite

---

## 12. 错误处理

### 12.1 全局错误码

| 错误码 | 含义 |
|--------|------|
| 1001 | 用户未认证 |
| 1002 | Token 过期 |
| 2001 | DeepSeek API 调用失败 |
| 2002 | 速率限制，请稍后重试 |
| 3001 | 会话不存在 |
| 3002 | 会话已过期 |
| 4001 | MCP 服务不可用 |
| 4002 | 简历渲染失败 |
| 4003 | 简历不存在（resume_id 无效） |
| 5001 | 记忆文档不存在 |
| 6001 | 网页抓取失败 |

### 12.2 SSE 流式错误处理

SSE 场景下，错误通过 `error` 类型事件推送：

```json
data: {"type": "error", "code": 2001, "message": "DeepSeek API 调用失败，正在重试..."}
```

- 可恢复错误（如 429 重试中）：推送 error 事件后继续流式输出
- 不可恢复错误：推送 error 事件后发送 `data: {"type": "assistant_turn_complete"}` 结束本轮，客户端可重新发送请求

---

## 13. 部署方案

### 13.1 单机部署架构

```
云服务器 (2C4G 轻量级)
├── uvicorn (1 worker, 10 concurrent)
│   └── resume_agent.web.app
├── stdio-to-http MCP proxy (1-2 个)
│   ├── pdf-converter proxy (localhost:9100)
│   └── 其他 stdio MCP 代理
└── nginx
    ├── / → 静态前端文件
    ├── /api → proxy_pass uvicorn HTTP (含 SSE)
    └── /api/chat → proxy_pass uvicorn HTTP (SSE 需禁用缓冲)
```

nginx SSE 配置要点：
```nginx
location /api/chat {
    proxy_pass http://uvicorn;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering off;           # 禁用缓冲，确保 SSE 实时推送
    proxy_cache off;
    proxy_read_timeout 1800s;      # SSE 长连接超时 30 分钟
}
```

### 13.2 进程管理

```bash
# systemd service
[Unit]
Description=Resume Agent Service
After=network.target

[Service]
Type=simple
User=resume-agent
WorkingDirectory=/opt/resume-agent
ExecStart=/opt/resume-agent/venv/bin/uvicorn resume_agent.web.app:app --host 0.0.0.0 --port 8000 --workers 1
Restart=on-failure
Environment=DEEPSEEK_API_KEY=sk-xxx

[Install]
WantedBy=multi-user.target
```

### 13.3 资源预估

| 资源 | 预估用量 | 说明 |
|------|----------|------|
| CPU | 1-2 核 | 主要是网络 I/O，CPU 消耗低 |
| 内存 | 2-4 GB | 10 个 QueryEngine + 消息历史 + MCP 连接 + weasyprint 渲染队列 |
| 磁盘 | 10 GB | 用户数据 + 简历文件 + SQLite 数据库 + 日志 |
| 带宽 | 5 Mbps | 流式文本为主，带宽需求低 |