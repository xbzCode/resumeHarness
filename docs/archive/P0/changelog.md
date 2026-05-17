# P0 实现记录：Agent 核心可用版

## P0-1：项目骨架 + OpenHarness 裁剪 ✅

| 功能 | 状态 | 说明 |
|------|------|------|
| `resume_agent/` 包结构 | ✅ 已完成 | 包含 api/engine/config/tools/memory/prompts/models/services/skills/templates 等子模块 |
| `build_resume_runtime()` | ✅ 已完成 | 精简版 RuntimeBundle 构建，支持用户记忆注入 + Skill 加载 |
| OpenAICompatibleClient | ✅ 已完成 | DeepSeek/OpenAI 兼容客户端，流式对话，指数退避重试，429/500/502/503 自动重试 |
| ApiKeyPool 多 Key 轮询 | ✅ 已完成 | 令牌桶限流 + 轮询策略，已与 OpenAICompatibleClient 集成，429 自动报告 Key 暂停 |
| QueryEngine | ✅ 已完成 | 对话引擎，支持流式输出、工具调用循环、max_turns 控制、权限检查、Hook 前后置 |
| RuntimeBundle | ✅ 已完成 | 运行时数据类，包含 QueryEngine 及其依赖 |
| 权限检查（AUTO 模式） | ✅ 已完成 | PermissionChecker 固定 FULL_AUTO 模式，敏感路径拦截 |
| Hook 系统（空实现） | ✅ 已完成 | HookExecutor + HookRegistry，P0 阶段不加载 hooks |
| .env 配置加载 | ✅ 已完成 | python-dotenv 自动加载项目根目录 .env 文件 |
| 异常体系 | ✅ 已完成 | 统一错误码（1001-6001）+ ResumeAgentError 层次结构 |
| 上下文压缩（compact） | ✅ 已完成 | 长对话自动压缩，Token 估算 + 阈值判断 + LLM 生成摘要，在 `run_query()` 中集成 |

**关键文件**：
- `resume_agent/runtime.py` — RuntimeBundle 构建 + 进程级单例
- `resume_agent/api/openai_client.py` — OpenAI 兼容客户端
- `resume_agent/api_key_pool.py` — 多 Key 轮询池
- `resume_agent/engine/query_engine.py` — 对话引擎
- `resume_agent/engine/query.py` — 核心工具调用循环
- `resume_agent/config/settings.py` — 全局配置加载
- `resume_agent/exceptions.py` — 统一错误码与异常定义
- `resume_agent/services/compact.py` — 上下文压缩服务

## P0-2：简历领域提示词 + Skill + 记忆 ✅

| 功能 | 状态 | 说明 |
|------|------|------|
| `resume-skill.md` | ✅ 已完成 | 简历优化领域知识：ATS 友好、STAR 法则、量化成果、关键词匹配、不同场景策略 |
| 系统提示词模板 | ✅ 已完成 | 角色定义（简历优化顾问）+ 输出格式约束（Markdown 简历模板）+ 工作原则 + 工具使用规范 |
| 提示词组装逻辑 | ✅ 已完成 | `build_resume_system_prompt(user_id)` 三层组装：角色提示词 + 用户记忆 + resume-skill |
| 用户记忆加载 | ✅ 已完成 | 按 user_id 加载记忆目录，容量控制（简历 16KB/其他 4KB），自动注入系统提示词 |
| `memory_write` 工具 | ✅ 已完成 | 白名单控制（职业偏好/技能标签/优化历史），append/replace 模式，容量控制 |
| `skill_loader` 工具 | ✅ 已完成 | `SkillLoaderTool` 已在 `_get_shared_tool_registry()` 中注册，LLM 可调用加载 resume-skill.md |
| `web_fetch` 工具 | ✅ 已完成 | 抓取 URL 网页内容，5 分钟缓存，内容截断，协议校验（仅 HTTP/HTTPS） |

**关键文件**：
- `resume_agent/prompts/system_prompt.py` — 系统提示词 + 组装逻辑
- `resume_agent/skills/resume-skill.md` — 简历优化领域知识
- `resume_agent/skills/resume_skill.py` — Skill 管理模块
- `resume_agent/memory/manager.py` — 记忆加载/写入/容量控制
- `resume_agent/memory/paths.py` — 用户记忆目录路径管理
- `resume_agent/tools/memory_write.py` — 记忆写入工具
- `resume_agent/tools/skill_loader.py` — 技能加载工具
- `resume_agent/tools/web_fetch.py` — 网页抓取工具

## P0-3：SSE 对话端点 + 极简验证页面 ✅

| 功能 | 状态 | 说明 |
|------|------|------|
| FastAPI 应用骨架 | ✅ 已完成 | 路由注册、CORS 中间件（allow_origins=*）、静态文件挂载、生命周期管理 |
| `POST /api/chat` SSE 端点 | ✅ 已完成 | SSE 流式对话，P0 开发模式使用默认 user_id `dev_user` |
| SessionPool | ✅ 已完成 | LRU 淘汰 + 空闲超时淘汰（5 分钟定时），max_sessions 限制，会话 Key 格式 `channel:user_id:session_id` |
| StreamEvent → SSE 序列化 | ✅ 已完成 | 完整映射 |
| 极简 HTML 验证页面 | ✅ 已完成 | 单文件 HTML（P1 阶段已升级为 5 Tab 页面） |
| 会话快照持久化 | ✅ 已完成 | `session_pool._save_snapshot()` 已实现 |

**关键文件**：
- `backend/app.py` — FastAPI 应用入口
- `backend/routes/chat.py` — SSE 流式对话端点
- `resume_agent/session_pool.py` — 多租户会话池
- `resume_agent/models/sse_events.py` — SSE 事件类型定义
- `resume_agent/services/session_storage.py` — 会话快照持久化
