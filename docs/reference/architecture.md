# 架构概要

> 精简版架构参考，完整设计见 `docs/archive/design/`。

## 产品定位

Resume Agent：基于 OpenHarness 重构的简历智能体，结合用户简历与 JD 智能生成优化简历，支持 Web 和 IM 渠道交互。

| 属性 | 值 |
|------|-----|
| 产品形态 | 云端 Web 服务 + IM 渠道接入 |
| 目标并发 | 10 用户同时在线 |
| LLM 后端 | DeepSeek API（OpenAI 兼容协议，多 Key 轮询） |
| 部署环境 | 轻量级云服务器（单机） |
| 底层框架 | OpenHarness v0.1.6（裁剪复用） |

## 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                     接入层                                │
│   Web UI (Next.js) │ 飞书频道 │ 微信/企微 │ 其他 IM     │
└────────┬────────────┬─────────────┬──────────────────────┘
         │ SSE/JSON   │ MessageBus  │ ChannelAdapter
┌────────▼────────────▼─────────────▼──────────────────────┐
│                Resume Agent Service (FastAPI)             │
│  ┌────────────────────────────────────────────────────┐  │
│  │           共享单例层（进程级）                        │  │
│  │  API Client Pool │ McpClientMgr │ ToolRegistry     │  │
│  │  HookExecutor    │ SkillLoader                      │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │           每会话独立层（用户级）                      │  │
│  │  QueryEngine │ Messages │ UserMemory │ Settings    │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │           Web API 层                                │  │
│  │  /api/chat │ /api/resume/* │ /api/memory/*         │  │
│  │  /api/tools/* │ /api/settings/* │ /api/auth/*      │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
                         │
                    DeepSeek API (多Key)
```

## 代码目录结构

```
ResumeHarness/
├── backend/              # FastAPI Web 服务层
│   ├── app.py            # 应用入口
│   ├── routes/           # API 路由
│   └── middleware/       # 中间件（认证/限速/监控）
├── resume_agent/         # 核心 Agent 逻辑包
│   ├── runtime.py        # 精简版 RuntimeBundle 构建
│   ├── session_pool.py   # 多租户会话池
│   ├── resume_parser.py  # Markdown → ResumeData 解析
│   ├── resume_renderer.py # 渲染管线
│   ├── api_key_pool.py   # 多 Key 轮询
│   ├── mcp_auth.py       # 用户级 MCP 认证
│   ├── db.py             # SQLite 数据库
│   ├── config/           # 配置管理
│   ├── prompts/          # 提示词
│   ├── memory/           # 记忆系统
│   ├── channels/         # 消息渠道
│   ├── services/         # 核心服务
│   ├── models/           # 数据模型
│   ├── tools/            # Agent 工具
│   ├── skills/           # 技能文件
│   └── templates/        # Jinja2 HTML 模板（7 套）
└── frontend/             # Next.js 前端
```

## 核心数据流

### Web 端对话

```
POST /api/chat → SessionPool → QueryEngine → DeepSeek API → SSE 流式推送
                                          ↘ tool_use → memory_write/web_fetch/MCP tools
```

### 简历生成

```
LLM 输出 Markdown → 正则截取 → ResumeData 解析 →
  ├── SSE resume_data → 前端 ResumePreview 组件渲染
  └── 自动保存快照（JSON + MD 双格式）
      └── 下载：ResumeData + Jinja2 模板 → weasyprint/xhtml2pdf → PDF/DOCX/HTML
```

## 多租户隔离

| 资源 | 隔离级别 |
|------|----------|
| QueryEngine/Messages | 每会话 |
| Memory/Settings | 每用户 |
| API Client/MCP Manager/ToolRegistry | 进程级共享 |

## 技术栈

| 层次 | 技术 |
|------|------|
| Agent 框架 | OpenHarness (裁剪复用) |
| LLM | DeepSeek API (多 Key 轮询) |
| Web 后端 | FastAPI + uvicorn |
| Web 前端 | Next.js 16 + React 19 + shadcn/ui + Tailwind CSS v4 |
| PDF 生成 | ResumeData + Jinja2 + weasyprint/xhtml2pdf/fpdf2 降级 |
| MCP | HTTP 协议 + McpServerBase 共享框架 |
| 认证 | JWT (access 7d + refresh 30d) |
| 数据存储 | SQLite (aiosqlite) |
