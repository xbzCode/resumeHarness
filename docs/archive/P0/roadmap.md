# P0 迭代规划：Agent 核心可用版

**目标**：Resume Agent 核心能力跑通——精简版 RuntimeBundle 构建、Agent Loop、DeepSeek 对接、记忆注入、Skill 加载，通过 CLI 或最简 HTML 页面可验证完整对话流程。

> **设计原则**：P0 聚焦 agent 后端功能，不涉及认证和前端 UI 开发。Web 端仅提供一个极简 HTML 页面用于功能验证。开发模式使用默认 user_id `dev_user`。

## P0-1：项目骨架 + OpenHarness 裁剪 (3 天) ✅ 已完成

| 任务 | 说明 |
|------|------|
| 创建 `resume_agent/` 包结构 | 按架构文档建立目录和模块 |
| 实现 `build_resume_runtime()` | 精简版 RuntimeBundle 构建，跳过本地工具 |
| 接入 DeepSeek API | 配置 OpenAICompatibleClient，支持多 Key 轮询 |
| 验证 Agent Loop | 单元测试：提交 prompt → 流式返回 → 工具调用 |

**验收标准**：`resume_agent` 包可 import，`build_resume_runtime()` 可创建能对话的 QueryEngine。

## P0-2：简历领域提示词 + Skill + 记忆 (4 天) ✅ 已完成

| 任务 | 说明 |
|------|------|
| 编写 `resume-skill.md` | 简历优化的领域知识 |
| 系统提示词模板 | 角色定义 + 输出格式约束 |
| 提示词组装逻辑 | 复用 `prompts/context.py`，注入 resume-skill + 用户记忆 |
| 用户记忆加载 | 按 user_id 加载记忆目录，注入系统提示词 |
| `memory_write` 工具 | LLM 主动调用写入记忆文件 |
| `skill_loader` 工具 | LLM 主动加载 skill 内容到上下文 |

**验收标准**：对话中要求生成简历，LLM 输出结构化的 Markdown 简历内容；LLM 可通过 `memory_write` 持久化用户偏好。

## P0-3：SSE 对话端点 + 极简验证页面 (3 天) ✅ 已完成

| 任务 | 说明 |
|------|------|
| FastAPI 应用骨架 | 路由注册、中间件、CORS |
| `POST /api/chat` SSE 端点 | SSE 流式对话 |
| `SessionPool` 实现 | 单用户单会话，消息历史内存存储 |
| StreamEvent → SSE 序列化 | 将 StreamEvent 序列化为 SSE 格式 |
| 极简 HTML 验证页面 | 单文件 HTML + fetch SSE |

**验收标准**：通过极简 HTML 页面或 curl 发送 prompt，可收到 SSE 流式回复。
