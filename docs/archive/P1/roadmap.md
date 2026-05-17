# P1 迭代规划：Web 服务可用版

**目标**：FastAPI 完整 Web 服务跑通，SSE 流式对话 + 简历渲染下载，单用户完整流程。

## P1-1：简历渲染与下载 (3 天) ✅ 已完成

| 任务 | 说明 |
|------|------|
| `resume_renderer.py` | Markdown → PDF (fpdf2)，实现渲染队列 |
| 简历快照持久化 | LLM 生成简历后自动保存 |
| `GET /api/resume/{resume_id}/download` | 简历下载端点 |
| `GET /api/resume/{resume_id}/preview` | 简历预览端点 |
| `GET /api/resume/templates` | 获取可用简历模板列表 |
| 端到端测试 | 从对话到下载完整流程 |

## P1-2：记忆管理 API + 用户配置 + web_fetch (4 天) ✅ 已完成

| 任务 | 说明 |
|------|------|
| 记忆 CRUD API | `GET/PUT/DELETE /api/memory/{doc_name}` |
| 简历上传 | `POST /api/memory/upload` |
| 用户级 Settings | 每用户可覆盖全局配置 |
| 记忆注入提示词 | 对话时自动加载用户记忆文件 |
| `web_fetch` 工具 | 抓取 URL 网页内容 |

## P1-3：工具与系统 API (3 天) ✅ 已完成

| 任务 | 说明 |
|------|------|
| `GET /api/tools` | 查询可用工具列表 |
| `GET /api/mcp/status` | MCP 服务状态 |
| `GET /api/skills` | Skill 列表 |
| `GET /api/sessions` | 列出历史会话 |
| `GET /api/sessions/{id}` | 加载历史会话 |
