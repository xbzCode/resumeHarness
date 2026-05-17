# P0-P3 缺陷修复记录

| 序号 | 日期 | 缺陷描述 | 修复方式 | 涉及文件 |
|------|------|----------|----------|----------|
| 1 | 2026-04-19 | 创建会话失败：RuntimeBundle.__init__() missing 1 required positional argument: 'session_id' | `build_resume_runtime()` 构造 `RuntimeBundle` 时漏传 `session_id` 参数 | `ResumeHarness/resume_agent/runtime.py` |
| 2 | 2026-04-19 | web_fetch 工具误调用虚构 URL 导致 HTTP 404 | 系统提示词中新增"工具使用规范"段落 | `ResumeHarness/resume_agent/prompts/system_prompt.py` |
| 3 | 2026-04-19 | 记忆文档不会自动更新 | 在 `_get_shared_tool_registry()` 中注册 `MemoryWriteTool` | `ResumeHarness/resume_agent/runtime.py` |
| 4 | 2026-04-21 | `SkillLoaderTool` 未在 ToolRegistry 中注册 | 添加注册 | `ResumeHarness/resume_agent/runtime.py` |
| 5 | 2026-04-21 | `ApiKeyPool` 未与 `OpenAICompatibleClient` 集成 | 重构客户端支持多 Key | `ResumeHarness/resume_agent/api/openai_client.py` |
| 6 | 2026-04-21 | `session_pool._save_snapshot()` 空实现 | 实现方法体 | `ResumeHarness/resume_agent/session_pool.py` |
| 7 | 2026-04-21 | 上下文压缩未实现 | 新建 `services/compact.py` | `ResumeHarness/resume_agent/services/compact.py` |
| 8 | 2026-04-21 | SSE 心跳未实现 | 添加 15 秒心跳 | `ResumeHarness/backend/routes/chat.py` |
| 9 | 2026-04-21 | `render_pdf.py` 硬编码 Windows 字体路径 | 改为跨平台字体搜索 | `ResumeHarness/resume_agent/render_pdf.py` |
| 10 | 2026-04-21 | `web_fetch` 简易正则提取 HTML | 改用 readability-lxml | `ResumeHarness/resume_agent/tools/web_fetch.py` |
| 11 | 2026-05-01 | PDF 上传不支持解析 | 新增 PyPDF2 提取 | `ResumeHarness/backend/routes/memory.py` |
| 12 | 2026-05-02 | 对话页回车不会发送消息 | 改为 Enter 发送 | `frontend/src/app/(app)/chat/page.tsx` |
| 13 | 2026-05-02 | 对话页消息过长时不会自动滚动 | 改用 `overflow-y-auto` + `scrollIntoView` | `frontend/src/app/(app)/chat/page.tsx` |
| 14 | 2026-05-02 | 对话中已给出 JD 描述，下次仍调用 web_fetch 重复获取 | 新增 `session_started` SSE 事件 + 加强提示词约束 | `ResumeHarness/backend/routes/chat.py` 等 |
| 15 | 2026-05-02 | 对话页没有展示思考过程 | 新增 `ThinkingDelta` 事件类型 | 多个文件 |
| 16 | 2026-05-02 | 对话页没有头像 | 添加 Bot/User 头像 | `frontend/src/app/(app)/chat/page.tsx` |
| 17 | 2026-05-02 | 页面刷新后对话内容丢失 | zustand persist + 历史会话列表 | `frontend/src/store/chat.ts` |
| 18 | 2026-05-02 | 生成的简历中包含无关的思考过程内容 | 修复截取逻辑 | `ResumeHarness/backend/routes/chat.py` |
| 19 | 2026-05-02 | 左侧新建对话按钮不生效 | 同时清空 chatStore | `frontend/src/app/(app)/layout.tsx` |
| 20 | 2026-05-02 | 路由始终为 /chat，刷新后无法恢复会话 | URL sid 参数方案 | `frontend/src/app/(app)/chat/page.tsx` |
| 21 | 2026-05-02 | 生成简历快照中包含优化说明等非简历内容 | 非简历章节检测正则 | `ResumeHarness/backend/routes/chat.py` |
| 22 | 2026-05-02 | 发送消息时出现两个 Bot 头像 | 跳过空 assistant 消息渲染 | `frontend/src/app/(app)/chat/page.tsx` |
| 23 | 2026-05-02 | 简历内容截取逻辑错误 | 重写简历提取策略 | `ResumeHarness/backend/routes/chat.py` |
| 24 | 2026-05-02 | 思考过程未正确折叠展示 | 新增 `streaming` prop | `frontend/src/app/(app)/chat/page.tsx` |
| 25 | 2026-05-02 | 服务重启后 LLM 无法感知之前的对话内容 | `load_session_snapshot()` + `_restore_history()` | `ResumeHarness/resume_agent/services/session_storage.py` |
| 26 | 2026-05-03 | 简历渲染包含非简历内容 | `<!--RESUME-->` 标记分隔机制 | 多个文件 |
| 27 | 2026-05-03 | 简历预览后"优化要点"不可见 | suggestions + resume_prefix 字段 | 多个文件 |
| 28 | 2026-05-03 | 简历预览只展示左栏布局 | 模板切换按钮组 | `frontend/src/app/(app)/chat/page.tsx` |
| 34 | 2026-05-04 | `aiosqlite` 未安装 | 安装缺失依赖 | `ResumeHarness/requirements.txt` |
| 35 | 2026-05-04 | `ApiRetryEvent` 未定义 | 移除错误导入 | `ResumeHarness/backend/routes/chat.py` |
| 36 | 2026-05-04 | 前端 `prevResumeContent` 未解构 | 补充解构 | `frontend/src/app/(app)/chat/page.tsx` |
| 37 | 2026-05-04 | 前端从局域网 IP 访问时 CORS 拒绝 | CORS 白名单扩展 | `ResumeHarness/resume_agent/config/settings.py` |
| 38 | 2026-05-04 | 登录接口 pending 无响应 | 中间件改为纯 ASGI | 多个中间件文件 |
| 39 | 2026-05-05 | 简历保存接口失败 | 前端修改保存逻辑 | `frontend/src/app/(app)/memory/page.tsx` |
| 40 | 2026-05-05 | 对话输出到一半暂停 | 自动续写机制 | `ResumeHarness/resume_agent/api/openai_client.py` |
| 41-49 | 2026-05-06 | 前端各类 UI 问题修复 | 各种修复 | 多个前端文件 |
| 50-62 | 2026-05-06~07 | PDF/DOCX/分享/模板样式问题修复 | 各种修复 | 多个文件 |
