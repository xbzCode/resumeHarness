# P3 迭代规划：质量增强版

**目标**：解决简历生成的核心体验问题——PDF 高质量排版、领域 Skill 精调提升内容匹配度、MCP 工具扩展能力、速率限制保障稳定性。

## P3-1：简历结构化渲染引擎 (5 天) ✅ 已完成

| 任务 | 说明 |
|------|------|
| ResumeData 数据模型 | Pydantic 结构化简历数据模型 |
| Markdown → ResumeData 解析器 | 容错处理格式不一致 |
| Jinja2 HTML 模板引擎 | 替代 python-markdown + CSS overlay |
| professional/academic/creative 模板 | 三种布局风格 |
| SSE resume_data 事件 | LLM 输出完毕后推送结构化数据 |
| 前端 ResumePreview 组件 | 所见即所得简历预览 |
| 双格式快照持久化 | 同时保存 ResumeData JSON + Markdown 原文 |
| 渲染引擎集成 | ResumeData + Jinja2 → weasyprint/xhtml2pdf → PDF |

## P3-2：领域 Skill 精调 + 智能模板匹配 (3 天) ✅ 已完成

| 任务 | 说明 |
|------|------|
| 简历输出标记分隔 | `<!--RESUME-->` / `<!--/RESUME-->` 标记 |
| `resume-skill.md` 迭代 | 根据实际使用反馈优化 |
| 行业细分 Skill | tech/finance/jd 专项技能文件 |
| 系统提示词优化 | 增强输出格式约束 |
| 行业→模板映射 | 自动推荐最佳模板 |
| 智能模板推荐 API | `GET /api/resume/template-hint` |

## P3-3：MCP 工具接入 (3 天) ✅ 已完成

| 任务 | 说明 |
|------|------|
| McpClientManager 共享单例 | 进程级创建，所有会话复用 |
| MCP Tool Wrapper | 远程 MCP 工具注册为 BaseTool |
| PDF 转换 MCP | 部署 PDF 转换 HTTP MCP 服务 |
| 邮件发送 MCP | 用户可通过对话让 Agent 发送简历到邮箱 |
| 运行时集成 | MCP 工具注册到 ToolRegistry + 生命周期管理 |
| MCP 管理 API | 状态/认证/刷新 |

## P3-4：速率限制 + 监控 (2 天) ✅ 已完成

| 任务 | 说明 |
|------|------|
| API 速率限制 | 按 user_id 维护令牌桶 |
| DeepSeek 429 处理 | 多 Key 轮询 + 排队重试 + SSE 友好提示 |
| 基础监控 | 请求量/延迟/错误率日志 + 定期汇总 |
